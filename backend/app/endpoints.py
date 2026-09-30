from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models import (
    Business,
    Checklist,
    ChecklistItem,
    Item,
    Reminder,
    StoredFile,
)
from app.schemas import (
    BusinessCreate,
    BusinessResponse,
    ChecklistItemResponse,
    ChecklistItemUpdate,
    ChecklistResponse,
    ChecklistResult,
    ChecklistResultDetails,
    ChecklistResultItem,
    ChecklistChapterResult,
    PingResponse,
    StoredFileResponse,
    UnfinishedChecklistResponse,
)


router = APIRouter()


# =========================
# Files
# =========================

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ


# =========================
# Service
# =========================

@router.get(
    "/ping",
    response_model=PingResponse,
    tags=["service"],
)
def ping() -> PingResponse:
    """Проверяет, что API-роутер доступен и подключён."""

    return PingResponse(
        message="pong",
    )


# =========================
# Businesses
# =========================

@router.post(
    "/businesses",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["businesses"],
)
def create_business(
    payload: BusinessCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> BusinessResponse:
    """Создаёт бизнес для текущего пользователя MAX."""

    business = Business(
        user_id=user_id,
        name=payload.name,
        type=payload.business_type,
    )

    try:
        db.add(business)
        db.commit()
        db.refresh(business)
    except SQLAlchemyError:
        db.rollback()
        raise

    return business


@router.get(
    "/businesses",
    response_model=list[BusinessResponse],
    tags=["businesses"],
)
def get_businesses(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[BusinessResponse]:
    """Возвращает бизнесы текущего пользователя MAX с актуальным прогрессом."""

    businesses = (
        db.query(Business)
        .filter(Business.user_id == user_id)
        .order_by(Business.id)
        .all()
    )

    result = []

    for business in businesses:
        active_checklist = (
            db.query(Checklist)
            .filter(
                Checklist.business_id == business.id,
                Checklist.status.in_(["draft", "finished_early"]),
            )
            .order_by(Checklist.updated_at.desc(), Checklist.id.desc())
            .first()
        )

        last_result = (
            db.query(Checklist)
            .filter(
                Checklist.business_id == business.id,
                Checklist.status.in_(["completed", "finished_early"]),
            )
            .order_by(Checklist.updated_at.desc(), Checklist.id.desc())
            .first()
        )

        checked = 0
        violations = 0
        unknown = 0

        if active_checklist is not None:
            items = (
                db.query(ChecklistItem)
                .filter(ChecklistItem.checklist_id == active_checklist.id)
                .all()
            )

            checked = sum(1 for item in items if item.result is not None)
            violations = sum(1 for item in items if item.result == "no")
            unknown = sum(1 for item in items if item.result == "unknown")

        business.checked = checked
        business.violations = violations
        business.unknown = unknown
        business.active_checklist_id = (
            active_checklist.id if active_checklist else None
        )
        business.active_status = (
            active_checklist.status if active_checklist else None
        )
        business.last_result_checklist_id = (
            last_result.id if last_result else None
        )
        business.last_result_status = (
            last_result.status if last_result else None
        )
        business.last_result_at = (
            last_result.completed_at or last_result.updated_at
            if last_result
            else None
        )

        result.append(business)

    return result

@router.delete(
    "/businesses/{business_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["businesses"],
)
def delete_business(
    business_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Удаляет бизнес текущего пользователя вместе со связанными данными."""

    business = (
        db.query(Business)
        .filter(
            Business.id == business_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бизнес не найден",
        )

    # Собираем физические файлы фотографий до удаления связанных записей из БД.
    files_to_delete: list[Path] = []

    for checklist in business.checklists:
        for checklist_item in checklist.checklist_items:
            for stored_file in checklist_item.files:
                filename = Path(stored_file.file_url).name

                if filename:
                    files_to_delete.append(
                        settings.UPLOAD_DIR / filename
                    )

    try:
        db.delete(business)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    # Удаляем физические файлы после успешного удаления из БД.
    for file_path in files_to_delete:
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass

# =========================
# Checklists
# =========================

@router.post(
    "/businesses/{business_id}/checklists",
    response_model=ChecklistResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["checklists"],
)
def create_checklist(
    business_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ChecklistResponse:
    """
    Создаёт новую проверку для бизнеса пользователя.

    Все доступные нормативные пункты из таблицы items
    добавляются в эту проверку.
    """

    business = (
        db.query(Business)
        .filter(
            Business.id == business_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бизнес не найден",
        )

        # Если у бизнеса уже есть незавершённая проверка,
    # новую не создаём — продолжаем существующую.
    existing_checklist = (
        db.query(Checklist)
        .filter(
            Checklist.business_id == business.id,
            Checklist.status.in_(["draft", "finished_early"]),
        )
        .order_by(
            Checklist.updated_at.desc(),
            Checklist.id.desc(),
        )
        .first()
    )

    if existing_checklist is not None:
        return existing_checklist

    items = (
        db.query(Item)
        .order_by(Item.id)
        .all()
    )

    if not items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="В системе пока нет пунктов чек-листа",
        )

    checklist = Checklist(
        business_id=business.id,
        status="draft",
    )

    try:
        db.add(checklist)
        db.flush()

        for item in items:
            checklist_item = ChecklistItem(
                checklist_id=checklist.id,
                item_id=item.id,
                result=None,
                comment=None,
            )

            db.add(checklist_item)

        db.commit()
        db.refresh(checklist)

    except SQLAlchemyError:
        db.rollback()
        raise

    return checklist


@router.get(
    "/checklists/{checklist_id}",
    response_model=list[ChecklistItemResponse],
    tags=["checklists"],
)
def get_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[ChecklistItemResponse]:
    """Возвращает пункты проверки с нормативными требованиями."""

    checklist = (
        db.query(Checklist)
        .join(Business)
        .filter(
            Checklist.id == checklist_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проверка не найдена",
        )

    checklist_items = (
        db.query(ChecklistItem)
        .options(
            joinedload(ChecklistItem.item),
        )
        .filter(
            ChecklistItem.checklist_id == checklist.id,
        )
        .order_by(ChecklistItem.id)
        .all()
    )

    result = []

    for checklist_item in checklist_items:
        item = checklist_item.item

        result.append(
            ChecklistItemResponse(
                id=checklist_item.id,
                checklist_id=checklist_item.checklist_id,
                item_id=checklist_item.item_id,
                result=checklist_item.result,
                comment=checklist_item.comment,
                requirement=item.requirement,
                chapter=item.chapter,
                chapter_title=item.chapter_title,
                source_point=item.source_point,
                recommendation=item.recommendation,
                source_id=item.source_id,
            )
        )

    return result


# =========================
# Resume
# =========================

@router.get(
    "/businesses/{business_id}/checklists/unfinished",
    response_model=UnfinishedChecklistResponse | None,
    tags=["checklists"],
)
def get_unfinished_checklist(
    business_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> UnfinishedChecklistResponse | None:
    """
    Возвращает последнюю незавершённую проверку бизнеса.

    Если незавершённой проверки нет, возвращает null.
    """

    business = (
        db.query(Business)
        .filter(
            Business.id == business_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бизнес не найден",
        )

    checklist = (
        db.query(Checklist)
        .filter(
            Checklist.business_id == business.id,
            Checklist.status.in_(["draft", "finished_early"]),
        )
        .order_by(Checklist.updated_at.desc(), Checklist.id.desc())
        .first()
    )

    if checklist is None:
        return None

    checklist_items = (
        db.query(ChecklistItem)
        .options(
            joinedload(ChecklistItem.item),
            joinedload(ChecklistItem.files),
        )
        .filter(
            ChecklistItem.checklist_id == checklist.id,
        )
        .order_by(ChecklistItem.id)
        .all()
    )

    items = []

    for checklist_item in checklist_items:
        item = checklist_item.item

        items.append(
            ChecklistItemResponse(
                id=checklist_item.id,
                checklist_id=checklist_item.checklist_id,
                item_id=checklist_item.item_id,
                result=checklist_item.result,
                comment=checklist_item.comment,
                requirement=item.requirement,
                chapter=item.chapter,
                chapter_title=item.chapter_title,
                source_point=item.source_point,
                recommendation=item.recommendation,
                source_id=item.source_id,
                files=checklist_item.files,
            )
        )

    return UnfinishedChecklistResponse(
        checklist_id=checklist.id,
        business_id=checklist.business_id,
        status=checklist.status,
        created_at=checklist.created_at,
        updated_at=checklist.updated_at,
        items=items,
    )


@router.patch(
    "/checklist-items/{checklist_item_id}",
    response_model=ChecklistItemResponse,
    tags=["checklists"],
)
def update_checklist_item(
    checklist_item_id: int,
    payload: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ChecklistItemResponse:
    """Сохраняет ответ пользователя на пункт проверки."""

    checklist_item = (
        db.query(ChecklistItem)
        .join(Checklist)
        .join(Business)
        .filter(
            ChecklistItem.id == checklist_item_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if checklist_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пункт проверки не найден",
        )

    if checklist_item.checklist.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Проверка уже завершена",
        )

    checklist_item.result = payload.result
    checklist_item.comment = payload.comment

    if checklist_item.checklist.status == "finished_early":
        checklist_item.checklist.status = "draft"

    try:
        db.commit()
        db.refresh(checklist_item)
    except SQLAlchemyError:
        db.rollback()
        raise

    item = checklist_item.item

    return ChecklistItemResponse(
        id=checklist_item.id,
        checklist_id=checklist_item.checklist_id,
        item_id=checklist_item.item_id,
        result=checklist_item.result,
        comment=checklist_item.comment,
        requirement=item.requirement,
        chapter=item.chapter,
        chapter_title=item.chapter_title,
        source_point=item.source_point,
        recommendation=item.recommendation,
        source_id=item.source_id,
    )


# =========================
# Checklist files
# =========================

@router.post(
    "/checklist-items/{checklist_item_id}/files",
    response_model=StoredFileResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["files"],
)
async def upload_checklist_item_file(
    checklist_item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> StoredFileResponse:
    """
    Загружает фотографию к конкретному пункту проверки.

    Файл можно прикрепить только к пункту проверки,
    принадлежащей текущему пользователю MAX.
    """

    checklist_item = (
        db.query(ChecklistItem)
        .join(Checklist)
        .join(Business)
        .filter(
            ChecklistItem.id == checklist_item_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if checklist_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пункт проверки не найден",
        )

    if checklist_item.checklist.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Проверка уже завершена",
        )

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Разрешены только изображения JPEG, PNG и WebP",
        )

    file_data = await file.read()

    if len(file_data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Размер файла не должен превышать 10 МБ",
        )

    if len(file_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл пустой",
        )

    extension_by_type = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    extension = extension_by_type[file.content_type]
    filename = f"{uuid4().hex}{extension}"

    upload_dir = Path(settings.UPLOAD_DIR)

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = upload_dir / filename

    try:
        file_path.write_bytes(file_data)

    except OSError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить файл",
        )

    try:
        stored_file = StoredFile(
            checklist_item_id=checklist_item.id,
            file_url=f"/api/files/{filename}",
        )

        db.add(stored_file)
        db.commit()
        db.refresh(stored_file)

    except SQLAlchemyError:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise

    return StoredFileResponse(
        id=stored_file.id,
        checklist_item_id=stored_file.checklist_item_id,
        file_url=stored_file.file_url,
        uploaded_at=stored_file.uploaded_at,
    )


@router.get(
    "/checklist-items/{checklist_item_id}/files",
    response_model=list[StoredFileResponse],
    tags=["files"],
)
def get_checklist_item_files(
    checklist_item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[StoredFileResponse]:
    """Возвращает файлы, прикреплённые к пункту проверки."""

    checklist_item = (
        db.query(ChecklistItem)
        .join(Checklist)
        .join(Business)
        .filter(
            ChecklistItem.id == checklist_item_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if checklist_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пункт проверки не найден",
        )

    return checklist_item.files


@router.get(
    "/files/{filename}",
    response_class=FileResponse,
    tags=["files"],
)
def get_file(
    filename: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> FileResponse:
    """Отдаёт файл с диска, если он принадлежит текущему пользователю."""

    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден",
        )

    stored_file = (
        db.query(StoredFile)
        .join(ChecklistItem)
        .join(Checklist)
        .join(Business)
        .filter(
            StoredFile.file_url == f"/api/files/{filename}",
            Business.user_id == user_id,
        )
        .first()
    )

    if stored_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден",
        )

    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    file_path = (upload_dir / filename).resolve()

    if upload_dir not in file_path.parents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден на диске",
        )

    return FileResponse(file_path)


@router.delete(
    "/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["files"],
)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> None:
    """Удаляет фотографию, если она принадлежит текущему пользователю."""

    stored_file = (
        db.query(StoredFile)
        .join(ChecklistItem)
        .join(Checklist)
        .join(Business)
        .filter(
            StoredFile.id == file_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if stored_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден",
        )

    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    file_path = (upload_dir / Path(stored_file.file_url).name).resolve()

    if upload_dir not in file_path.parents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден",
        )

    try:
        db.delete(stored_file)
        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise

    file_path.unlink(missing_ok=True)


# =========================
# Checklist finish
# =========================

@router.post(
    "/checklists/{checklist_id}/finish",
    response_model=ChecklistResult,
    tags=["checklists"],
)
def finish_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ChecklistResult:
    """
    Завершает проверку.

    Если проверены не все пункты — finished_early.
    Если проверены все пункты — completed.
    """

    checklist = (
        db.query(Checklist)
        .join(Business)
        .filter(
            Checklist.id == checklist_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проверка не найдена",
        )

    if checklist.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Проверка уже завершена",
        )

    checklist_items = (
        db.query(ChecklistItem)
        .filter(
            ChecklistItem.checklist_id == checklist.id,
        )
        .all()
    )

    total = len(checklist_items)

    checked = sum(
        item.result is not None
        for item in checklist_items
    )

    yes = sum(
        item.result == "yes"
        for item in checklist_items
    )

    no = sum(
        item.result == "no"
        for item in checklist_items
    )

    unknown = sum(
        item.result == "unknown"
        for item in checklist_items
    )

    not_applicable = sum(
        item.result == "not_applicable"
        for item in checklist_items
    )

    remaining = total - checked

    if checked == total:
        checklist.status = "completed"
    else:
        checklist.status = "finished_early"

    now = datetime.now(timezone.utc)

    if checklist.status == "completed":
        checklist.completed_at = now

        reminder = (
            db.query(Reminder)
            .filter(
                Reminder.business_id == checklist.business_id,
            )
            .first()
        )

        if reminder is None:
            reminder = Reminder(
                business_id=checklist.business_id,
                is_active=True,
                period_days=30,
                last_notification_at=None,
                next_notification_at=now + timedelta(minutes=1),
            )
            db.add(reminder)
        else:
            reminder.is_active = True
            reminder.period_days = 30
            reminder.next_notification_at = now + timedelta(minutes=1)
    try:
        db.commit()
        db.refresh(checklist)

    except SQLAlchemyError:
        db.rollback()
        raise

    return ChecklistResult(
        checklist_id=checklist.id,
        status=checklist.status,
        checked=checked,
        total=total,
        remaining=remaining,
        yes=yes,
        no=no,
        unknown=unknown,
        not_applicable=not_applicable,
    )


# =========================
# Checklist result details
# =========================

@router.get(
    "/checklists/{checklist_id}/result",
    response_model=ChecklistResultDetails,
    tags=["checklists"],
)
def get_checklist_result(
    checklist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ChecklistResultDetails:
    """Возвращает подробный результат проверки."""

    checklist = (
        db.query(Checklist)
        .join(Business)
        .filter(
            Checklist.id == checklist_id,
            Business.user_id == user_id,
        )
        .first()
    )

    if checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проверка не найдена",
        )

    checklist_items = (
        db.query(ChecklistItem)
        .options(
            joinedload(ChecklistItem.item).joinedload(Item.source),
        )
        .filter(
            ChecklistItem.checklist_id == checklist.id,
        )
        .order_by(ChecklistItem.id)
        .all()
    )

    total = len(checklist_items)

    checked = sum(
        item.result is not None
        for item in checklist_items
    )

    yes = sum(
        item.result == "yes"
        for item in checklist_items
    )

    no = sum(
        item.result == "no"
        for item in checklist_items
    )

    unknown = sum(
        item.result == "unknown"
        for item in checklist_items
    )

    not_applicable = sum(
        item.result == "not_applicable"
        for item in checklist_items
    )

    remaining = total - checked

    violations: list[ChecklistResultItem] = []
    unknown_items: list[ChecklistResultItem] = []

    chapter_data: dict[str, dict] = {}

    for checklist_item in checklist_items:
        item = checklist_item.item

        if item.chapter not in chapter_data:
            chapter_data[item.chapter] = {
                "chapter": item.chapter,
                "chapter_title": item.chapter_title,
                "checked": 0,
                "yes": 0,
                "no": 0,
                "unknown": 0,
                "not_applicable": 0,
            }

        chapter = chapter_data[item.chapter]

        if checklist_item.result is not None:
            chapter["checked"] += 1

        if checklist_item.result == "yes":
            chapter["yes"] += 1

        elif checklist_item.result == "no":
            chapter["no"] += 1

        elif checklist_item.result == "unknown":
            chapter["unknown"] += 1

        elif checklist_item.result == "not_applicable":
            chapter["not_applicable"] += 1

        if checklist_item.result not in {"no", "unknown"}:
            continue

        result_item = ChecklistResultItem(
            checklist_item_id=checklist_item.id,
            item_id=item.id,
            result=checklist_item.result,
            requirement=item.requirement,
            chapter=item.chapter,
            chapter_title=item.chapter_title,
            source_point=item.source_point,
            recommendation=item.recommendation,
            source_id=item.source_id,
            source_name=item.source.name,
            source_link=item.source.link,
        )

        if checklist_item.result == "no":
            violations.append(result_item)

        elif checklist_item.result == "unknown":
            unknown_items.append(result_item)

    chapters = [
        ChecklistChapterResult(**chapter)
        for chapter in chapter_data.values()
    ]

    return ChecklistResultDetails(
        checklist_id=checklist.id,
        status=checklist.status,
        checked=checked,
        total=total,
        remaining=remaining,
        yes=yes,
        no=no,
        unknown=unknown,
        not_applicable=not_applicable,
        violations=violations,
        unknown_items=unknown_items,
        chapters=chapters,
    )