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

SYSTEM_PROMPT = """
You are Binkath Concierge.

You are an AI travel assistant for Uzbekistan.

Rules:
- Answer shortly and professionally.
- Help tourists with hotels, restaurants, taxis, banks, routes and attractions.
- If user writes in Russian answer in Russian.
- If user writes in English answer in English.
- If user asks about nearby places, use provided Google Maps links.
"""

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })

def send_location_button(chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    keyboard = {
        "keyboard": [
            [
                {
                    "text": "📍 Отправить геолокацию",
                    "request_location": True
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

    requests.post(url, json={
        "chat_id": chat_id,
        "text": "📍 Пожалуйста, отправьте вашу геолокацию.",
        "reply_markup": keyboard
    })

def search_google_places(query, lat=None, lng=None):
    if lat and lng:
        search_query = f"{query} near {lat},{lng}"
    else:
        search_query = query

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    params = {
        "query": search_query,
        "key": GOOGLE_MAPS_API_KEY,
        "language": "ru"
    }

    response = requests.get(url, params=params)
    data = response.json()

    results = data.get("results", [])

    if not results:
        return "Ничего не найдено."

    text = "🔎 Найдено:\n\n"

    for place in results[:5]:
        name = place.get("name")
        address = place.get("formatted_address")
        rating = place.get("rating", "—")

        location = place.get("geometry", {}).get("location", {})
        plat = location.get("lat")
        plng = location.get("lng")

        maps_link = f"https://www.google.com/maps/search/?api=1&query={plat},{plng}"

        text += (
            f"🏨 {name}\n"
            f"⭐ Рейтинг: {rating}\n"
            f"📍 {address}\n"
            f"🗺 {maps_link}\n\n"
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

    # LOCATION
    if "location" in message:
        lat = message["location"]["latitude"]
        lng = message["location"]["longitude"]

        user_locations[chat_id] = {
            "lat": lat,
            "lng": lng
        }

        send_telegram_message(
            chat_id,
            f"📍 Геолокация сохранена.\n\n"
            f"Теперь напишите что найти рядом:\n"
            f"- отель\n"
            f"- ресторан\n"
            f"- банкомат\n"
            f"- аптека\n"
            f"- такси"
        )

        return "ok"

    user_text = message.get("text", "")

    if user_text == "/start":
        send_telegram_message(
            chat_id,
            "Здравствуйте! Я Binkath Concierge.\n\n"
            "Ваш AI-консьерж по Узбекистану.\n\n"
            "Я могу помочь:\n"
            "- найти гостиницы\n"
            "- рестораны\n"
            "- банкоматы\n"
            "- маршруты\n"
            "- достопримечательности\n"
        )

        send_location_button(chat_id)

        return "ok"

    # QUICK BUTTONS
    quick_queries = [
        "отель",
        "ресторан",
        "банкомат",
        "аптека",
        "такси"
    ]

    if user_text.lower() in quick_queries:

        if chat_id not in user_locations:
            send_location_button(chat_id)
            return "ok"

        lat = user_locations[chat_id]["lat"]
        lng = user_locations[chat_id]["lng"]

        result = search_google_places(user_text, lat, lng)

        send_telegram_message(chat_id, result)

        return "ok"

    # HOTEL / LOCATION SEARCH
    hotel_words = [
        "отель",
        "гостиница",
        "hotel",
        "ресторан",
        "банкомат",
        "аптека"
    ]

    if any(word in user_text.lower() for word in hotel_words):

        result = search_google_places(user_text)

        send_telegram_message(chat_id, result)

        return "ok"

    # GPT CHAT
    if chat_id not in chat_history:
        chat_history[chat_id] = []

    chat_history[chat_id].append({
        "role": "user",
        "content": user_text
    })

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(chat_history[chat_id][-10:])

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages
    )

    answer = response.choices[0].message.content

    chat_history[chat_id].append({
        "role": "assistant",
        "content": answer
    })

    send_telegram_message(chat_id, answer)

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
