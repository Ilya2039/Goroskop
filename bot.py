import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import sqlite3
import json  # ВАЖНО: для json.loads
from google import genai

# 🔹 Настройки
API_TOKEN = '7584759675:AAGMKdKTRMjaC0Rc1g-Ysw-5J2dlniIQdAA'
MINI_APP_URL = 'https://a67f-79-127-211-218.ngrok-free.app'  # Ссылка на мини-приложение
GEMINI_API_KEY = "AIzaSyCqE4taBEs1GJUh_pJQUqdGgcSEfGL8Pbc"  # Укажите ваш API-ключ Gemini

# 🔹 Инициализация бота и Gemini API
bot = telebot.TeleBot(API_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# 🔹 База данных SQLite
DB_NAME = "users.db"

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name, last_name):
    """Добавление пользователя в базу данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, last_name))
        conn.commit()
    except sqlite3.IntegrityError:
        # Если пользователь уже есть
        pass
    
    conn.close()

# 🔹 Инициализируем базу данных
init_db()

# 🔹 Карты и их значения
tarot_meanings = {
    1: "Огонь",
    2: "Вода",
    3: "Земля",
    4: "Воздух",
    5: "Сила",
    6: "Мудрость",
    7: "Любовь",
    8: "Дом"
}

# Словарь для хранения выбранных карт пользователей
user_cards = {}

# 🔹 Команда /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Добавляем пользователя в БД
    add_user(user_id, username, first_name, last_name)

    # Кнопка для мини-приложения
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔮 Выбрать карты Таро", web_app=WebAppInfo(url=MINI_APP_URL)))

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Привет, {first_name}! Нажми на кнопку, чтобы запустить мини-приложение и выбрать свои карты таро:",
        reply_markup=keyboard
    )

@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    print(">>> web_app_data handler TRIGGERED!")
    user_id = message.chat.id

    try:
        # Данные, пришедшие из tg.sendData(...) (JSON-строка)
        selected_cards_json = message.web_app_data.data
        selected_cards = json.loads(selected_cards_json)  # Превращаем JSON в список

        # Например selected_cards = ["Таро1.jpg", "Таро5.jpg", "Таро3.jpg"]

        # Преобразуем имена файлов в номера карт (1..8)
        # Ищем совпадение по шаблону: "Таро{номер}.jpg"
        numbers = []
        for filename in selected_cards:
            # Из "Таро1.jpg" достаём 1
            # Можно регуляркой, но можно проще:
            # вырезать "Таро" и ".jpg": "1"
            num_str = filename.replace("Таро", "").replace(".jpg", "")
            # Пробуем привести к int
            try:
                num = int(num_str)
                numbers.append(num)
            except:
                pass

        if len(numbers) != 3:
            bot.send_message(user_id, "❌ Не удалось определить выбранные карты.")
            return

        # Получаем значения карт по номерам
        selected_meanings = []
        for num in numbers:
            meaning = tarot_meanings.get(num)
            if meaning:
                selected_meanings.append(meaning)

        if len(selected_meanings) != 3:
            bot.send_message(user_id, "❌ Ошибка в определении карт.")
            return

        # Формируем запрос в Gemini
        query = (
            f"Карты таро показали человеку {', '.join(selected_meanings)}. "
            f"Какое значение это может иметь? Дай ответ до 800 символов."
        )
        print("🔍 Запрос в Gemini:", query)

        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=query
            )

            if hasattr(response, "text") and response.text:
                answer = response.text.strip()
            else:
                answer = "❌ Gemini не дал понятного ответа."

            print("🔮 Ответ от Gemini:", answer)

            # Отправляем ответ пользователю
            bot.send_message(
                chat_id=user_id,
                text=f"📜 Твои карты: {', '.join(selected_meanings)}\n\n✨ Ответ от Gemini:\n{answer}"
            )

        except Exception as e:
            print("❌ Ошибка при запросе к Gemini:", e)
            bot.send_message(
                chat_id=user_id,
                text="🚨 Ошибка при запросе к Gemini. Попробуйте позже."
            )

    except Exception as e:
        print("❌ Ошибка обработки web_app_data:", e)
        bot.send_message(user_id, "❌ Невозможно обработать данные от мини-приложения.")



# 🔹 Запуск бота
if __name__ == '__main__':
    print("🚀 Бот запущен...")
    bot.polling(none_stop=True)

