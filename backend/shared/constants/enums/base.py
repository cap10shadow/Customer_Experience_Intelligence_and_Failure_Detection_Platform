from enum import Enum
from typing import List, Any

class BaseStringEnum(str, Enum):
    """
    Base string enumeration class that provides centralized string serialization,
    helper utilities, and cross-framework compatibility (SQLAlchemy, FastAPI, Pydantic).
    """

    def __str__(self) -> str:
        """Ensure string representation returns the value directly for seamless serialization."""
        return str(self.value)
        
    @classmethod
    def values(cls) -> List[str]:
        """Utility method to get a list of all enum values. Useful for validation."""
        return [member.value for member in cls]
        
    @classmethod
    def has_value(cls, value: Any) -> bool:
        """Utility method to check if a value exists within the enum bounds."""
        return value in cls.values()
