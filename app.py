from flask import Flask, request
import requests
import openai
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

chat_history = {}
user_locations = {}

SYSTEM_PROMPT = """
You are Binkath Concierge.

You are an AI concierge for tourists visiting Uzbekistan.

You help with:
- restaurants
- hotels
- transport
- taxis
- tourism
- local tips
- ATMs
- navigation
- routes
- Uzbek culture
- shopping

Rules:
- Be concise
- Be practical
- Always help tourists
- Speak in the same language as the user
- If user asks for nearby places and location exists, use it
- Do not invent exact prices, booking availability or fake confirmations
"""

MAIN_KEYBOARD = {
    "keyboard": [
        [
            {
                "text": "📍 Отправить геолокацию",
                "request_location": True
            }
        ],
        [
            {"text": "🌐 eSIM"},
            {"text": "🚕 Вызвать такси"}
        ],
        [
            {"text": "🏨 Забронировать отель"}
        ]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False
}


def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(url, json=payload)


def ask_gpt(messages):
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages
        ],
        temperature=0.7,
        max_tokens=500
    )

    return response.choices[0].message.content


@app.route("/")
def home():
    return "Binkath Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return "ok"

    if "location" in message:
        location = message["location"]

        lat = location.get("latitude")
        lon = location.get("longitude")

        user_locations[chat_id] = {
            "lat": lat,
            "lon": lon
        }

        maps_link = f"https://maps.google.com/?q={lat},{lon}"

        send_telegram_message(
            chat_id,
            f"📍 Геолокация сохранена.\n\n"
            f"Ваше местоположение:\n{maps_link}\n\n"
            f"Теперь напишите, что нужно найти рядом:\n"
            f"- отель\n"
            f"- ресторан\n"
            f"- банкомат\n"
            f"- аптека\n"
            f"- достопримечательность\n"
            f"- такси",
            reply_markup=MAIN_KEYBOARD
        )

        return "ok"

    user_text = message.get("text", "")

    if user_text == "/start":
        chat_history[chat_id] = []

        welcome_text = (
            "🇺🇿 Добро пожаловать в Binkath Concierge!\n\n"
            "Я AI-консьерж по Узбекистану.\n"
            "Могу помочь с:\n"
            "- отелями\n"
            "- ресторанами\n"
            "- маршрутами\n"
            "- банкоматами\n"
            "- транспортом\n"
            "- достопримечательностями\n\n"
            "📍 Нажмите кнопку «Отправить геолокацию», чтобы я мог искать места рядом.\n\n"
            "You can also write in English."
        )

        send_telegram_message(
            chat_id,
            welcome_text,
            reply_markup=MAIN_KEYBOARD
        )

        return "ok"

    if user_text in ["🌐 eSIM", "🚕 Вызвать такси", "🏨 Забронировать отель"]:
        send_telegram_message(
            chat_id,
            "🚧 Эта функция сейчас на стадии разработки.\n\n"
            "Скоро здесь появится полноценный сервис Binkath Concierge.",
            reply_markup=MAIN_KEYBOARD
        )

        return "ok"

    if not user_text:
        send_telegram_message(
            chat_id,
            "Пожалуйста, отправьте текстовое сообщение.",
            reply_markup=MAIN_KEYBOARD
        )
        return "ok"

    nearby_keywords = [
        "банкомат",
        "atm",
        "ресторан",
        "restaurant",
        "hotel",
        "отель",
        "кафе",
        "cafe",
        "coffee",
        "аптека",
        "pharmacy",
        "достопримечательность",
        "sightseeing",
        "attraction",
        "такси",
        "taxi"
    ]

    if any(word in user_text.lower() for word in nearby_keywords):
        if chat_id in user_locations:
            lat = user_locations[chat_id]["lat"]
            lon = user_locations[chat_id]["lon"]

            query = user_text.replace(" ", "+")

            maps_search = (
                f"https://www.google.com/maps/search/"
                f"{query}/@{lat},{lon},15z"
            )

            send_telegram_message(
                chat_id,
                f"🔎 Нашёл поиск рядом с вашей геолокацией:\n\n"
                f"{maps_search}",
                reply_markup=MAIN_KEYBOARD
            )

            return "ok"

        else:
            send_telegram_message(
                chat_id,
                "📍 Сначала нажмите кнопку «Отправить геолокацию».",
                reply_markup=MAIN_KEYBOARD
            )

            return "ok"

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    chat_history[chat_id].append({
        "role": "user",
        "content": user_text
    })

    chat_history[chat_id] = chat_history[chat_id][-10:]

    try:
        reply = ask_gpt(chat_history[chat_id])

        chat_history[chat_id].append({
            "role": "assistant",
            "content": reply
        })

        chat_history[chat_id] = chat_history[chat_id][-10:]

        send_telegram_message(
            chat_id,
            reply,
            reply_markup=MAIN_KEYBOARD
        )

    except Exception as e:
        print("ERROR:", e)

        send_telegram_message(
            chat_id,
            "Ошибка сервиса. Попробуйте позже.",
            reply_markup=MAIN_KEYBOARD
        )

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
