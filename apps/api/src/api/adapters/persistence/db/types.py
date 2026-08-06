"""SQLAlchemy mappings for domain value objects."""

from enum import StrEnum

from sqlalchemy import Enum


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_type]


def string_enum(enum_type: type[StrEnum], name: str) -> Enum:
    """Persist a StrEnum as a length-checked varchar guarded by a named check constraint."""
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=16,
        values_callable=enum_values,
    )
