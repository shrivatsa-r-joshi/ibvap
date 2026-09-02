"""
Owner: Integration (alert delivery)

Goal
----
Consume `alert` messages (docs/schema.md) and actually deliver them:
  - SMS via Twilio (TWILIO_* env vars)
  - Email via SendGrid (SENDGRID_API_KEY, ALERT_EMAIL_* env vars)

Called by app/main.py whenever fence.py produces a new alert. Keep this file as
the ONLY place that talks to Twilio/SendGrid so API keys and retry logic live
in one spot.

Suggested SMS text:
  "[IBVAP ALERT] {severity} - {class} detected at {location}, {timestamp}"
"""
from app import config


def send_alert(alert: dict) -> None:
    """
    Args:
        alert: an `alert` message dict matching docs/schema.md
    """
    # TODO: implement Twilio SMS + SendGrid email dispatch
    raise NotImplementedError
