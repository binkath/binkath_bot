from flask import Flask, request
from openai import OpenAI
import os
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are Binkath Concierge, an AI concierge for travelers in Uzbekistan.

Language rules:
- If the user writes in Russian, answer only in Russian.
- If the user writes in English, answer only in English.
- Never mix Russian and English in one answer.
- If the user asks to switch language, switch to that language.

Role:
You help travelers with hotels, routes, transport, local advice, safety, restaurants, attractions and travel planning in Uzbekistan.

Style:
Be clear, professional, concise and helpful.
Do not invent exact hotel availability or prices unless the user provided them.
If needed, ask one short clarifying question.
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
        send_telegram_message(
            chat_id,
            "Hello! I am Binkath Concierge, your AI travel assistant for Uzbekistan.\n\n"
            "You can write in English or Russian.\n\n"
            "Здравствуйте! Я Binkath Concierge, ваш AI-консьерж по Узбекистану.\n\n"
            "Можете писать на русском или английском."
        )
        return "ok"

    if not user_text:
        send_telegram_message(chat_id, "Please send a text message.")
        return "ok"

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ]
        )

        reply = response.choices[0].message.content
        send_telegram_message(chat_id, reply)

    except Exception as e:
        print("ERROR:", e)
        send_telegram_message(
            chat_id,
            "Извините, временная ошибка сервиса. Попробуйте ещё раз через минуту."
        )

    return "ok"
