import os
import httpx
from fastapi import FastAPI, Request

# Ortam değişkenleri (Render Environment Variables)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GETIR_BEARER_TOKEN = os.environ.get("GETIR_BEARER_TOKEN")

app = FastAPI()


@app.get("/")
async def home():
    return {"message": "Bot works"}


# ------------------------
# GETIR STOCKS API
# ------------------------

STOCKS_URL = "https://franchise-api-gateway.getirapi.com/stocks"


async def fetch_stocks(limit: int = 100, offset: int = 0):
    """
    Getir franchise API'sindeki stocks endpoint'ine istek atar.

    - Authorization: Bearer <GETIR_BEARER_TOKEN>
    - limit / offset query parametreleri ile sayfalama yapar.
    """

    if not GETIR_BEARER_TOKEN:
        return {
            "ok": False,
            "reason": "GETIR_BEARER_TOKEN ortam değişkeni tanımlı değil."
        }

    headers = {
        "Authorization": f"Bearer {GETIR_BEARER_TOKEN}",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://franchise.getir.com",
        "Referer": "https://franchise.getir.com/stock/current",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
    }

    params = {
        "limit": limit,
        "offset": offset,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(STOCKS_URL, headers=headers, params=params)
    except Exception as e:
        return {
            "ok": False,
            "step": "request",
            "error": str(e),
        }

    # JSON parse etmeyi dene
    try:
        data = resp.json()
    except Exception:
        data = None

    # Ön izleme: çok veri varsa ilk birkaç elemanı göster
    preview = data
    if isinstance(data, list):
        preview = data[:3]
    elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        preview = {
            **{k: v for k, v in data.items() if k != "items"},
            "items_preview": data["items"][:3],
        }

    return {
        "ok": resp.status_code == 200,
        "status_code": resp.status_code,
        "url": str(resp.url),
        "preview": preview,
    }


@app.get("/test-stocks")
async def test_stocks(limit: int = 50, offset: int = 0):
    """
    Tarayıcıdan çağırıp Getir stocks endpoint'ini test etmek için.
    Örn:
      /test-stocks
      /test-stocks?limit=10&offset=0
    """
    return await fetch_stocks(limit=limit, offset=offset)


# ------------------------
# TELEGRAM WEBHOOK (Şimdilik echo)
# ------------------------

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

    reply_text = f"Sen yazdın: {text}"

    if TELEGRAM_TOKEN:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": reply_text},
            )

    return {"ok": True}
