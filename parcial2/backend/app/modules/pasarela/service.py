import os
from uuid import uuid4
from fastapi import HTTPException


def crear_cobro(total):
    clave = os.getenv("STRIPE_SECRET_KEY")
    if not clave:
        return {"aprobado": True, "referencia": f"SIM-{uuid4().hex[:12]}"}
    if not clave.startswith("sk_test_"):
        raise HTTPException(402, "Solo se admite Stripe en modo prueba")
    try:
        import stripe
        stripe.api_key = clave
        intent = stripe.PaymentIntent.create(amount=round(float(total) * 100), currency="bob",
                                             payment_method="pm_card_visa", confirm=True,
                                             automatic_payment_methods={"enabled": True, "allow_redirects": "never"})
        return {"aprobado": intent.status == "succeeded", "referencia": intent.id}
    except Exception as exc:
        raise HTTPException(402, "Pago rechazado") from exc
