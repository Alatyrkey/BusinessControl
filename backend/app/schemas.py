from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Ответ проверки состояния API."""

    status: str
    service: str


class PingResponse(BaseModel):
    """Ответ проверки доступности API."""

    message: str


# =========================
# Businesses
# =========================

class BusinessCreate(BaseModel):
    """Данные для создания бизнеса."""

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    business_type: str = Field(
        min_length=1,
        max_length=64,
    )


class BusinessResponse(BaseModel):
    """Бизнес, возвращаемый API."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    user_id: int
    name: str
    type: str
    created_at: datetime
    updated_at: datetime


# =========================
# Checklists
# =========================

class ChecklistCreate(BaseModel):
    """Данные для создания новой проверки."""

    business_id: int = Field(
        gt=0,
    )


class ChecklistResponse(BaseModel):
    """Чек-лист, возвращаемый API."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    business_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class StoredFileResponse(BaseModel):
    """Фотография, прикреплённая к пункту проверки."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    checklist_item_id: int
    file_url: str
    uploaded_at: datetime


class ChecklistItemResponse(BaseModel):
    """Пункт проверки вместе с нормативным требованием."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    checklist_id: int
    item_id: int

    result: str | None
    comment: str | None

    requirement: str
    chapter: str
    chapter_title: str
    source_point: str
    recommendation: str
    source_id: int

    files: list[StoredFileResponse] = Field(
        default_factory=list,
    )


class ChecklistItemUpdate(BaseModel):
    """Ответ пользователя на пункт проверки."""

    result: Literal[
        "yes",
        "no",
        "unknown",
        "not_applicable",
    ]

    comment: str | None = Field(
        default=None,
        max_length=5000,
    )


class UnfinishedChecklistResponse(BaseModel):
    """Незавершённая проверка для продолжения."""

    checklist_id: int
    business_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    items: list[ChecklistItemResponse]


# =========================
# Checklist results
# =========================

class ChecklistResult(BaseModel):
    """Результат проверки."""

    checklist_id: int
    status: str

    checked: int
    total: int
    remaining: int

    yes: int
    no: int
    unknown: int
    not_applicable: int


# =========================
# Checklist result details
# =========================

class ChecklistResultItem(BaseModel):
    """Один проблемный или неопределённый пункт."""

    checklist_item_id: int
    item_id: int
    result: str
    requirement: str
    chapter: str
    chapter_title: str
    source_point: str
    recommendation: str
    source_id: int
    source_name: str
    source_link: str | None


class ChecklistChapterResult(BaseModel):
    """Итог по одной главе."""

    chapter: str
    chapter_title: str
    checked: int
    yes: int
    no: int
    unknown: int
    not_applicable: int


class ChecklistResultDetails(BaseModel):
    """Подробный результат проверки."""

    checklist_id: int
    status: str
    checked: int
    total: int
    remaining: int

    yes: int
    no: int
    unknown: int
    not_applicable: int

    violations: list[ChecklistResultItem]
    unknown_items: list[ChecklistResultItem]
    chapters: list[ChecklistChapterResult]