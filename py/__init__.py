import functools

from .hook import pre_execute, pre_get_input_data, post_get_input_data
import execution


# refer. https://stackoverflow.com/a/35758398
def prefix_function(function, prefunction):
    @functools.wraps(function)
    def run(*args, **kwargs):
        prefunction(*args, **kwargs)
        return function(*args, **kwargs)

    return run


execution.PromptExecutor.execute = prefix_function(
    execution.PromptExecutor.execute, pre_execute
)


_original_get_input_data = execution.get_input_data


def wrapped_get_input_data(inputs, class_def, unique_id, execution_list=None, dynprompt=None, extra_data=None):
    pre_get_input_data(inputs, class_def, unique_id, execution_list, dynprompt, extra_data)
    result = _original_get_input_data(
        inputs,
        class_def,
        unique_id,
        execution_list,
        dynprompt,
        extra_data if extra_data is not None else {},
    )
    try:
        post_get_input_data(
            inputs,
            class_def,
            unique_id,
            result,
            execution_list,
            dynprompt,
            extra_data if extra_data is not None else {},
        )
    except Exception:
        pass
    return result


execution.get_input_data = wrapped_get_input_data
