from typing import Dict, List

from app.domain.skeletons.models import ParameterValidationResult


class ParameterValidator:
    """Lightweight JSON Schema parameter validator.

    Checks required fields and type constraints without external dependencies.
    """

    def validate(self, schema: dict, params: dict) -> ParameterValidationResult:
        errors: List[Dict[str, str]] = []

        required: list = schema.get("required", [])
        properties: dict = schema.get("properties", {})

        for field in required:
            val = params.get(field)
            if val is None or val == "":
                errors.append({
                    "field": field,
                    "error": f"Required field '{field}' is missing or empty",
                })

        for field_name, field_schema in properties.items():
            val = params.get(field_name)
            if val is None or val == "":
                continue
            expected_type = field_schema.get("type", "string")
            if not self._check_type(expected_type, val):
                errors.append({
                    "field": field_name,
                    "error": (
                        f"Expected type '{expected_type}' for field "
                        f"'{field_name}', got '{type(val).__name__}'"
                    ),
                })

        return ParameterValidationResult(
            valid=len(errors) == 0,
            errors=errors,
        )

    @staticmethod
    def _check_type(expected_type: str, value) -> bool:
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type == "boolean":
            return isinstance(value, bool)
        return True
