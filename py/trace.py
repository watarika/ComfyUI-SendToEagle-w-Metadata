from collections import deque

from .defs.samplers import SAMPLERS
from .defs.combo import SAMPLER_SELECTION_METHOD


class Trace:
    @staticmethod
    def _resolve_node_id(node_id, prompt):
        if node_id is None:
            return None

        candidate = str(node_id)
        if candidate in prompt:
            return candidate

        # ComfyUI's For Loop nodes append iteration metadata to the unique id.
        # Walk prefixes (dropping the deepest segments) to locate the actual node id.
        parts = candidate.split(".")
        if len(parts) > 1:
            for i in range(len(parts) - 1, 0, -1):
                prefix = ".".join(parts[:i])
                if prefix in prompt:
                    return prefix

            for i in range(len(parts) - 1, 0, -1):
                suffix = ".".join(parts[-i:])
                if suffix in prompt:
                    return suffix

        if candidate.isdigit():
            numeric_key = int(candidate)
            if numeric_key in prompt:
                return numeric_key

        return None

    @staticmethod
    def _resolve_node_id_in_trace(node_id, trace_tree):
        if node_id is None:
            return None

        if node_id in trace_tree:
            return node_id

        candidate = str(node_id)
        if candidate in trace_tree:
            return candidate

        parts = candidate.split(".")
        if len(parts) > 1:
            for i in range(len(parts) - 1, 0, -1):
                prefix = ".".join(parts[:i])
                if prefix in trace_tree:
                    return prefix

            for i in range(len(parts) - 1, 0, -1):
                suffix = ".".join(parts[-i:])
                if suffix in trace_tree:
                    return suffix

        if candidate.isdigit():
            numeric_key = int(candidate)
            if numeric_key in trace_tree:
                return numeric_key

        return None

    @classmethod
    def trace(cls, start_node_id, prompt):
        resolved_start_id = cls._resolve_node_id(start_node_id, prompt)
        if resolved_start_id is None or resolved_start_id not in prompt:
            return {}

        trace_tree = {}
        queue = deque()
        start_class_type = prompt[resolved_start_id]["class_type"]
        trace_tree[resolved_start_id] = (0, start_class_type)
        queue.append((resolved_start_id, 0))

        while queue:
            current_node_id, distance = queue.popleft()
            prompt_node = prompt.get(current_node_id)
            if prompt_node is None:
                continue

            input_fields = prompt_node.get("inputs", {})
            for value in input_fields.values():
                if isinstance(value, list) and len(value) > 0:
                    raw_nid = value[0]
                    resolved_nid = cls._resolve_node_id(raw_nid, prompt)
                    if resolved_nid is None or resolved_nid in trace_tree:
                        continue

                    child_node = prompt.get(resolved_nid)
                    if child_node is None:
                        continue

                    class_type = child_node.get("class_type")
                    trace_tree[resolved_nid] = (distance + 1, class_type)
                    queue.append((resolved_nid, distance + 1))

        return trace_tree

    @classmethod
    def find_sampler_node_id(cls, trace_tree, sampler_selection_method, node_id):
        if sampler_selection_method == SAMPLER_SELECTION_METHOD[2]:
            resolved_node_id = cls._resolve_node_id_in_trace(node_id, trace_tree)
            if resolved_node_id is None:
                return -1

            _, class_type = trace_tree.get(resolved_node_id, (-1, None))
            if class_type in SAMPLERS.keys():
                return resolved_node_id
            return -1

        sorted_by_distance_trace_tree = sorted(
            [(k, v[0], v[1]) for k, v in trace_tree.items()],
            key=lambda x: x[1],
            reverse=(sampler_selection_method == SAMPLER_SELECTION_METHOD[0]),
        )
        for nid, _, class_type in sorted_by_distance_trace_tree:
            if class_type in SAMPLERS.keys():
                return nid
        return -1

    @classmethod
    def filter_inputs_by_trace_tree(cls, inputs, trace_tree):
        filtered_inputs = {}
        for meta, inputs_list in inputs.items():
            for node_id, input_value in inputs_list:
                resolved_node_id = cls._resolve_node_id_in_trace(node_id, trace_tree)
                if resolved_node_id is None:
                    continue

                trace = trace_tree.get(resolved_node_id)
                if trace is not None:
                    distance = trace[0]
                    if meta not in filtered_inputs:
                        filtered_inputs[meta] = []
                    filtered_inputs[meta].append((node_id, input_value, distance))

        # sort by distance
        for k, v in filtered_inputs.items():
            filtered_inputs[k] = sorted(v, key=lambda x: x[2])
        return filtered_inputs
