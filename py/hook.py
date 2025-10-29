from .nodes.node import SendToEagleWithMetadataFull, SendToEagleWithMetadataSimple

current_prompt = {}
current_extra_data = {}
prompt_executer = None
current_full_node_id = -1
current_simple_node_id = -1
runtime_input_cache = {}


def pre_execute(self, prompt, prompt_id, extra_data, execute_outputs):
    global current_prompt
    global current_extra_data
    global prompt_executer
    global runtime_input_cache

    current_prompt = prompt
    current_extra_data = extra_data
    prompt_executer = self
    runtime_input_cache = {}


def pre_get_input_data(inputs, class_def, unique_id, *args):
    global current_full_node_id
    global current_simple_node_id

    if class_def == SendToEagleWithMetadataFull:
        current_full_node_id = unique_id
    elif class_def == SendToEagleWithMetadataSimple:
        current_simple_node_id = unique_id


def post_get_input_data(inputs, class_def, unique_id, result, execution_list=None, dynprompt=None, extra_data=None):
    global runtime_input_cache

    if dynprompt is None or result is None:
        return

    try:
        input_data_all, missing_keys, hidden_inputs = result
    except (TypeError, ValueError):
        return

    try:
        display_node_id = dynprompt.get_display_node_id(unique_id)
    except Exception:
        return

    entry = {
        "unique_id": unique_id,
        "inputs": input_data_all,
        "missing": missing_keys,
        "hidden": hidden_inputs,
    }
    runtime_input_cache[display_node_id] = entry

    try:
        real_node_id = dynprompt.get_real_node_id(unique_id)
        runtime_input_cache[real_node_id] = entry
    except Exception:
        pass

    runtime_input_cache[unique_id] = entry
