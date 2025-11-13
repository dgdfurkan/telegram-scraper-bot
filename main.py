import os
import httpx
from fastapi import FastAPI, Request

# Telegram bot token'ını ortam değişkeninden alıyoruz
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

app = FastAPI()


@app.get("/")
async def home():
    return {"message": "Bot works"}


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram'dan gelen update'leri alan endpoint.
    Mesaj geldiyse aynısını geri cevaplayacak (echo bot).
    """
    data = await request.json()

    # Normal mesaj veya düzenlenmiş mesaj olabilir
    message = data.get("message") or data.get("edited_message")
    if not message:
        # Mesaj içermeyen update'ler için bir şey yapmıyoruz
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    if not chat_id:
        return {"ok": True}

    # Basit echo cevabı
    reply_text = f"Sen yazdın: {text}"

    if TELEGRAM_TOKEN:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": reply_text},
            )

    return {"ok": True}