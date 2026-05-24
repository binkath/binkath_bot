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
Answer clearly, professionally and helpfully.
You help with hotels, routes, transport, local advice, safety and travel planning.
If the user writes in Russian, answer in Russian.
If the user writes in English, answer in English.
"""

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

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

    if not chat_id or not user_text:
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
        send_telegram_message(chat_id, "Извините, временная ошибка сервиса. Мы уже работаем над этим.")
        print(e)

    return "ok"
