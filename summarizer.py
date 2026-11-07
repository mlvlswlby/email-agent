import html
import logging
import requests

logger = logging.getLogger(__name__)

class EmailSummarizer:
    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash-lite"):
        self.api_key = api_key.strip()
        self.model_name = model_name
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"

    def summarize(self, sender: str, subject: str, body: str) -> str:
        """
        Summarizes the email content using Gemini REST API.
        """
        truncated_body = body[:8000] if len(body) > 8000 else body

        prompt = f"""Kamu adalah asisten AI cerdas untuk memfilter dan meringkas email masuk.
Tugasmu adalah membuat ringkasan singkat, jelas, dan padat dari email berikut dalam Bahasa Indonesia.

Informasi Email:
- Pengirim: {sender}
- Subjek: {subject}
- Isi Email:
\"\"\"
{truncated_body}
\"\"\"

Instruksi Ringkasan:
1. Ringkas intisari atau maksud utama email dalam 2 sampai 4 poin penting (bullet points).
2. Tentukan tingkat urgensi: [Rendah / Sedang / Mendesak].
3. Sebutkan tindakan yang diperlukan (Action Item), misalnya: "Perlu balasan konfirmasi", "Hanya informasi/receipt", "Perlu verifikasi OTP/link", dsb.

Format output WAJIB persis seperti berikut (jangan gunakan markdown bintang ganda atau tanda pagar, cukup format teks bersih):
Ringkasan:
• Poin 1
• Poin 2
• (Poin 3 jika perlu)

Urgensi: [Rendah/Sedang/Mendesak]
Tindakan: [Tindakan yang perlu diambil]
"""
        url = f"{self.base_url}?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 600
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=20)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            else:
                logger.error(f"Gemini API returned error: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error calling Gemini REST API: {e}")

        return "Ringkasan otomatis tidak tersedia. Silakan cek langsung email Anda."

    def format_telegram_message(self, sender: str, subject: str, date: str, summary: str, message_id: str) -> str:
        """
        Formats the summarized email into an aesthetically pleasing Telegram HTML message.
        """
        safe_sender = html.escape(sender or "Tidak diketahui")
        safe_subject = html.escape(subject or "(Tanpa Subjek)")
        safe_date = html.escape(date or "")
        safe_summary = html.escape(summary)

        msg = (
            f"📬 <b>Email Baru Masuk</b>\n\n"
            f"👤 <b>Pengirim:</b> {safe_sender}\n"
            f"📌 <b>Subjek:</b> {safe_subject}\n"
        )
        if safe_date:
            msg += f"🕒 <b>Waktu:</b> {safe_date}\n"

        msg += f"\n📝 <b>Analisis & Ringkasan AI:</b>\n{safe_summary}\n"

        if message_id:
            gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{message_id}"
            msg += f"\n🔗 <a href=\"{gmail_link}\">Buka di Gmail</a>"

        return msg
