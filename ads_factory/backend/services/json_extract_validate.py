"""
JSON extraction and schema validation helpers.

Public API:
    extract_first_json(text) -> dict | list | None
    validate_json(obj, schema_text)  # raises jsonschema.ValidationError on mismatch
"""
import json
import re


def extract_first_json(text: str):
    """
    Extract the first valid JSON object or array from *text*.

    Handles:
    - Plain JSON responses
    - JSON wrapped in markdown code fences (```json ... ```)
    - JSON embedded in prose (searches for outermost { } or [ ])

    Returns the parsed Python object, or None if nothing could be found.
    """
    # Strip markdown code fences the model may have added
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned.strip(), flags=re.MULTILINE)

    # Fast path: the whole text is valid JSON
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass

    # Fall back: find the outermost { … } or [ … ] block
    for pattern in (r"(\{[\s\S]*\})", r"(\[[\s\S]*\])"):
        m = re.search(pattern, cleaned)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue

    return None


def validate_json(obj, schema_text: str) -> None:
    """
    Validate *obj* against the JSON Schema in *schema_text*.

    Raises:
        json.JSONDecodeError   if schema_text is not valid JSON
        jsonschema.ValidationError  if obj does not conform to the schema
    """
    import jsonschema

    schema = json.loads(schema_text)
    jsonschema.validate(instance=obj, schema=schema)
