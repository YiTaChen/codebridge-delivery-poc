"""Provider-neutral observations. The model reads; Python reconciles."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PackingRow(StrictModel):
    row_id: str = Field(min_length=1, max_length=30)
    source_line: int = Field(ge=1)
    sku: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=160)
    expected_qty: int = Field(ge=0, le=999)


class Observation(StrictModel):
    object_id: str | None
    sku_read: str | None
    label_read: str | None
    photo_id: str
    region_description: str = Field(min_length=1, max_length=500)
    visibility: Literal["clear", "obscured", "unreadable"]
    confidence_note: str = Field(max_length=500)
    related_row_id: str | None


class ModelReading(StrictModel):
    rows: list[PackingRow] = Field(min_length=1, max_length=5)
    observations: list[Observation] = Field(max_length=100)
    warnings: list[str] = Field(max_length=20)


def strict_json_schema() -> dict:
    """Codex/OpenAI require every property required, including nullable fields."""
    return ModelReading.model_json_schema()
