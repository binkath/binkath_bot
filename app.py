from flask import Flask, request
from openai import OpenAI
import os
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

chat_history = {}

SYSTEM_PROMPT = """
You are Binkath Concierge, an AI concierge for travelers in Uzbekistan.

Rules:
- Reply in Russian if the user writes in Russian.
- Reply in English if the user writes in English.
- Remember previous messages in the conversation.
- Help with hotels, restaurants, routes, districts, safety and tourism.
- Be practical and concise.
"""

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })

@app.route("/", methods=["GET"])
def home():
    return "Binkath Concierge Bot is running"

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json()

    message = data.get("message", {})
    chat = message.get("chat", {})

    chat_id = chat.get("id")
    user_text = message.get("text", "")

    # GEOLOCATION SUPPORT
    location = message.get("location")

    if location:

        lat = location.get("latitude")
        lon = location.get("longitude")

        maps_link = f"https://www.google.com/maps?q={lat},{lon}"

        send_telegram_message(
            chat_id,
            f"📍 Геолокация получена.\n\n"
            f"Ваше местоположение:\n{maps_link}\n\n"
            f"Теперь напишите, что вам нужно рядом:\n"
            f"- отель\n"
            f"- ресторан\n"
            f"- банкомат\n"
            f"- аптека\n"
            f"- достопримечательность"
        )

        return "ok"

    if not chat_id:
        return "ok"

    # START COMMAND
    if user_text == "/start":

        chat_history[chat_id] = []

        send_telegram_message(
            chat_id,
            "Здравствуйте! Я Binkath Concierge.\n\n"
            "Ваш AI-консьерж по Узбекистану.\n\n"
            "Можете отправить геолокацию или написать вопрос."
        )

        return "ok"

    if not user_text:

        send_telegram_message(
            chat_id,
            "Пожалуйста, отправьте текстовое сообщение."
        )

        return "ok"

    # MEMORY
    if chat_id not in chat_history:
        chat_history[chat_id] = []

    chat_history[chat_id].append({
        "role": "user",
        "content": user_text
    })

    chat_history[chat_id] = chat_history[chat_id][-10:]

    try:

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ] + chat_history[chat_id]

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages
        )

        reply = response.choices[0].message.content

        chat_history[chat_id].append({
            "role": "assistant",
            "content": reply
        })

        send_telegram_message(chat_id, reply)

    except Exception as e:

        print("ERROR:", e)

        send_telegram_message(
            chat_id,
            "Ошибка сервиса. Попробуйте позже."
        )

    return "ok"
