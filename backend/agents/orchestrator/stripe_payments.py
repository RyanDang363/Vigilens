"""
Stripe Embedded Checkout for SafeWatch.

Creates checkout sessions for analysis report payments
and verifies payment completion.
"""

from __future__ import annotations

import os
import time

from backend.agents.models.config import (
    STRIPE_AMOUNT_CENTS,
    STRIPE_CURRENCY,
    STRIPE_PRODUCT_NAME,
    STRIPE_PUBLISHABLE_KEY,
    STRIPE_SECRET_KEY,
    STRIPE_SUCCESS_URL,
)


def _get_stripe():
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def _expires_at() -> int:
    expires_in = int(os.getenv("STRIPE_CHECKOUT_EXPIRES_SECONDS", "1800"))
    expires_in = max(1800, min(86400, expires_in))
    return int(time.time()) + expires_in


def create_checkout_session(
    *,
    user_address: str,
    chat_session_id: str,
    description: str,
) -> dict:
    """Create an embedded Stripe Checkout session for a SafeWatch report."""
    stripe = _get_stripe()

    return_url = (
        f"{STRIPE_SUCCESS_URL}"
        f"?session_id={{CHECKOUT_SESSION_ID}}"
        f"&chat_session_id={chat_session_id}"
        f"&user={user_address}"
    )

    session = stripe.checkout.Session.create(
        ui_mode="embedded_page",
        redirect_on_completion="if_required",
        payment_method_types=["card"],
        mode="payment",
        return_url=return_url,
        expires_at=_expires_at(),
        line_items=[
            {
                "price_data": {
                    "currency": STRIPE_CURRENCY,
                    "product_data": {
                        "name": STRIPE_PRODUCT_NAME,
                        "description": description,
                    },
                    "unit_amount": STRIPE_AMOUNT_CENTS,
                },
                "quantity": 1,
            }
        ],
        metadata={
            "user_address": user_address,
            "session_id": chat_session_id,
            "service": "safewatch_report",
        },
    )

    return {
        "client_secret": session.client_secret,
        "id": session.id,
        "checkout_session_id": session.id,
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "currency": STRIPE_CURRENCY,
        "amount_cents": STRIPE_AMOUNT_CENTS,
        "ui_mode": "embedded",
    }


def verify_checkout_paid(checkout_session_id: str) -> bool:
    """Check if a Stripe Checkout session has been paid."""
    stripe = _get_stripe()
    session = stripe.checkout.Session.retrieve(checkout_session_id)
    return getattr(session, "payment_status", None) == "paid"
