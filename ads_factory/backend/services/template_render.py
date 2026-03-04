"""
Safe prompt template renderer.

Public API:
    render_template(template, variables) -> str

Rules:
- Only ``{{variable_name}}`` placeholders are substituted; no code execution.
- Raises ValueError if the template references a variable name not in KNOWN_VARS.
- All values are coerced to str; None → empty string.
"""
import re

# The complete set of variables an agent prompt template is allowed to use.
KNOWN_VARS: frozenset = frozenset({
    "project_name",
    "brand_name",
    "product_description",
    "offer_description",
    "brand_rules",
    "landing_summary_json",
    "language",
})


def render_template(template: str, variables: dict) -> str:
    """
    Replace every ``{{key}}`` token in *template* with ``variables[key]``.

    Unknown variable names raise ``ValueError`` — they most likely indicate a
    typo or an injection attempt.
    """
    referenced = set(re.findall(r"\{\{(\w+)\}\}", template))
    unknown = referenced - KNOWN_VARS
    if unknown:
        raise ValueError(
            f"Template references unknown variable(s): {sorted(unknown)}. "
            f"Allowed: {sorted(KNOWN_VARS)}"
        )

    result = template
    for key in referenced:
        val = variables.get(key)
        result = result.replace("{{" + key + "}}", str(val) if val is not None else "")
    return result
