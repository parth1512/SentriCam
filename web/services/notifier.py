"""
Notification service for vehicle tracking events.

Supports webhook-based notifications (Telegram, WhatsApp, etc.)
"""

import os
import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

NOTIFY_WEBHOOK = os.getenv("NOTIFY_WEBHOOK", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")
TWILIO_WHATSAPP_TO = os.getenv("TWILIO_WHATSAPP_TO", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")


class Notifier:
    """Notification service with pluggable backends."""
    
    def __init__(self):
        self.webhook_url = NOTIFY_WEBHOOK
        self.telegram_token = TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = TELEGRAM_CHAT_ID
        self.twilio_from = TWILIO_WHATSAPP_FROM
        self.twilio_to = TWILIO_WHATSAPP_TO
        self.twilio_sid = TWILIO_ACCOUNT_SID
        self.twilio_token = TWILIO_AUTH_TOKEN
    
    def notify_owner(self, plate: str, message: str, event_type: str = "info"):
        """
        Notify vehicle owner about tracking event.
        
        Args:
            plate: License plate number
            message: Notification message
            event_type: Type of event (entry, exit, parked, etc.)
        """
        full_message = f"Vehicle {plate}: {message}"
        
        # Try Telegram first
        if self.telegram_token and self.telegram_chat_id:
            try:
                self._send_telegram(full_message)
                logger.info(f"Sent Telegram notification for {plate}")
            except Exception as e:
                logger.error(f"Failed to send Telegram notification: {e}")
        
        # Try generic webhook
        if self.webhook_url:
            try:
                self._send_webhook({
                    "plate": plate,
                    "message": message,
                    "event_type": event_type,
                    "full_message": full_message
                })
                logger.info(f"Sent webhook notification for {plate}")
            except Exception as e:
                logger.error(f"Failed to send webhook notification: {e}")
        
        # Try Twilio WhatsApp
        if self.twilio_sid and self.twilio_token and self.twilio_from and self.twilio_to:
            try:
                self._send_whatsapp(full_message)
                logger.info(f"Sent WhatsApp notification for {plate}")
            except Exception as e:
                logger.error(f"Failed to send WhatsApp notification: {e}")
        
        # Always log
        logger.info(f"Notification: {full_message}")
    
    def notify_admin(self, event: Dict):
        """
        Notify admin about system events.
        
        Args:
            event: Event dictionary with event details
        """
        message = f"Admin Alert: {event.get('type', 'unknown')} - {event.get('message', '')}"
        logger.warning(message)
        
        # Send to webhook if configured
        if self.webhook_url:
            try:
                self._send_webhook({
                    "type": "admin_alert",
                    **event
                })
            except Exception as e:
                logger.error(f"Failed to send admin webhook: {e}")
    
    def _send_telegram(self, message: str):
        """Send message via Telegram Bot API."""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
    
    def _send_webhook(self, data: Dict):
        """Send data to generic webhook URL."""
        if not self.webhook_url:
            return
        
        response = requests.post(
            self.webhook_url,
            json=data,
            timeout=5,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
    
    def _send_whatsapp(self, message: str):
        """Send message via Twilio WhatsApp API."""
        if not all([self.twilio_sid, self.twilio_token, self.twilio_from, self.twilio_to]):
            return
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
        auth = (self.twilio_sid, self.twilio_token)
        payload = {
            "From": f"whatsapp:{self.twilio_from}",
            "To": f"whatsapp:{self.twilio_to}",
            "Body": message
        }
        
        response = requests.post(url, data=payload, auth=auth, timeout=10)
        response.raise_for_status()


# Global notifier instance
_notifier = None

def get_notifier() -> Notifier:
    """Get or create notifier instance (singleton)."""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier





