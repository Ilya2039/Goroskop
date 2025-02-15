import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import API_TOKEN
from handlers import start, admin, horoscope, consultation, payment, mailing
from database import init_db

def main():
    logging.basicConfig(level=logging.INFO)

    init_db()
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(horoscope.router)
    dp.include_router(consultation.router)
    dp.include_router(payment.router)
    dp.include_router(mailing.router)
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    main()