import json
from datetime import date
from pathlib import Path

from app.database import SessionLocal, init_db
from app.models import Source, Item


SOURCE_NAME = "СП 2.3.6.4281-26"
SOURCE_LINK = "http://publication.pravo.gov.ru/document/0001202606020079"

DATA_FILE = Path(__file__).resolve().parent / "data" / "checklist_items.json"


def seed() -> None:
    init_db()

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Файл с требованиями не найден: {DATA_FILE}"
        )

    with DATA_FILE.open("r", encoding="utf-8") as file:
        items_data = json.load(file)

    if not isinstance(items_data, list):
        raise ValueError("checklist_items.json должен содержать JSON-массив")

    if len(items_data) != 84:
        raise ValueError(
            f"Ожидалось 84 требования, получено: {len(items_data)}"
        )

    source_points = [item["source_point"] for item in items_data]

    if source_points != list(range(3, 87)):
        raise ValueError(
            "source_point должны идти последовательно от 3 до 86"
        )

    db = SessionLocal()

    try:
        source = (
            db.query(Source)
            .filter(Source.name == SOURCE_NAME)
            .first()
        )

        if source is None:
            source = Source(
                name=SOURCE_NAME,
                link=SOURCE_LINK,
                valid_from=date(2026, 9, 1),
                valid_to=date(2032, 9, 1),
            )
            db.add(source)
            db.flush()

        existing_items = db.query(Item).count()

        if existing_items > 0:
            print(
                f"SEED SKIPPED: в таблице items уже есть записи: "
                f"{existing_items}"
            )
            return

        for data in items_data:
            db.add(
                Item(
                    requirement=data["requirement"],
                    chapter=data["chapter"],
                    chapter_title=data["chapter_title"],
                    source_point=data["source_point"],
                    recommendation=data["recommendation"],
                    source_id=source.id,
                    priority=data.get("priority"),
                )
            )

        db.commit()

        print("SEED OK")
        print(f"Источник: {SOURCE_NAME}")
        print(f"Добавлено требований: {len(items_data)}")
        print(
            f"Диапазон пунктов: "
            f"{items_data[0]['source_point']}–"
            f"{items_data[-1]['source_point']}"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()