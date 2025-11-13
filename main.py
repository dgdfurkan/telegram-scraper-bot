import os
import httpx
from fastapi import FastAPI, Request

# Ortam değişkenleri (Render Environment Variables)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GETIR_EMAIL = os.environ.get("GETIR_EMAIL")
GETIR_PASSWORD = os.environ.get("GETIR_PASSWORD")

app = FastAPI()


@app.get("/")
async def home():
    return {"message": "Bot works"}


# ------------------------
# GETIR LOGIN + STOCK TEST
# ------------------------

LOGIN_URL = "https://franchise.getir.com/login?redirect_uri=%2Fstock%2Fcurrent"
STOCK_URL = "https://franchise.getir.com/stock/current"


async def login_and_fetch_stock():
    """
    Getir franchise paneline login olmayı DENEYEN ve
    /stock/current sayfasını çekmeye çalışan basit iskelet.

    Not:
    - Buradaki LOGIN_URL ve form alan isimleri (email/password),
      Getir'in gerçek login akışına göre ayarlanabilir.
    - Şu an için yapı hazır; ileride Network tab'dan baktığımız
      bilgiye göre ince ayar yapacağız.
    """

    if not GETIR_EMAIL or not GETIR_PASSWORD:
        return {
            "ok": False,
            "reason": "GETIR_EMAIL veya GETIR_PASSWORD ortam değişkenleri tanımlı değil."
        }

    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        # 1) Login isteği atmayı dene
        try:
            login_payload = {
                "email": GETIR_EMAIL,
                "password": GETIR_PASSWORD,
            }

            login_resp = await client.post(LOGIN_URL, data=login_payload)
        except Exception as e:
            return {
                "ok": False,
                "step": "login_request",
                "error": str(e),
            }

        # 2) Login sonrası stock sayfasını çek
        try:
            stock_resp = await client.get(STOCK_URL)
        except Exception as e:
            return {
                "ok": False,
                "step": "stock_request",
                "error": str(e),
            }

        # Sonuç özetini dön (debug amaçlı)
        return {
            "ok": True,
            "login_status_code": login_resp.status_code,
            "stock_status_code": stock_resp.status_code,
            "stock_url_final": str(stock_resp.url),
            "stock_text_preview": stock_resp.text[:300],  # ilk 300 karakter
        }


@app.get("/test-getir")
async def test_getir():
    """
    Tarayıcıdan çağırıp Getir login + stock akışını test etmek için.
    """
    result = await login_and_fetch_stock()
    return result


# ------------------------
# TELEGRAM WEBHOOK
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

    # Basit echo cevabı
    reply_text = f"Sen yazdın: {text}"

    if TELEGRAM_TOKEN:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": reply_text},
            )

    return {"ok": True}
