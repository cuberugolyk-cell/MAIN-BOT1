import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
import user
import admin
import payments


async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(payments.router)
    dp.include_router(user.router)

    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
