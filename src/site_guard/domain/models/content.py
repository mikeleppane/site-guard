import fnmatch

from pydantic import BaseModel, StrictBool, field_validator


class ContentRequirement(BaseModel, validate_assignment=True):
    """A single content requirement with optional wildcard support."""

    pattern: str
    use_wildcards: StrictBool = False
    case_sensitive: StrictBool = True

    model_config = {"frozen": True}

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content requirement pattern cannot be empty")
        return v.strip()

    def matches(self, content: str) -> bool:
        """Check if content matches this requirement."""
        text_to_check = content if self.case_sensitive else content.lower()
        pattern_to_use = self.pattern if self.case_sensitive else self.pattern.lower()

        if self.use_wildcards:
            return fnmatch.fnmatch(text_to_check, pattern_to_use)
        return pattern_to_use in text_to_check
