from flask import Flask, request, jsonify, render_template
from google import genai
from googletrans import Translator  # Импортируем переводчик
import logging

app = Flask(__name__)

# Установите уровень логирования
logging.basicConfig(level=logging.DEBUG)

# Инициализация переводчика
translator = Translator()

# API-ключ для Gemini
GEMINI_API_KEY = "AIzaSyCqE4taBEs1GJUh_pJQUqdGgcSEfGL8Pbc"
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

@app.route('/tarot/')
def tarot_page():
    return render_template('tarot/index.html')

# Маршрут для отображения страницы натальной карты
@app.route('/natal/', methods=['GET'])
def natal_page():
    return render_template('natal/index.html')


# Маршрут для обработки запросов к Gemini
@app.route('/natal/gemini', methods=['POST'])
def natal_gemini():
    try:
        logging.info("Получен запрос на эндпоинт /natal/gemini")

        # Читаем данные из запроса
        data = request.get_json()
        logging.debug(f"Данные запроса: {data}")

        query = data.get('query')
        if not query:
            logging.error("Запрос не содержит параметра 'query'")
            return jsonify({'error': 'No query provided'}), 400

        # Отправляем запрос в Gemini
        logging.info(f"Отправляем запрос в Gemini: {query}")
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=query
        )

        if hasattr(response, 'text') and response.text:
            result = response.text.strip()
            logging.info(f"Ответ от Gemini: {result}")

            # Переводим ответ на русский
            translated_result = translator.translate(result, src='en', dest='ru').text
            logging.info(f"Переведенный ответ: {translated_result}")

            return jsonify({'answer': translated_result})
        else:
            logging.error("Gemini вернул пустой ответ")
            return jsonify({'error': 'Empty response from Gemini'}), 500

    except Exception as e:
        logging.exception("Ошибка при обработке запроса")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
# ✅ **Гороскоп на сегодня**
@app.route('/horoscope/today', methods=['POST'])
def horoscope_today():
    try:
        logging.info("Получен запрос на гороскоп на сегодня")

        data = request.get_json()
        zodiac_sign = data.get('zodiac_sign')

        if not zodiac_sign:
            logging.error("Некорректный запрос: отсутствует знак зодиака")
            return jsonify({'error': 'Укажите знак зодиака'}), 400

        # Запрос в Gemini
        query = f"Предоставь детальный гороскоп на сегодня для знака зодиака {zodiac_sign}. Ответ должен быть кратким и содержательным."

        logging.info(f"Отправляем запрос в Gemini: {query}")
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=query
        )

        # Проверяем ответ
        if hasattr(response, 'text') and response.text:
            result = response.text.strip()
            logging.info(f"Ответ от Gemini: {result}")

            # Переводим ответ на русский
            translated_result = translator.translate(result, src='en', dest='ru').text
            logging.info(f"Переведенный ответ: {translated_result}")

            return jsonify({'answer': translated_result})
        else:
            logging.error("Gemini вернул пустой ответ")
            return jsonify({'error': 'Gemini не дал ответа'}), 500

    except Exception as e:
        logging.exception("Ошибка при обработке запроса")
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)


