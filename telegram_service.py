import html
import logging
import requests

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token.strip()
        self.chat_id = str(chat_id).strip()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Sends a message to the configured Telegram chat.
        Splits automatically if the message exceeds Telegram's 4096 character limit.
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram bot token or chat ID is missing.")
            return False

        url = f"{self.base_url}/sendMessage"
        max_length = 4000
        parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]

        success = True
        for part in parts:
            payload = {
                "chat_id": self.chat_id,
                "text": part,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            try:
                response = requests.post(url, json=payload, timeout=15)
                res_data = response.json()
                if not response.ok or not res_data.get("ok"):
                    logger.error(f"Failed to send Telegram message: {res_data.get('description')}")
                    success = False
            except Exception as e:
                logger.error(f"Error calling Telegram API: {e}")
                success = False

        return success

    def test_connection(self) -> bool:
        """Verifies if the bot token is valid and can reach the chat."""
        url = f"{self.base_url}/getMe"
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            if data.get("ok"):
                bot_name = data.get("result", {}).get("username")
                logger.info(f"Connected to Telegram Bot: @{bot_name}")
                return True
            else:
                logger.error(f"Telegram getMe error: {data.get('description')}")
                return False
        except Exception as e:
            logger.error(f"Connection error to Telegram: {e}")
            return False

