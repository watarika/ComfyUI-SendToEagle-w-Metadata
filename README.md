# ComfyUI-SendToEagle-w-Metadata

[English] [<a href="README_ja.md">日本語</a>]

- A custom node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- Sends images with metadata (PNGInfo) obtained from the input values of each node to [Eagle](https://en.eagle.cool/) (image management software)
- You can also add arbitrary `Key:Value` pairs to the metadata
- You can customize the tags to be registered in Eagle
- You can save arbitrary strings and metadata in the Eagle notes field

## Installation

```
cd <ComfyUI directory>/custom_nodes
git clone https://github.com/watarika/ComfyUI-SendToEagle-w-Metadata.git
```

## List of Custom Nodes

- Send to Eagle With Metadata
- Send to Eagle With Metadata (Extended)
- Create Extra MetaData

## Send to Eagle With Metadata

- Saves the `images` received as input to storage as images with metadata (PNGInfo), and then sends them to Eagle
- For details on the actual metadata added, please refer to [Metadata Added to Images](#metadata-detail)
- If the file format is `png` or `webp`, the workflow is also saved in the image<br>
 Note: If it is `webp` and `lossless`, the workflow may not be saved (under investigation)

![SendToEagleWithMetadata Preview](img/sendtoeagle_w_metadata.png)

### Default Behavior

The default behavior is as follows:<br>
If you want to change these behaviors, use the `Send to Eagle With Metadata (Extended)` node.

- The file name is saved in the format `yyyyMMdd-hhmmss_SSSSSS` + `extension`
  - If the batch size is 2 or more, `(Batch index)` is appended to the end to ensure that images executed in batches have unique file names
- Sent to the default Eagle folder
- Metadata is also saved in the Eagle notes field
- The sampler name is converted to the notation used on Civitai
  - Example: If the sampler is `dpmpp_2m` and the scheduler is `karras`, it becomes `DPM++ 2M Karras`
- The model hash value is not output in the metadata
- Metadata is obtained from the first processed KSampler node

### Configurable Settings

| Item                | Description                                                                                                                                                                                                                                                                                                |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| file_format         | Specifies the format of the file to be saved. You can specify `png`, `jpeg`, or `webp`                                                                                                                                                                                                                        |
| lossless_webp       | Specifies whether to compress the image when `file_format` is `webp`<ul><li>`lossless`: Saves the image without compression</li><li>`lossy`: Compresses and saves the image</li></ul>                                                                                                                         |
| quality             | Specifies the quality when compressing the image. Specify a value between `0` and `100`.<br>Note: Only valid for jpeg or webp (lossy).                                                                                                                                                                          |
| save_only_no_send   | If `true`, the image is saved to storage but not sent to Eagle                                                                                                                                                                                                                                             |
| tag_pattern         | Specifies what to add to Eagle tags.<ul><li>`None`: No tags are added</li><li>`Positive Prompt`: The positive prompt is added as a tag</li><li>`Positive Prompt, Negative Prompt`: The positive and negative prompts are added as tags</li><li>`Memo`: The content of `memo` is added as a tag</li><li>`Custom`: The string specified by `custom_tag_pattern` is added as a tag</li></ul>Note: When registering the negative prompt, `"n:"` is added to the beginning of the tag name to distinguish it from the positive prompt tag |
| custom_tag_pattern  | Specifies the tag pattern to be used when `tag_pattern` is `Custom`, separated by commas.<br>The following settings are available:<ul><li>Image metadata: `Positive prompt`, `Negative prompt`, `Steps`, `Sampler`, `CFG scale`, `Seed`, `Clip skip`, `Size`, `Model`, `Model hash`, `VAE`, `VAE hash`, `Batch index`, `Batch size`</li><li>Memo content: `Memo`</li><li>Additional metadata: The `Key` defined in `extra_metadata`</li></ul>Note: Items that do not match the above are added as tags as they are<br>Note: Metadata for which a value cannot be obtained is added with a value of `-` (e.g., `"Model hash: -"`)||
| memo                | Specifies the text to be saved in the Eagle notes field. The specified text is appended with `"Memo:"` and saved at the end of the notes field                                                                                                                                                                    |
| extra_metadata      | Allows you to add your own metadata to the saved image. Can be omitted if not needed.<br>Specifies the metadata to be added using the `Create Extra MetaData` node.                                                                                                                                                               |
| positive / negative | This is an option input for explicitly specifying prompts, rather than automatically retrieving them from the workflow. Use this input when prompts cannot be automatically retrieved or when you wish to specify prompts yourself. |

### Batch Support
The inputs memo, custom_tag_pattern, extra_metadata, positive, and negative support batch images.  
If an input is a list, the corresponding element is applied to each image in the batch index. If the list is shorter than the batch size, empty strings are used. If a single string is passed, the same string is applied to all images.

### Node Output

- filepath: Outputs the full file paths of saved images (in list format)
- filepath_count: Outputs the number of saved images
- image: Outputs the input image as received

## Send to Eagle With Metadata (Extended)

- Saves the `images` received as input to storage as images with metadata (PNGInfo), and then sends them to Eagle
- You can customize the default behavior of `Send to Eagle With Metadata`
- Added feature: You can save the workflow's JSON file to storage

![SendToEagleWithMetadataExtended Preview](img/sendtoeagle_w_metadata_ex.png)

### Additional Configurable Settings

- In addition to the settings that can be specified in `Send to Eagle With Metadata`, the following settings can be specified

| Item                      | Description                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| filename_prefix           | Specifies the string to be added to the beginning of the saved file name. You can also specify a directory by separating it with a slash (/).<br>You can replace it with the acquired information by using `%<Key>%`.<br>Note: Refer to the [table below](#filename-prefix-key) for the keys that can be specified.                                                                  |
| sampler_selection_method  | Specifies how to select the KSampler node executed before this node<ul><li>`Farthest`: Selects the KSampler node farthest from this node</li><li>`Nearest`: Selects the KSampler node closest to this node</li><li>`By node ID`: Selects the KSampler node with the node ID `sampler_selection_node_id`</li></ul>                                                       |
| sampler_selection_node_id | Only specified when `sampler_selection_method` is `By node ID`.<br>Specifies the node ID of the KSampler node executed before this node. The node ID is the number displayed in the upper right corner of the node.                                                                                                                                                        |
| save_workflow_json        | Specifies whether to save the workflow's JSON file to storage.<br>Note: It will not be sent to Eagle.                                                                                                                                                                                                                                                                    |
| add_counter_to_filename   | Specifies whether to add a counter to the file name.<ul><li>`true`: Adds a sequential number to a group of files with the same file name excluding the counter part</li><li>`false`: Does not add a counter. However, if the batch size is 2 or more, `(Batch index)` is appended to the end of the file name to ensure that images executed in batches have unique file names</li></ul> |
| civitai_sampler           | Converts the sampler name to the notation used on Civitai<br>Example: If the sampler is `dpmpp_2m` and the scheduler is `karras`, it becomes `DPM++ 2M Karras`                                                                                                                                                                                                     |
| calc_model_hash           | If `true`, calculates the hash value of the model and adds it to the metadata<br>Note: It takes time to calculate the hash value of the model                                                                                                                                                                                                                               |
| send_metadata_as_memo     | <ul><li>`true`: Saves the metadata in the Eagle notes field. If there is input to `memo`, its content is appended with `"Memo:"` and saved after the metadata</li><li>`false`: Does not save the metadata in the Eagle notes field. Only the content of `memo` is saved in the Eagle notes field</li></ul>                                                              |
| eagle_folder              | Specifies the image save destination folder in Eagle by FolderID or Folder name                                                                                                                                                                                                                                                                                          |

#### Batch Support
The filename_prefix and eagle_folder inputs support batch images.  
If an input is a list, elements corresponding to the batch index are applied. If the list is shorter than the batch size, empty strings are used. If a single string is passed, the same string is applied to all images.

<a id="filename-prefix-key"></a>
### Keys that can be specified in `filename_prefix`

| Key                   | Replaced Information       |
| --------------------- | -------------------------- |
| %seed%                | Seed value                 |
| %width%               | Image width                |
| %height%              | Image height               |
| %pprompt%             | Positive Prompt            |
| %pprompt:<n>chars%    | First n characters of Positive Prompt |
| %nprompt%             | Negative Prompt            |
| %nprompt:<n>chars%    | First n characters of Negative Prompt |
| %model%               | Checkpoint name            |
| %model:<n>chars%      | First n characters of Checkpoint name    |
| %date%                | Generation date and time (yyyyMMddhhmmss)   |
| %date:<format>%       | Generation date and time                   |

Refer to the table below for the identifiers specified in `<format>` of `%date:<format>%`.

| Identifier | Description |
| ------ | ---- |
| yyyy   | Year   |
| MM     | Month   |
| dd     | Day   |
| hh     | Hour   |
| mm     | Minute   |
| ss     | Second   |

## Create Extra Metadata

- Specifies the metadata to be added to the saved image.

![CreateExtraMetaData Preview](img/create_extra_metadata.png)

<a id="metadata-detail"></a>
## Metadata Added to Images

| Item                | Description                                                                                                                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Positive prompt     | Positive prompt                                                                                                                                                                             |
| Negative prompt     | Negative prompt                                                                                                                                                                             |
| Steps               | Number of steps                                                                                                                                                                            |
| Sampler             | Sampler + Scheduler name                                                                                                                                                                   |
| CFG scale           | CFG scale                                                                                                                                                                               |
| Seed                | Seed value                                                                                                                                                                              |
| Clip skip           | Clip skip value<br>Note: Output only when the `CLIP Set Last Layer` node is used                                                                                                                   |
| Size                | Image width × Image height                                                                                                                                                                  |
| Model               | Checkpoint name                                                                                                                                                                            |
| Model hash          | Checkpoint hash value<br>Note: Output only when `calc_model_hash` is `true`                                                                                                                         |
| VAE                 | VAE name                                                                                                                                                                                |
| VAE hash            | VAE hash value<br>Note: Output only when `calc_model_hash` is `true`                                                                                                                             |
| Lora_`n` Model name | `n`th LoRA name                                                                                                                                                                              |
| Lora_`n` Model hash | `n`th LoRA hash value                                                                                                                                                                           |
| Lora_`n` Strength model | Strength value for the model of the `n`th LoRA                                                                                                                                                        |
| Lora_`n` Strength clip | Strength value for the clip of the `n`th LoRA                                                                                                                                                        |
| Embedding_`n` Name  | `n`th Embedding name                                                                                                                                                                         |
| Embedding_`n` Hash  | `n`th Embedding hash value                                                                                                                                                                      |
| Batch index         | Batch process index<br>Note: Output only when Batch size >= 2                                                                                                                                     |
| Batch size          | Batch size<br>Note: Output only when Batch size >= 2                                                                                                                                            |
| Hashes              | Outputs the hash values of Model, Lora_`n`, and Embedding_`n` separated by commas (for [Civitai](https://civitai.com/))<br>Note: Output only when `calc_model_hash` is `true`                         |
| (Additional metadata) | Unique metadata entered in `extra_metadata`                                                                                                                                                     |

## Supported Nodes and Extensions
- Metadata is obtained from the inputs of the KSampler node found by `sampler_selection_method` and the inputs of previously executed nodes
  - The target KSampler nodes are the keys of `SAMPLERS` in [py/defs/samplers.py](py/defs/samplers.py) and files under [py/defs/ext/](py/defs/ext/)
- Please check the following files for supported nodes.
  - [py/defs/captures.py](py/defs/captures.py)
  - [py/defs/samplers.py](py/defs/samplers.py)
- Please check the following directory for supported extensions.
  - [py/defs/ext/](py/defs/ext/)

## Known Issues
- When using multiple “CLIP Text Encode (Prompt)” equivalent nodes in a loop, the first workflow execution works correctly. However, if the input to “CLIP Text Encode (Prompt)” remains unchanged and the node is not re-executed via caching during subsequent workflow executions, the prompt cannot be retrieved correctly (All prompts in the loop will end up being the value from the first loop iteration).
- If the input to “CLIP Text Encode (Prompt)” or its upstream inputs differ from the previous execution, causing the equivalent node to re-execute, it will function correctly in subsequent workflow runs.
- This behavior is due to ComfyUI's caching mechanism, making it difficult to address on the custom node side.
- Workaround: Explicitly input values into the node's positive/negative inputs.

## Change History
- 2025/11/05 1.1.6 Added IMAGE to output. Outputs the IMAGE received as input without modification.
- 2025/11/03 1.1.5 Fixed a bug that could cause the error "AttributeError: 'NoneType' object has no attribute 'caches'".
- 2025/11/02 1.1.4 Fixed a bug that caused errors in certain workflows
- 2025/11/01 1.1.3 Added the ability to set different values for each image in a batch by passing a list to each input in filename_prefix/custom_tag_pattern/eagle_folder/memo/extra_metadata.
- 2025/10/29 1.1.2 Fixed to correctly save the value for each loop iteration to metadata when called multiple times within a loop
- 2025/10/29 1.1.1 Add the size of the filepath (list) to the output
- 2025/10/29 1.1.0 Added support for supplying per-image positive/negative prompts via list inputs
- 2025/10/28 1.0.6 Changed to no preview for improved performance
- 2025/10/27 1.0.5 Supports Eagle API Token (specified via environment variable)
- 2025/10/26 1.0.4 Fixed cases where errors occur related to DynamicPrompt
- 2025/08/22 1.0.3 Fixed an issue where using Qwen-Image caused an error
- 2025/03/23 1.0.2 Fixed an error when using embeddings
- 2025/02/07 1.0.1 Support for comfyui-prompt-control
- 2025/01/04 1.0.0 First release

## Acknowledgements
  - The implementation for metadata acquisition is based on [ComfyUI-SaveImageWithMetaData](https://github.com/nkchocoai/ComfyUI-SaveImageWithMetaData)
  - The implementation for sending to Eagle is based on [D2 Send Eagle](https://github.com/da2el-ai/ComfyUI-d2-send-eagle)
  - The tag customization specification is based on the WebUI extension [Eagle-pnginfo](https://github.com/bbc-mc/sdweb-eagle-pnginfo)
  - Thanks to nkchocoai, da2el, and bbc_mc for creating and publishing such wonderful programs
