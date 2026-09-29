import asyncio
import logging

from app.services.max_bot import MaxBot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


async def main():
    bot = MaxBot()

    try:
        print("Запускаем MAX бота...")
        await bot.run_polling()
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())