"""
Safe template renderer for agent user_prompt_template fields.
Only supports {{variable}} substitution — no code execution.
"""
import re

# The full set of variables a prompt template is allowed to reference.
KNOWN_VARS: frozenset = frozenset({
    "brand_name",
    "brand_rules",
    "product_description",
    "offer_description",
    "landing_summary_json",
    "language",
    "project_name",
})


def render(template: str, variables: dict) -> str:
    """
    Replace every ``{{key}}`` token in *template* with the corresponding
    value from *variables*.

    Raises ``ValueError`` if the template references a variable name that is
    not in ``KNOWN_VARS``.  Unknown variable names most likely indicate a
    typo or an injection attempt, so we reject them early.
    """
    referenced = set(re.findall(r"\{\{(\w+)\}\}", template))
    unknown = referenced - KNOWN_VARS
    if unknown:
        raise ValueError(
            f"Template references unknown variable(s): {sorted(unknown)}. "
            f"Allowed variables: {sorted(KNOWN_VARS)}"
        )

    result = template
    for key in referenced:
        val = variables.get(key)
        result = result.replace("{{" + key + "}}", str(val) if val is not None else "")
    return result
