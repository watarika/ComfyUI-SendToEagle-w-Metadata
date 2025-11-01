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
        self.api_token = os.environ.get("EAGLE_API_TOKEN", None) # Go to Preferences > Developer Settings to generate and configure your API token.
        self.eagle_api = EagleAPI(self.eagle_server_url, self.api_token)

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("filepath", "filepath_count")
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)
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
        positive="",
        negative="",
        prompt=None,
        extra_pnginfo=None,
    ):
        images = self._unwrap_to_value(images)
        default_filename_prefix = "ComfyUI"
        filename_prefix_source = self._normalize_batch_input(
            self._unwrap_to_value(filename_prefix),
            self._coerce_string_value,
        )
        sampler_selection_method = self._unwrap_scalar(sampler_selection_method)
        sampler_selection_node_id = self._unwrap_scalar(sampler_selection_node_id)
        file_format = self._unwrap_scalar(file_format)
        lossless_webp = self._unwrap_scalar(lossless_webp)
        quality = self._unwrap_scalar(quality)
        save_workflow_json = self._unwrap_scalar(save_workflow_json)
        add_counter_to_filename = self._unwrap_scalar(add_counter_to_filename)
        civitai_sampler = self._unwrap_scalar(civitai_sampler)
        calc_model_hash = self._unwrap_scalar(calc_model_hash)
        save_only_no_send = self._unwrap_scalar(save_only_no_send)
        send_metadata_as_memo = self._unwrap_scalar(send_metadata_as_memo)
        tag_pattern = self._unwrap_scalar(tag_pattern)
        custom_tag_pattern_source = self._normalize_batch_input(
            self._unwrap_to_value(custom_tag_pattern),
            self._coerce_string_value,
        )
        eagle_folder_source = self._normalize_batch_input(
            self._unwrap_to_value(eagle_folder),
            self._coerce_string_value,
        )
        memo_source = self._normalize_batch_input(
            self._unwrap_to_value(memo),
            self._coerce_string_value,
        )
        extra_metadata_source = self._normalize_batch_input(
            self._unwrap_to_value(extra_metadata),
            self._coerce_metadata_value,
        )
        positive = self._unwrap_to_value(positive)
        negative = self._unwrap_to_value(negative)
        prompt = self._unwrap_to_value(prompt)
        extra_pnginfo = self._unwrap_to_value(extra_pnginfo)

        image_tensors = self._flatten_image_batch(images)
        if not image_tensors:
            return ([], 0)

        positive_prompts = self._normalize_prompt_input(positive)
        negative_prompts = self._normalize_prompt_input(negative)

        has_manual_positive = self._prompt_has_manual(positive_prompts)
        has_manual_negative = self._prompt_has_manual(negative_prompts)
        use_workflow_prompts = not (has_manual_positive and has_manual_negative)

        pnginfo_dict_src = self.gen_pnginfo(
            sampler_selection_method,
            sampler_selection_node_id,
            civitai_sampler,
            calc_model_hash,
            include_prompts=use_workflow_prompts,
        )

        results = []
        file_path_list = []
        batch_size = len(image_tensors)
        primary_image = image_tensors[0]

        folder_id_cache = {}

        for index, image in enumerate(image_tensors):
            image_array = image.cpu().numpy() if hasattr(image, "cpu") else np.asarray(image)
            i = 255.0 * image_array
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            pnginfo_dict = pnginfo_dict_src.copy()
            extra_metadata_value = self._select_batch_value(extra_metadata_source, index, {})
            if isinstance(extra_metadata_value, dict):
                extra_metadata_value = extra_metadata_value.copy()
            else:
                extra_metadata_value = {}
            for k, v in extra_metadata_value.items():
                if k and v:
                    pnginfo_dict[k] = str(v).replace(",", "/")
            if batch_size >= 2:
                pnginfo_dict["Batch index"] = index
                pnginfo_dict["Batch size"] = batch_size

            positive_value, apply_positive = self._select_prompt_for_index(
                positive_prompts, index
            )
            negative_value, apply_negative = self._select_prompt_for_index(
                negative_prompts, index
            )

            if apply_positive:
                pnginfo_dict["Positive prompt"] = positive_value
            if apply_negative:
                pnginfo_dict["Negative prompt"] = negative_value

            parameters = Capture.gen_parameters_str(pnginfo_dict)
            filename_prefix_value = self._select_batch_value(
                filename_prefix_source, index, default_filename_prefix
            )
            if not filename_prefix_value:
                filename_prefix_value = default_filename_prefix
            formatted_filename_prefix = self.format_filename(filename_prefix_value, pnginfo_dict)
            output_path = os.path.join(self.output_dir, formatted_filename_prefix)
            if not os.path.exists(os.path.dirname(output_path)):
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            (
                full_output_folder,
                filename,
                counter,
                subfolder,
                _filename_prefix_from_path,
            ) = folder_paths.get_save_image_path(
                formatted_filename_prefix,
                self.output_dir,
                primary_image.shape[1],
                primary_image.shape[0],
            )
            base_filename = filename
            if add_counter_to_filename:
                base_filename += f"_{counter:05}_"
            elif batch_size >= 2:
                base_filename += f"({index})"

            # jpegの場合は拡張子をjpgに変更（jpegのままだとEagleに送信した場合に .jpeg.jpg となるため）
            file_name = base_filename + "." + ("jpg" if file_format == "jpeg" else file_format)
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
                eagle_folder_value = self._select_batch_value(eagle_folder_source, index, "")
                folder_cache_key = eagle_folder_value or ""
                if folder_cache_key not in folder_id_cache:
                    folder_id_cache[folder_cache_key] = self.eagle_api.find_or_create_folder(eagle_folder_value)
                folder_id = folder_id_cache[folder_cache_key]

                # Eagleに送るURLを作成
                url = f"{self.comfyui_url}/api/view?filename={file_name}&type={self.type}&subfolder={subfolder}"

                # annotationを作成
                annotation = ""
                memo_value = self._select_batch_value(memo_source, index, "")
                memo_value = memo_value if isinstance(memo_value, str) else str(memo_value)
                if send_metadata_as_memo:
                    annotation += parameters
                    if memo_value:
                        annotation += "\nMemo: " + memo_value
                elif memo_value:
                    annotation = memo_value

                # Eagleに送る情報を作成
                custom_tag_pattern_value = self._select_batch_value(
                    custom_tag_pattern_source, index, ""
                )
                item = {
                    "url": url,
                    "name": file_name,
                    "annotation": annotation,
                    "tags": self.create_tags(
                        tag_pattern,
                        custom_tag_pattern_value,
                        memo_value,
                        extra_metadata_value,
                        pnginfo_dict,
                    ),
                }

                # Eagleに送る
                self.eagle_api.add_item_from_url(data=item, folder_id=folder_id)

            results.append(
                {"filename": file_name, "subfolder": subfolder, "type": self.type}
            )
            file_path_list.append(file_path)
            counter += 1

        return (file_path_list, len(file_path_list))

    @classmethod
    def gen_pnginfo(
        cls,
        sampler_selection_method,
        sampler_selection_node_id,
        save_civitai_sampler,
        calc_model_hash,
        include_prompts=True,
    ):
        # get all node inputs
        inputs = Capture.get_inputs(calc_model_hash, include_prompts)

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
    
    @staticmethod
    def _unwrap_to_value(value):
        while isinstance(value, list) and len(value) == 1:
            value = value[0]
        return value

    @staticmethod
    def _unwrap_scalar(value):
        value = SendToEagleWithMetadata._unwrap_to_value(value)
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @classmethod
    def _normalize_prompt_input(cls, prompt_input):
        if isinstance(prompt_input, list):
            normalized = []
            for item in prompt_input:
                if isinstance(item, list):
                    normalized.extend(cls._normalize_prompt_input(item))
                else:
                    normalized.append(cls._coerce_prompt_text(item))
            return normalized
        return cls._coerce_prompt_text(prompt_input)

    @staticmethod
    def _coerce_prompt_text(value):
        if isinstance(value, str):
            return value.strip()
        return ""

    @staticmethod
    def _prompt_has_manual(prompt_source):
        if isinstance(prompt_source, list):
            return len(prompt_source) > 0
        if isinstance(prompt_source, str):
            return prompt_source != ""
        return False

    @staticmethod
    def _select_prompt_for_index(prompt_source, index):
        if isinstance(prompt_source, list):
            if 0 <= index < len(prompt_source):
                return prompt_source[index], True
            return "", True
        if isinstance(prompt_source, str) and prompt_source != "":
            return prompt_source, True
        return "", False

    @classmethod
    def _normalize_batch_input(cls, value, coerce_fn=None):
        value = cls._unwrap_to_value(value)
        if isinstance(value, list):
            normalized = []
            for item in value:
                if isinstance(item, list):
                    normalized.extend(cls._normalize_batch_input(item, coerce_fn))
                else:
                    normalized.append(cls._apply_coerce(item, coerce_fn))
            return normalized
        return cls._apply_coerce(value, coerce_fn)

    @staticmethod
    def _apply_coerce(value, coerce_fn):
        if coerce_fn is None:
            return value
        return coerce_fn(value)

    @staticmethod
    def _coerce_string_value(value):
        if isinstance(value, str):
            return value
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _coerce_metadata_value(value):
        if isinstance(value, dict):
            return value
        if value is None:
            return {}
        return {}

    @staticmethod
    def _select_batch_value(source, index, default=None):
        if isinstance(source, list):
            if 0 <= index < len(source):
                return source[index]
            return default
        if source is None or source == "":
            return default
        return source

    @classmethod
    def _flatten_image_batch(cls, images):
        flattened = []

        def _collect(item):
            if item is None:
                return
            if isinstance(item, (list, tuple)):
                for sub_item in item:
                    _collect(sub_item)
                return
            if hasattr(item, "shape"):
                shape_len = len(item.shape)
                if shape_len >= 4:
                    for idx in range(item.shape[0]):
                        _collect(item[idx])
                    return
            flattened.append(item)

        _collect(images)
        return flattened

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

