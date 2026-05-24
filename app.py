from flask import Flask, request
from openai import OpenAI
import requests
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

chat_history = {}
user_locations = {}

MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "📍 Отправить геолокацию", "request_location": True}],
        [{"text": "🏨 Отель"}, {"text": "🍽 Ресторан"}],
        [{"text": "🏧 Банкомат"}, {"text": "💊 Аптека"}],
        [{"text": "🌐 eSIM"}, {"text": "🚕 Вызвать такси"}],
        [{"text": "🏨 Забронировать отель"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False
}

SYSTEM_PROMPT = """
You are Binkath Concierge, an AI travel assistant for Uzbekistan.

Rules:
- Answer in the same language as the user.
- Be concise, practical and helpful.
- Do not invent hotel availability, prices or bookings.
- Help with hotels, restaurants, ATMs, pharmacies, transport, routes and attractions.
"""

def send_message(chat_id, text, reply_markup=MAIN_KEYBOARD):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(url, json=payload)

def google_nearby_search(category, lat, lng):
    category_map = {
        "отель": {"type": "lodging", "keyword": "hotel"},
        "ресторан": {"type": "restaurant", "keyword": "restaurant"},
        "банкомат": {"type": "atm", "keyword": "ATM"},
        "аптека": {"type": "pharmacy", "keyword": "pharmacy"},
    }

    item = category_map.get(category.lower(), {"type": None, "keyword": category})

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    params = {
        "location": f"{lat},{lng}",
        "radius": 1500,
        "keyword": item["keyword"],
        "key": GOOGLE_MAPS_API_KEY,
        "language": "ru"
    }

    if item["type"]:
        params["type"] = item["type"]

    response = requests.get(url, params=params)
    data = response.json()

    status = data.get("status")
    error_message = data.get("error_message")

    if status not in ["OK", "ZERO_RESULTS"]:
        return f"⚠️ Ошибка Google Maps API:\n{status}\n{error_message or ''}"

    results = data.get("results", [])

    if not results:
        return "Ничего не найдено рядом. Попробуйте увеличить радиус или уточнить запрос."

    text = "🔎 Найдено рядом с вами:\n\n"

    for place in results[:5]:
        name = place.get("name", "Без названия")
        rating = place.get("rating", "—")
        address = place.get("vicinity", "Адрес не указан")

        loc = place.get("geometry", {}).get("location", {})
        plat = loc.get("lat")
        plng = loc.get("lng")

        maps_link = f"https://www.google.com/maps/search/?api=1&query={plat},{plng}"

        text += (
            f"📍 {name}\n"
            f"⭐ Рейтинг: {rating}\n"
            f"🏠 Адрес: {address}\n"
            f"🗺 Карта: {maps_link}\n\n"
        )

    return text

def google_text_search(query):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    params = {
        "query": query,
        "key": GOOGLE_MAPS_API_KEY,
        "language": "ru"
    }

    response = requests.get(url, params=params)
    data = response.json()

    status = data.get("status")
    error_message = data.get("error_message")

    if status not in ["OK", "ZERO_RESULTS"]:
        return f"⚠️ Ошибка Google Maps API:\n{status}\n{error_message or ''}"

    results = data.get("results", [])

    if not results:
        return "Ничего не найдено. Попробуйте уточнить запрос."

    text = "🔎 Найдено по вашему запросу:\n\n"

    for place in results[:5]:
        name = place.get("name", "Без названия")
        address = place.get("formatted_address", "Адрес не указан")
        rating = place.get("rating", "—")

        loc = place.get("geometry", {}).get("location", {})
        plat = loc.get("lat")
        plng = loc.get("lng")

        maps_link = f"https://www.google.com/maps/search/?api=1&query={plat},{plng}"

        text += (
            f"📍 {name}\n"
            f"⭐ Рейтинг: {rating}\n"
            f"🏠 Адрес: {address}\n"
            f"🗺 Карта: {maps_link}\n\n"
        )

    return text

@app.route("/", methods=["GET"])
def home():
    return "Binkath Concierge Bot is running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return "ok"

    if "location" in message:
        lat = message["location"]["latitude"]
        lng = message["location"]["longitude"]

        user_locations[chat_id] = {
            "lat": lat,
            "lng": lng
        }

        send_message(
            chat_id,
            "📍 Геолокация сохранена.\n\n"
            "Теперь нажмите кнопку или напишите, что найти рядом:\n"
            "🏨 Отель\n"
            "🍽 Ресторан\n"
            "🏧 Банкомат\n"
            "💊 Аптека"
        )

        return "ok"

    user_text = message.get("text", "").strip()

    if user_text == "/start":
        chat_history[chat_id] = []

        send_message(
            chat_id,
            "🇺🇿 Добро пожаловать в Binkath Concierge!\n\n"
            "Я AI-консьерж по Узбекистану.\n\n"
            "Могу помочь найти:\n"
            "🏨 отели\n"
            "🍽 рестораны\n"
            "🏧 банкоматы\n"
            "💊 аптеки\n"
            "📍 маршруты и локации\n\n"
            "Отправьте геолокацию или напишите запрос, например:\n"
            "«отель около рынка Чорсу в Ташкенте»"
        )

        return "ok"

    if user_text in ["🌐 eSIM", "🚕 Вызвать такси", "🏨 Забронировать отель"]:
        send_message(
            chat_id,
            "🚧 Эта функция сейчас на стадии разработки.\n\n"
            "Скоро здесь появится полноценный сервис Binkath Concierge."
        )

        return "ok"

    quick_map = {
        "🏨 Отель": "отель",
        "Отель": "отель",
        "отель": "отель",
        "🍽 Ресторан": "ресторан",
        "Ресторан": "ресторан",
        "ресторан": "ресторан",
        "🏧 Банкомат": "банкомат",
        "Банкомат": "банкомат",
        "банкомат": "банкомат",
        "💊 Аптека": "аптека",
        "Аптека": "аптека",
        "аптека": "аптека",
    }

    if user_text in quick_map:
        if chat_id not in user_locations:
            send_message(
                chat_id,
                "📍 Сначала нажмите «Отправить геолокацию», чтобы я искал рядом с вами."
            )
            return "ok"

        lat = user_locations[chat_id]["lat"]
        lng = user_locations[chat_id]["lng"]

        result = google_nearby_search(quick_map[user_text], lat, lng)
        send_message(chat_id, result)
        return "ok"

    place_words = [
        "отель",
        "гостиница",
        "hotel",
        "ресторан",
        "restaurant",
        "банкомат",
        "atm",
        "аптека",
        "pharmacy",
        "чорсу",
        "аэропорт",
        "airport",
        "регистан",
        "самарканд",
        "бухара",
        "ташкент"
    ]

    if any(word in user_text.lower() for word in place_words):
        result = google_text_search(user_text)
        send_message(chat_id, result)
        return "ok"

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    chat_history[chat_id].append({
        "role": "user",
        "content": user_text
    })

    chat_history[chat_id] = chat_history[chat_id][-10:]

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history[chat_id]

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages
        )

        answer = response.choices[0].message.content

        chat_history[chat_id].append({
            "role": "assistant",
            "content": answer
        })

        chat_history[chat_id] = chat_history[chat_id][-10:]

        send_message(chat_id, answer)

    except Exception as e:
        print("ERROR:", e)
        send_message(chat_id, "Ошибка сервиса. Попробуйте позже.")

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
