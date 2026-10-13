from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

T = TypeVar("T")

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
MediumText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)]
# Year-month as "YYYY-MM" (or just "YYYY" when the month is unknown).
YearMonth = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$")]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class Message(BaseModel):
    message: str


class TaskRef(BaseModel):
    task_id: str
    status: str


def page_count(total: int, page_size: int) -> int:
    return max(1, -(-total // page_size))


__all__ = ["ApiModel", "Field", "LongText", "MediumText", "Message", "Page", "ShortText", "TaskRef", "YearMonth", "page_count"]
