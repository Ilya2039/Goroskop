import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

API_TOKEN = '7584759675:AAGMKdKTRMjaC0Rc1g-Ysw-5J2dlniIQdAA'
MINI_APP_URL = 'https://554a-185-77-216-6.ngrok-free.app'  # Ссылка на мини-приложение

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    # Создаём кнопку с WebApp
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎲 Бросить кубик!", web_app=WebAppInfo(url=MINI_APP_URL)))

    # Отправляем сообщение с кнопкой
    bot.send_message(
        chat_id=message.chat.id,
        text="Нажми на кнопку, чтобы запустить мини-приложение:",
        reply_markup=keyboard
    )

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
