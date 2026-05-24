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

Language rules:
- If the user writes in Russian, answer only in Russian.
- If the user writes in English, answer only in English.
- Never mix Russian and English in one answer.

Important behavior:
- Remember the conversation context.
- If the user asks "where?", "give location", "near this place", or similar, understand it based on the previous messages.
- Do not invent exact hotel availability or prices.
- If you are not sure, say that you need to check live map or hotel database.
- Be practical: give addresses, districts, route advice and Google Maps search links when possible.

Role:
You help travelers with hotels, districts, routes, transport, local advice, safety, restaurants, attractions and travel planning in Uzbekistan.

Style:
Clear, professional, concise, helpful.
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

    if not chat_id:
        return "ok"

    if user_text == "/start":
        chat_history[chat_id] = []
        send_telegram_message(
            chat_id,
            "Здравствуйте! Я Binkath Concierge, ваш AI-консьерж по Узбекистану.\n\n"
            "Можете писать на русском или английском.\n\n"
            "Hello! I am Binkath Concierge, your AI travel assistant for Uzbekistan.\n\n"
            "You can write in English or Russian."
        )
        return "ok"

    if not user_text:
        send_telegram_message(chat_id, "Пожалуйста, отправьте текстовое сообщение.")
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

        reply = response.choices[0].message.content

        chat_history[chat_id].append({
            "role": "assistant",
            "content": reply
        })

        chat_history[chat_id] = chat_history[chat_id][-10:]

        send_telegram_message(chat_id, reply)

    except Exception as e:
        print("ERROR:", e)
        send_telegram_message(
            chat_id,
            "Извините, временная ошибка сервиса. Попробуйте ещё раз через минуту."
        )

    return "ok"
