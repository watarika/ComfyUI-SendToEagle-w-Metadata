import json
import os
import re

from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image
from PIL.PngImagePlugin import PngInfo
import numpy as np

import piexif
import piexif.helper

import folder_paths
from comfy.cli_args import args

from ..capture import Capture
from .. import hook
from ..trace import Trace

from ..defs.combo import SAMPLER_SELECTION_METHOD, TAG_PATTERN
from ..utils.eagle_api import EagleAPI

class BaseNode:
    CATEGORY = "SendToEagle"


class SendToEagleWithMetadata(BaseNode):
    SAVE_FILE_FORMATS = ["png", "jpeg", "webp"]

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4
        self.eagle_server_url = os.environ.get("EAGLE_SERVER_URL", "http://localhost:41595") # No need to set for local machine
        self.comfyui_url = os.environ.get("EAGLE_COMFYUI_URL", "http://localhost:8188") # No need to set for local machine
        self.timezone = os.environ.get("EAGLE_TIMEZONE", None) # ex. "Asia/Tokyo",  No need to set for local machine
        self.eagle_api = EagleAPI(self.eagle_server_url)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filepath",)
    OUTPUT_IS_LIST = (True,)
    OUTPUT_NODE = True

    pattern_format = re.compile(r"(%[^%]+%)")

    def send_to_eagle(
        self,
        images,
        filename_prefix="ComfyUI",
        sampler_selection_method=SAMPLER_SELECTION_METHOD[0],
        sampler_selection_node_id=0,
        file_format="png",
        lossless_webp=True,
        quality=100,
        save_workflow_json=False,
        add_counter_to_filename=True,
        civitai_sampler=False,
        calc_model_hash=False,
        save_only_no_send=False,
        send_metadata_as_memo=True,
        tag_pattern=TAG_PATTERN[0],
        custom_tag_pattern="",
        eagle_folder="",
        memo="",
        extra_metadata={},
        prompt=None,
        extra_pnginfo=None,
    ):
        pnginfo_dict_src = self.gen_pnginfo(
            sampler_selection_method, sampler_selection_node_id, civitai_sampler, calc_model_hash
        )
        for k, v in extra_metadata.items():
            if k and v:
                pnginfo_dict_src[k] = v.replace(",", "/")

        results = []
        file_path_list = []
        for index, image in enumerate(images):
            i = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            pnginfo_dict = pnginfo_dict_src.copy()
            if len(images) >= 2:
                pnginfo_dict["Batch index"] = index
                pnginfo_dict["Batch size"] = len(images)

            parameters = Capture.gen_parameters_str(pnginfo_dict)
            filename_prefix = self.format_filename(filename_prefix, pnginfo_dict)
            output_path = os.path.join(self.output_dir, filename_prefix)
            if not os.path.exists(os.path.dirname(output_path)):
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            (
                full_output_folder,
                filename,
                counter,
                subfolder,
                filename_prefix,
            ) = folder_paths.get_save_image_path(
                filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0]
            )
            base_filename = filename
            if add_counter_to_filename:
                base_filename += f"_{counter:05}_"
            elif len(images) >= 2:
                base_filename += f"({index})"

            file_name = base_filename + "." + file_format
            file_path = os.path.join(full_output_folder, file_name)

            if file_format == "png":
                metadata = self.create_pnginfo(parameters, extra_pnginfo, prompt)                
                img.save(
                    file_path,
                    pnginfo=metadata,
                    compress_level=self.compress_level,
                )
            else:
                exif_bytes = self.create_exif_bytes(img, parameters, extra_pnginfo, prompt)
                img.save(
                    file_path,
                    optimize=True,
                    quality=quality,
                    lossless=lossless_webp,
                    exif=exif_bytes,
                )

            if save_workflow_json:
                file_path_workflow = os.path.join(
                    full_output_folder, f"{base_filename}.json"
                )
                with open(file_path_workflow, "w", encoding="utf-8") as f:
                    json.dump(extra_pnginfo["workflow"], f)

            if not save_only_no_send:
                # Eagleフォルダが指定されているならフォルダIDを取得
                folder_id = self.eagle_api.find_or_create_folder(eagle_folder)

                # Eagleに送るURLを作成
                url = f"{self.comfyui_url}/api/view?filename={file_name}&type={self.type}&subfolder={subfolder}"

                # annotationを作成
                annotation = ""
                if send_metadata_as_memo:
                    annotation += parameters
                    if memo:
                        annotation += "\nMemo: " + memo
                elif memo:
                    annotation = memo

                # Eagleに送る情報を作成
                item = {
                    "url": url,
                    "name": file_name,
                    "annotation": annotation,
                    "tags": self.create_tags(tag_pattern, custom_tag_pattern, memo, extra_metadata, pnginfo_dict),
                }

                # Eagleに送る
                self.eagle_api.add_item_from_url(data=item, folder_id=folder_id)

            results.append(
                {"filename": file_name, "subfolder": subfolder, "type": self.type}
            )
            file_path_list.append(file_path)
            counter += 1

        return {
            "ui": {"images": results},
            "result": (file_path_list,)
        }

    @classmethod
    def gen_pnginfo(
        cls, sampler_selection_method, sampler_selection_node_id, save_civitai_sampler, calc_model_hash
    ):
        # get all node inputs
        inputs = Capture.get_inputs(calc_model_hash)

        # get sampler node before this node
        if cls.__name__ == "SendToEagleWithMetadataFull":
            current_node_id = hook.current_full_node_id
        elif cls.__name__ == "SendToEagleWithMetadataSimple":
            current_node_id = hook.current_simple_node_id
        trace_tree_from_this_node = Trace.trace(
            current_node_id, hook.current_prompt
        )
        inputs_before_this_node = Trace.filter_inputs_by_trace_tree(
            inputs, trace_tree_from_this_node
        )
        sampler_node_id = Trace.find_sampler_node_id(
            trace_tree_from_this_node,
            sampler_selection_method,
            sampler_selection_node_id,
        )

        # get inputs before sampler node
        trace_tree_from_sampler_node = Trace.trace(sampler_node_id, hook.current_prompt)
        inputs_before_sampler_node = Trace.filter_inputs_by_trace_tree(
            inputs, trace_tree_from_sampler_node
        )

        # generate PNGInfo from inputs
        pnginfo_dict = Capture.gen_pnginfo_dict(
            inputs_before_sampler_node, inputs_before_this_node, save_civitai_sampler, calc_model_hash
        )
        return pnginfo_dict

    def format_filename(self, filename, pnginfo_dict):
        result = re.findall(self.pattern_format, filename)
        for segment in result:
            parts = segment.replace("%", "").split(":")
            key = parts[0]
            if key == "seed":
                filename = filename.replace(segment, str(pnginfo_dict.get("Seed", "")))
            elif key == "width":
                w = pnginfo_dict.get("Size", "x").split("x")[0]
                filename = filename.replace(segment, str(w))
            elif key == "height":
                w = pnginfo_dict.get("Size", "x").split("x")[1]
                filename = filename.replace(segment, str(w))
            elif key == "pprompt":
                prompt = pnginfo_dict.get("Positive prompt", "").replace("\n", " ")
                if len(parts) >= 2:
                    length = int(parts[1])
                    prompt = prompt[:length]
                filename = filename.replace(segment, prompt.strip())
            elif key == "nprompt":
                prompt = pnginfo_dict.get("Negative prompt", "").replace("\n", " ")
                if len(parts) >= 2:
                    length = int(parts[1])
                    prompt = prompt[:length]
                filename = filename.replace(segment, prompt.strip())
            elif key == "model":
                model = pnginfo_dict.get("Model", "")
                model = os.path.splitext(os.path.basename(model))[0]
                if len(parts) >= 2:
                    length = int(parts[1])
                    model = model[:length]
                filename = filename.replace(segment, model)
            elif key == "date":
                if self.timezone:
                    now = datetime.now(ZoneInfo(self.timezone))
                else:
                    now = datetime.now()
                date_table = {
                    "yyyy": now.year,
                    "MM": now.month,
                    "dd": now.day,
                    "hh": now.hour,
                    "mm": now.minute,
                    "ss": now.second,
                    "SSSSSS": now.microsecond,
                }
                if len(parts) >= 2:
                    date_format = parts[1]
                    for k, v in date_table.items():
                        date_format = date_format.replace(k, str(v).zfill(len(k)))
                    filename = filename.replace(segment, date_format)
                else:
                    date_format = "yyyyMMddhhmmss"
                    for k, v in date_table.items():
                        date_format = date_format.replace(k, str(v).zfill(len(k)))
                    filename = filename.replace(segment, date_format)

        return filename
    
    @classmethod
    def create_tags(cls, tag_pattern, custom_tag_pattern, memo, extra_metadata, pnginfo_dict) -> list:
        results = []

        if tag_pattern == "None":
            return results

        if tag_pattern == "Custom":
            tag_pattern = custom_tag_pattern

        for tag in tag_pattern.split(","):
            tag = tag.strip()
            if not tag:
                continue

            if tag == "Memo":
                results.extend(cls.create_memo_tags(memo))
            elif tag  == "Positive prompt":
                results.extend(cls.create_prompt_tags(pnginfo_dict.get(tag, "")))
            elif tag == "Negative prompt":
                results.extend(cls.create_prompt_tags(pnginfo_dict.get(tag, ""), "n:"))
            elif tag in ("Steps", "Sampler", "CFG scale", "Seed", "Clip skip", "Size", "Model", "Model hash", "VAE", "VAE hash", "Batch index", "Batch size"):
                results.append(f"{tag}: " + str(pnginfo_dict.get(tag, "-")))
            elif tag in extra_metadata and extra_metadata[tag]:
                results.append(f"{tag}: " + str(extra_metadata[tag]))
            else:
                results.append(tag)

        return results

    @classmethod
    def create_prompt_tags(cls, prompt_text: str, prefix: str = "") -> list:
        if (
            not isinstance(prompt_text, str)
            or not prompt_text.strip()
            or prompt_text == "undefined"
        ):
            return []

        cleaned_string = re.sub(r":\d+\.\d+", "", prompt_text)
        items = cleaned_string.split(",")
        return [
            prefix + re.sub(r"[\(\)]", "", item).strip()
            for item in items
            if re.sub(r"[\(\)]", "", item).strip()
        ]

    @classmethod
    def create_memo_tags(cls, memo: str) -> list:
        if not isinstance(memo, str) or not memo.strip():
            return []

        items = memo.split(",")
        return [
            re.sub(r"[\(\)]", "", item).strip()
            for item in items
            if re.sub(r"[\(\)]", "", item).strip()
        ]

    @classmethod
    def create_exif_bytes(cls, img, parameters, extra_pnginfo, prompt):
        metadata = img.getexif()

        if len(metadata) == 0:
            metadata = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}}

        if prompt is not None:
            metadata["0th"][0x0110] = "prompt:{}".format(json.dumps(prompt))
        if extra_pnginfo is not None:
            inital_exif = 0x010f
            for x in extra_pnginfo:
                metadata["0th"][inital_exif] = "{}:{}".format(x, json.dumps(extra_pnginfo[x]))
                inital_exif -= 1

        metadata["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(parameters, "unicode")

        return piexif.dump(metadata)

    @classmethod
    def create_pnginfo(cls, parameters, extra_pnginfo, prompt):
        metadata = None

        if not args.disable_metadata:
            metadata = PngInfo()
            if parameters:
                metadata.add_text("parameters", parameters)
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for x in extra_pnginfo:
                    metadata.add_text(x, json.dumps(extra_pnginfo[x]))

        return metadata

