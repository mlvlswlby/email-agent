import os
import sys
from dotenv import load_dotenv
from telegram_service import TelegramService

def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or token == "your_telegram_bot_token_here":
        print("❌ Error: TELEGRAM_BOT_TOKEN belum diatur di file .env")
        sys.exit(1)

    if not chat_id or chat_id == "your_telegram_chat_id_here":
        print("❌ Error: TELEGRAM_CHAT_ID belum diatur di file .env")
        sys.exit(1)

    print("🔍 Menguji koneksi ke Telegram...")
    tg = TelegramService(token, chat_id)
    if not tg.test_connection():
        print("❌ Gagal terhubung ke Telegram Bot. Pastikan token bot benar.")
        sys.exit(1)

    print("📨 Mengirim pesan uji coba ke chat ID Anda...")
    msg = (
        "🤖 <b>Test Notifikasi Email Agent Berhasil!</b>\n\n"
        "Koneksi antara script dan Telegram Bot Anda sudah aktif dan siap menerima notifikasi email masuk."
    )
    if tg.send_message(msg):
        print("✅ Pesan uji coba berhasil dikirim! Silakan periksa aplikasi Telegram Anda.")
    else:
        print("❌ Gagal mengirim pesan. Pastikan Anda sudah menekan tombol 'Start' pada bot di Telegram.")

if __name__ == "__main__":
    main()

