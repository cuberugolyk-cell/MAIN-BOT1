from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio

from database import (
    list_services, get_service, get_text,
    create_payment, get_setting
)
from config import BOT_TOKEN

app = FastAPI()

# CORS — разрешаем Mini App обращаться к API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/services")
def api_services():
    items = list_services()
    return {
        "services": [
            {
                "id": s[0],
                "title": s[1],
                "description": s[2],
                "price": s[3],
                "stars": s[4],
                "rub": s[5],
            }
            for s in items
        ]
    }


@app.get("/api/texts")
def api_texts():
    return {
        "welcome": get_text("welcome"),
        "contacts": get_text("contacts"),
        "payment_note": get_text("payment_note"),
    }


class OrderRequest(BaseModel):
    user_id: int
    username: Optional[str] = ""
    service_id: int
    method: str  # stars / fiat


@app.post("/api/order")
def api_order(req: OrderRequest):
    s = get_service(req.service_id)
    if not s:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    sid, title, desc, price, stars, rub = s
    if req.method == "stars":
        amount, currency = stars, "XTR"
    elif req.method == "fiat":
        amount, currency = rub, "RUB"
    else:
        raise HTTPException(status_code=400, detail="Неверный метод")

    if not amount:
        raise HTTPException(status_code=400, detail="Цена не задана")

    payload = f"{req.method}:{req.user_id}:{req.service_id}"
    create_payment(req.user_id, None, req.service_id, amount, currency, req.method, payload)

    return {
        "ok": True,
        "payload": payload,
        "amount": amount,
        "currency": currency,
        "title": title,
    }


@app.get("/api/health")
def health():
    return {"ok": True}