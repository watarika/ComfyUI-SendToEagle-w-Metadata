from .py.nodes.node import SendToEagleWithMetadataFull, SendToEagleWithMetadataSimple, CreateExtraMetadata

NODE_CLASS_MAPPINGS = {
    "SendToEagleWithMetadataSimple": SendToEagleWithMetadataSimple,
    "SendToEagleWithMetadata": SendToEagleWithMetadataFull,
    "CreateExtraMetadata": CreateExtraMetadata,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SendToEagleWithMetadataSimple": "Send to Eagle With Metadata",
    "SendToEagleWithMetadata": "Send to Eagle With Metadata (Extended)",
    "CreateExtraMetadata": "Create Extra Metadata",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
