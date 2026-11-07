import socket

# Force IPv4 to prevent WinError 10060 timeout on networks with broken IPv6 routing
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

import os
import sys
import time
import json
import logging
import argparse
from dotenv import load_dotenv

from gmail_service import GmailService
from summarizer import EmailSummarizer
from telegram_service import TelegramService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("EmailAgent")

CACHE_FILE = "processed_emails.json"

def load_processed_ids() -> set:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            logger.warning(f"Could not load {CACHE_FILE}: {e}")
    return set()

def save_processed_ids(processed_ids: set):
    try:
        # Keep last 500 IDs to avoid unbounded file growth
        id_list = list(processed_ids)[-500:]
        with open(CACHE_FILE, "w") as f:
            json.dump(id_list, f)
    except Exception as e:
        logger.warning(f"Could not save {CACHE_FILE}: {e}")

def run_agent(run_once: bool = False):
    load_dotenv()

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    check_interval = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
    mark_as_read = os.getenv("MARK_AS_READ", "True").lower() in ("true", "1", "yes")

    if not telegram_token or not telegram_chat_id:
        logger.error("TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID wajib diisi di file .env!")
        sys.exit(1)

    if not gemini_api_key:
        logger.error("GEMINI_API_KEY wajib diisi di file .env!")
        sys.exit(1)

    logger.info("Inisialisasi layanan Telegram, Gemini, dan Gmail...")
    telegram_service = TelegramService(telegram_token, telegram_chat_id)
    summarizer = EmailSummarizer(gemini_api_key)
    gmail_service = GmailService()

    # Test Telegram bot connection
    if not telegram_service.test_connection():
        logger.error("Gagal terhubung ke Telegram Bot. Periksa TELEGRAM_BOT_TOKEN Anda.")
        sys.exit(1)

    # Initialize Gmail authentication
    try:
        gmail_service.authenticate()
    except Exception as e:
        logger.error(f"Gagal otentikasi Gmail: {e}")
        sys.exit(1)

    processed_ids = load_processed_ids()
    logger.info("Agent aktif dan siap memantau email baru.")

    try:
        while True:
            logger.info("Mengecek email baru...")
            unread_emails = gmail_service.get_unread_emails()

            new_count = 0
            for email in unread_emails:
                msg_id = email['id']
                if msg_id in processed_ids:
                    continue

                new_count += 1
                logger.info(f"Memproses email baru: '{email['subject']}' dari '{email['sender']}'")

                # Generate AI summary
                summary = summarizer.summarize(
                    sender=email['sender'],
                    subject=email['subject'],
                    body=email['body']
                )

                # Format message for Telegram
                tg_message = summarizer.format_telegram_message(
                    sender=email['sender'],
                    subject=email['subject'],
                    date=email['date'],
                    summary=summary,
                    message_id=msg_id
                )

                # Send Telegram notification
                sent = telegram_service.send_message(tg_message)
                if sent:
                    processed_ids.add(msg_id)
                    save_processed_ids(processed_ids)

                    if mark_as_read:
                        gmail_service.mark_as_read(msg_id)

            if new_count == 0:
                logger.info("Tidak ada email baru.")

            if run_once:
                logger.info("Mode single-run selesai.")
                break

            logger.info(f"Menunggu {check_interval} detik sebelum pengecekan berikutnya...")
            time.sleep(check_interval)

    except KeyboardInterrupt:
        logger.info("Agent dihentikan oleh pengguna.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gmail AI Notifier Agent for Telegram")
    parser.add_argument("--once", action="store_true", help="Jalankan pengecekan satu kali saja lalu keluar")
    args = parser.parse_args()

    run_agent(run_once=args.once)
