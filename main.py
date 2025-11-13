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
# GETIR API – Ortak ayarlar
# ------------------------

BASE_API = "https://franchise-api-gateway.getirapi.com"
STOCKS_URL = f"{BASE_API}/stocks"
WAREHOUSES_URL = f"{BASE_API}/users/warehouses/"


def build_getir_headers() -> dict:
    """
    Tarayıcıya benzer header seti oluşturur.
    Authorization dışında gizli bir şey yok.
    """
    if not GETIR_BEARER_TOKEN:
        raise RuntimeError("GETIR_BEARER_TOKEN tanımlı değil.")

    return {
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


# ------------------------
# GETIR STOCKS API
# ------------------------

async def fetch_stocks(limit: int = 100, offset: int = 0):
    """
    Getir franchise API'sindeki stocks endpoint'ine istek atar.

    Şu an 500 UnknownError dönüyor.
    Yine de debug için fonksiyon burada dursun.
    """

    try:
        headers = build_getir_headers()
    except RuntimeError as e:
        return {"ok": False, "reason": str(e)}

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

    try:
        data = resp.json()
    except Exception:
        data = None

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
    /stocks endpoint'ini test etmek için.
    Şu an 500 UnknownError veriyor, ama referans olarak kalsın.
    """
    return await fetch_stocks(limit=limit, offset=offset)


# ------------------------
# GETIR USERS/WAREHOUSES API
# ------------------------

async def fetch_warehouses():
    """
    GET /users/warehouses/ endpoint'ini test eder.
    Bu endpoint başarılıysa, token Render'dan çalışıyor demektir.
    """

    try:
        headers = build_getir_headers()
    except RuntimeError as e:
        return {"ok": False, "reason": str(e)}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(WAREHOUSES_URL, headers=headers)
    except Exception as e:
        return {
            "ok": False,
            "step": "request",
            "error": str(e),
        }

    try:
        data = resp.json()
    except Exception:
        data = resp.text

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


@app.get("/test-warehouses")
async def test_warehouses():
    """
    Tarayıcıdan:
      /test-warehouses

    ile çağırıp, Render'dan Getir API'ine token'lı istek atıp atamadığımızı test eder.
    """
    return await fetch_warehouses()


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

    message = data.get("message") or data.get("edited_message")
    if not message:
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
