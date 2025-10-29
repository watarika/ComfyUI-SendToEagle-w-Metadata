# Style and Conventions
- Follow PEP 8 style: snake_case for functions/variables, CamelCase for classes, spaces around operators.
- Limited use of type hints; rely on docstrings/comments sparingly, add explanatory comments only for non-obvious logic.
- Metadata keys and constants live in `py/defs`; reuse existing helpers in `BaseNode` instead of ad-hoc logic.
- Keep strings ASCII unless interacting with ComfyUI metadata that already contains UTF-8 content.