from datetime import date, datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    ForeignKey,
    UniqueConstraint,
    String,
    Text,
    Date,
    DateTime,
    Boolean,
    Integer,
    BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    """Вспомогательная функция для получения текущего времени в UTC (стандарт Python 3.12)."""
    return datetime.now(timezone.utc)


class Business(Base):
    """Бизнес пользователя MAX. Один пользователь может иметь несколько бизнесов."""
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)

    # user_id MAX - идентификатор владельца бизнеса.
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Пока единственное поддерживаемое значение - "food_retail".
    type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
    )

    checklists: Mapped[List["Checklist"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )

    reminders: Mapped[List["Reminder"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )


class Source(Base):
    """Нормативный источник (например, СП 2.3.6.4281-26)."""
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    link: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )

    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    # Может быть пустым, если дата окончания действия не указана
    # в данных источника.
    valid_to: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    items: Mapped[List["Item"]] = relationship(
        back_populates="source",
    )


class Item(Base):
    """
    Требование чек-листа. Данные заранее подготовлены на основе нормативного
    источника - backend их только хранит и отдаёт, ничего не генерирует.
    """
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)

    requirement: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    chapter: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    chapter_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source_point: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id"),
        nullable=False,
    )

    # Приоритет требования. В MVP может не использоваться.
    priority: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    source: Mapped["Source"] = relationship(
        back_populates="items",
    )

    checklist_items: Mapped[List["ChecklistItem"]] = relationship(
        back_populates="item",
    )


class Checklist(Base):
    """Конкретная проверка бизнеса (прохождение чек-листа)."""
    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(primary_key=True)

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Статусы: draft | finished_early | completed.
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    business: Mapped["Business"] = relationship(
        back_populates="checklists",
    )

    checklist_items: Mapped[List["ChecklistItem"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
    )


class ChecklistItem(Base):
    """
    Ответ пользователя на конкретное требование в рамках конкретной проверки.
    Уникальная пара (checklist_id, item_id) - один пункт не может иметь
    два ответа.
    """
    __tablename__ = "checklist_items"

    __table_args__ = (
        UniqueConstraint(
            "checklist_id",
            "item_id",
            name="uq_checklist_item",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    checklist_id: Mapped[int] = mapped_column(
        ForeignKey("checklists.id", ondelete="CASCADE"),
        nullable=False,
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id"),
        nullable=False,
    )

    # yes / no / unknown / not_applicable / None.
    # None = пункт ещё не проверен.
    result: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )

    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    checklist: Mapped["Checklist"] = relationship(
        back_populates="checklist_items",
    )

    item: Mapped["Item"] = relationship(
        back_populates="checklist_items",
    )

    files: Mapped[List["StoredFile"]] = relationship(
        back_populates="checklist_item",
        cascade="all, delete-orphan",
    )


class StoredFile(Base):
    """Фотография, прикреплённая к конкретному ответу (checklist_item)."""
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)

    checklist_item_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    file_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )

    checklist_item: Mapped["ChecklistItem"] = relationship(
        back_populates="files",
    )


class Reminder(Base):
    """Настройки напоминаний о повторной самопроверке бизнеса."""
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    period_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    last_notification_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    next_notification_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    business: Mapped["Business"] = relationship(
        back_populates="reminders",
    )