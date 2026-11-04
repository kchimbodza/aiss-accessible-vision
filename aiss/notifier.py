"""Alert delivery. Uses Twilio SMS when configured, otherwise logs to the console."""

from __future__ import annotations

import logging
import threading
from typing import Optional

from aiss.config import TwilioConfig

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, twilio: Optional[TwilioConfig] = None) -> None:
        self._twilio = twilio
        self._client = None
        if twilio:
            from twilio.rest import Client

            self._client = Client(twilio.account_sid, twilio.auth_token)

    def send(self, body: str) -> None:
        """Send an alert without blocking the video loop."""
        threading.Thread(target=self._send, args=(body,), daemon=True).start()

    def _send(self, body: str) -> None:
        if not self._client:
            log.warning("ALERT (SMS not configured): %s", body)
            return
        try:
            self._client.messages.create(
                to=self._twilio.to_number, from_=self._twilio.from_number, body=body
            )
            log.info("SMS alert sent")
        except Exception:  # network errors must never kill surveillance
            log.exception("Failed to send SMS alert")
