from .base import BaseNode, SendToEagleWithMetadata
from ..defs.combo import SAMPLER_SELECTION_METHOD, TAG_PATTERN

class SendToEagleWithMetadataFull(SendToEagleWithMetadata):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "sampler_selection_method": (SAMPLER_SELECTION_METHOD,),
                "sampler_selection_node_id": (
                    "INT",
                    {"default": 0, "min": 0, "max": 999999999, "step": 1},
                ),
                "file_format": (s.SAVE_FILE_FORMATS,),
                "lossless_webp": ("BOOLEAN", {"default": True, "label_on": "lossless", "label_off": "lossy"}),
                "quality": ("INT", {"default": 95, "min": 1, "max": 100}),
                "save_workflow_json": ("BOOLEAN", {"default": False}),
                "add_counter_to_filename": ("BOOLEAN", {"default": True}),
                "civitai_sampler": ("BOOLEAN", {"default": True}),
                "calc_model_hash": ("BOOLEAN", {"default": False}),
                "save_only_no_send": ("BOOLEAN", {"default": False}),
                "send_metadata_as_memo": ("BOOLEAN", {"default": True}),
                "tag_pattern": (TAG_PATTERN,),
                "custom_tag_pattern": ("STRING", {"default": ""}),
                "eagle_folder": ("STRING", {"default": ""}),
            },
            "optional": {
                "memo": ("STRING", {"multiline": True},),
                "extra_metadata": ("EXTRA_METADATA", {}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }
    
    FUNCTION = "send_to_eagle"


class SendToEagleWithMetadataSimple(SendToEagleWithMetadata):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "file_format": (s.SAVE_FILE_FORMATS,),
                "lossless_webp": ("BOOLEAN", {"default": True, "label_on": "lossless", "label_off": "lossy"}),
                "quality": ("INT", {"default": 95, "min": 1, "max": 100}),
                "save_only_no_send": ("BOOLEAN", {"default": False}),
                "tag_pattern": (TAG_PATTERN,),
                "custom_tag_pattern": ("STRING", {"default": ""}),
            },
            "optional": {
                "memo": ("STRING", {"multiline": True},),
                "extra_metadata": ("EXTRA_METADATA", {}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }
    
    FUNCTION = "send_to_eagle_simple"

    def send_to_eagle_simple(
        self,
        images,
        file_format,
        lossless_webp,
        quality,
        save_only_no_send,
        tag_pattern,
        custom_tag_pattern,
        memo="",
        extra_metadata={},
        prompt=None,
        extra_pnginfo=None,
    ):
        return self.send_to_eagle(
            images=images,
            filename_prefix="%date:yyyyMMdd-hhmmss_SSSSSS%",
            sampler_selection_method=SAMPLER_SELECTION_METHOD[0],
            sampler_selection_node_id=0,
            file_format=file_format,
            lossless_webp=lossless_webp,
            quality=quality,
            save_workflow_json=False,
            add_counter_to_filename=False,
            civitai_sampler=True,
            calc_model_hash=False,
            save_only_no_send=save_only_no_send,
            tag_pattern=tag_pattern,
            custom_tag_pattern=custom_tag_pattern,
            eagle_folder="",
            memo=memo,
            extra_metadata=extra_metadata,
            prompt=prompt,
            extra_pnginfo=extra_pnginfo,
        )


class CreateExtraMetadata(BaseNode):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "key1": ("STRING", {"default": "", "multiline": False}),
                "value1": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "key2": ("STRING", {"default": "", "multiline": False}),
                "value2": ("STRING", {"default": "", "multiline": False}),
                "key3": ("STRING", {"default": "", "multiline": False}),
                "value3": ("STRING", {"default": "", "multiline": False}),
                "key4": ("STRING", {"default": "", "multiline": False}),
                "value4": ("STRING", {"default": "", "multiline": False}),
                "extra_metadata": ("EXTRA_METADATA",),
            },
        }

    RETURN_TYPES = ("EXTRA_METADATA",)
    FUNCTION = "create_extra_metadata"

    def create_extra_metadata(
        self,
        extra_metadata={},
        key1="",
        value1="",
        key2="",
        value2="",
        key3="",
        value3="",
        key4="",
        value4="",
    ):
        extra_metadata.update(
            {
                key1: value1,
                key2: value2,
                key3: value3,
                key4: value4,
            }
        )
        return (extra_metadata,)
