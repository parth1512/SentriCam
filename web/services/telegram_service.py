"""
Telegram notification service for vehicle tracking alerts
"""
import os
import requests
import logging
from typing import Optional, Dict
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None
TELEGRAM_ENABLED = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'

class TelegramService:
    """Service for sending Telegram notifications"""
    
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.api_url = TELEGRAM_API_URL
        self.enabled = TELEGRAM_ENABLED and bool(self.bot_token)
        
        if not self.enabled:
            if not TELEGRAM_ENABLED:
                logger.info("Telegram notifications are disabled (TELEGRAM_ENABLED=false)")
            elif not self.bot_token:
                logger.warning("Telegram bot token not found. Set TELEGRAM_BOT_TOKEN environment variable.")
        else:
            logger.info("Telegram service initialized and enabled")
    
    def send_message(self, chat_id: str, text: str) -> Dict[str, any]:
        """
        Send a text message via Telegram
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            
        Returns:
            Dict with status and response data
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Telegram service is disabled'
            }
        
        if not chat_id:
            return {
                'success': False,
                'error': 'Chat ID is required'
            }
        
        url = f"{self.api_url}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Telegram message sent to chat_id: {chat_id}")
                return {
                    'success': True,
                    'message_id': result.get('result', {}).get('message_id'),
                    'response': result
                }
            else:
                error = result.get('description', 'Unknown error')
                logger.error(f"Telegram API error: {error}")
                return {
                    'success': False,
                    'error': error,
                    'response': result
                }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_location(self, chat_id: str, latitude: float, longitude: float) -> Dict[str, any]:
        """
        Send a location pin via Telegram
        
        Args:
            chat_id: Telegram chat ID
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dict with status and response data
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Telegram service is disabled'
            }
        
        if not chat_id:
            return {
                'success': False,
                'error': 'Chat ID is required'
            }
        
        url = f"{self.api_url}/sendLocation"
        payload = {
            'chat_id': chat_id,
            'latitude': latitude,
            'longitude': longitude
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Telegram location sent to chat_id: {chat_id}")
                return {
                    'success': True,
                    'message_id': result.get('result', {}).get('message_id'),
                    'response': result
                }
            else:
                error = result.get('description', 'Unknown error')
                logger.error(f"Telegram API error: {error}")
                return {
                    'success': False,
                    'error': error,
                    'response': result
                }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram location: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_vehicle_alert(self, chat_id: str, user_name: str, vehicle_number: str, 
                          camera_location_name: str, latitude: float, longitude: float,
                          send_location: bool = True) -> Dict[str, any]:
        """
        Send a vehicle last seen alert with map link and optional location pin
        
        Args:
            chat_id: Telegram chat ID
            user_name: Name of the vehicle owner
            vehicle_number: License plate number
            camera_location_name: Name of the camera location
            latitude: Latitude of last known location
            longitude: Longitude of last known location
            send_location: Whether to send location pin (default: True)
            
        Returns:
            Dict with status of both message and location sends
        """
        # Generate Google Maps link
        maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
        
        # Format message
        message = f"""🚗 <b>Vehicle Update Alert</b>

Hello {user_name},

Your car (<b>{vehicle_number}</b>) was last seen near <b>{camera_location_name}</b>.

Tap below to view on map:
<a href="{maps_link}">📍 View on Google Maps</a>

<i>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"""
        
        results = {
            'message': None,
            'location': None
        }
        
        # Send text message
        message_result = self.send_message(chat_id, message)
        results['message'] = message_result
        
        # Send location pin if enabled
        if send_location and message_result.get('success'):
            location_result = self.send_location(chat_id, latitude, longitude)
            results['location'] = location_result
        
        return results
    
    def get_bot_info(self) -> Optional[Dict]:
        """Get bot information to verify token is valid"""
        if not self.enabled:
            return None
        
        url = f"{self.api_url}/getMe"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return result.get('result')
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get bot info: {e}")
            return None

# Global instance
_telegram_service = None

def get_telegram_service() -> TelegramService:
    """Get or create Telegram service instance (singleton)"""
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramService()
    return _telegram_service




