import socket

# Force IPv4 — prevents timeout on some HuggingFace network configurations
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

import os
import json
import time
import logging
import threading
from datetime import datetime
from dotenv import load_dotenv
import gradio as gr

from gmail_service import GmailService
from summarizer import EmailSummarizer
from telegram_service import TelegramService

load_dotenv()

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("EmailAgent")

CACHE_FILE = "processed_emails.json"

# ─── Shared state (read by Gradio UI) ───────────────────────────────────────
state = {
    "status": "⏳ Memulai agent...",
    "last_check": "-",
    "emails_processed": 0,
    "log": [],
}


def add_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    state["log"].append(entry)
    state["log"] = state["log"][-60:]   # keep last 60 lines
    logger.info(msg)


def load_processed_ids() -> set:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def save_processed_ids(ids: set):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(list(ids)[-500:], f)
    except Exception as e:
        logger.warning(f"Cannot save cache: {e}")


# ─── Background email-polling agent ─────────────────────────────────────────
def run_agent():
    tg_token     = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat_id   = os.getenv("TELEGRAM_CHAT_ID")
    gemini_key   = os.getenv("GEMINI_API_KEY")
    interval     = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
    mark_read    = os.getenv("MARK_AS_READ", "True").lower() in ("true", "1", "yes")

    # Validate secrets
    missing = [k for k, v in {
        "TELEGRAM_BOT_TOKEN": tg_token,
        "TELEGRAM_CHAT_ID": tg_chat_id,
        "GEMINI_API_KEY": gemini_key,
    }.items() if not v]

    if missing:
        state["status"] = "❌ Secrets belum lengkap!"
        add_log(f"ERROR: Secret berikut belum diisi: {', '.join(missing)}")
        add_log("Buka Settings > Secrets di Space HuggingFace Anda, lalu restart Space.")
        return

    tg      = TelegramService(tg_token, tg_chat_id)
    summ    = EmailSummarizer(gemini_key)
    gmail   = GmailService()

    # Test Telegram
    if not tg.test_connection():
        state["status"] = "❌ Gagal konek ke Telegram Bot"
        add_log("ERROR: TELEGRAM_BOT_TOKEN tidak valid atau bot belum di-Start.")
        return

    # Authenticate Gmail
    try:
        gmail.authenticate()
    except Exception as e:
        state["status"] = "❌ Gagal autentikasi Gmail"
        add_log(f"ERROR Gmail auth: {e}")
        return

    processed_ids = load_processed_ids()
    state["status"] = "✅ Agent aktif — memantau inbox Gmail"
    add_log("Agent berhasil diinisialisasi. Memulai pemantauan email...")

    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            state["last_check"] = now
            add_log("Mengecek email baru...")

            emails = gmail.get_unread_emails()
            new_count = 0

            for email in emails:
                msg_id = email["id"]
                if msg_id in processed_ids:
                    continue

                new_count += 1
                add_log(f"📧 '{email['subject']}' dari {email['sender']}")

                summary = summ.summarize(email["sender"], email["subject"], email["body"])
                tg_msg  = summ.format_telegram_message(
                    email["sender"], email["subject"],
                    email["date"], summary, msg_id
                )

                if tg.send_message(tg_msg):
                    processed_ids.add(msg_id)
                    state["emails_processed"] += 1
                    save_processed_ids(processed_ids)
                    add_log("✅ Notifikasi terkirim ke Telegram.")
                    if mark_read:
                        gmail.mark_as_read(msg_id)

            if new_count == 0:
                add_log("Tidak ada email baru.")

        except Exception as e:
            err = str(e)[:120]
            add_log(f"⚠️ Error: {err}")
            state["status"] = f"⚠️ Error (auto-retry): {err}"
            time.sleep(10)   # brief pause before next cycle on error
            continue

        time.sleep(interval)


# Start background thread immediately
threading.Thread(target=run_agent, daemon=True).start()


# ─── Gradio UI ───────────────────────────────────────────────────────────────
def get_dashboard():
    logs = "\n".join(state["log"][-25:])
    return state["status"], state["last_check"], str(state["emails_processed"]), logs


with gr.Blocks(title="📬 Gmail AI Email Agent", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 📬 Gmail AI Email Notifier Agent
    Agent ini berjalan **24/7** memantau inbox Gmail Anda dan mengirim ringkasan AI ke **Telegram** secara otomatis.
    """)

    with gr.Row():
        status_out     = gr.Textbox(label="🔴 Status Agent", interactive=False, scale=3)
        last_check_out = gr.Textbox(label="🕒 Pengecekan Terakhir", interactive=False, scale=2)
        count_out      = gr.Textbox(label="📨 Email Diproses", interactive=False, scale=1)

    log_out = gr.Textbox(label="📋 Log Aktivitas (25 baris terakhir)",
                         interactive=False, lines=18, max_lines=18)

    refresh_btn = gr.Button("🔄 Refresh Status", variant="primary")
    refresh_btn.click(fn=get_dashboard,
                      outputs=[status_out, last_check_out, count_out, log_out])

    # Auto-refresh on page load
    demo.load(fn=get_dashboard,
              outputs=[status_out, last_check_out, count_out, log_out])

    gr.Markdown("""
    ---
    > 💡 **Tip:** Gunakan [UptimeRobot](https://uptimerobot.com) (gratis) untuk ping URL Space ini setiap 5 menit
    > agar agent tidak pernah tidur (*sleep*).
    """)


demo.launch(server_name="0.0.0.0", server_port=7860)
