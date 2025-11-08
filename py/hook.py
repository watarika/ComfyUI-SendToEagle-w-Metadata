from .nodes.node import SendToEagleWithMetadataFull, SendToEagleWithMetadataSimple

current_prompt = {}
current_extra_data = {}
prompt_executer = None
current_full_node_id = -1
current_simple_node_id = -1


def pre_execute(self, prompt, prompt_id, extra_data, execute_outputs):
    global current_prompt
    global current_extra_data
    global prompt_executer

    current_prompt = prompt
    current_extra_data = extra_data
    prompt_executer = self


def pre_get_input_data(inputs, class_def, unique_id, *args):
    global current_full_node_id
    global current_simple_node_id

    if class_def == SendToEagleWithMetadataFull:
        current_full_node_id = unique_id
    elif class_def == SendToEagleWithMetadataSimple:
        current_simple_node_id = unique_id


