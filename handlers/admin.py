from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
import io
from database import get_user_count, get_all_users_data
from config import ADMIN_IDS

router = Router()

@router.message(Command("stats"))
async def stats_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    count = get_user_count()
    await message.answer(f"Количество пользователей в боте: {count}")

@router.message(Command("list_users"))
async def list_users(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    rows = get_all_users_data()
    if not rows:
        await message.answer("Пока что никто не зарегистрирован.")
        return
    buffer = io.BytesIO()
    for row in rows:
        user_id_db = row[0]
        line = f"{user_id_db}\n"
        buffer.write(line.encode("utf-8"))
    buffer.seek(0)
    file_bytes = buffer.getvalue()
    file_to_send = BufferedInputFile(file=file_bytes, filename="user_ids.txt")
    await message.answer_document(document=file_to_send)