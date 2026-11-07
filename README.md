# 📬 Gmail AI Telegram Notifier Agent

Agent cerdas yang memantau email baru di akun Gmail Anda, merangkum isinya menggunakan AI (Google Gemini), dan langsung mengirimkan notifikasi rangkuman ke akun Telegram Anda secara berkala.

---

## 🌟 Fitur Utama

- **Otomatis & Real-time Polling**: Memantau inbox Gmail setiap interval tertentu (default: 60 detik).
- **AI-Powered Summarization**: Menggunakan Gemini AI untuk mengekstrak intisari email, menentukan tingkat urgensi (*Rendah/Sedang/Mendesak*), serta mendeteksi *action item*.
- **Aman & Anti-Spam**: Memiliki cache lokal `processed_emails.json` agar email yang sama tidak dikirimkan ulang dua kali.
- **Tautan Langsung**: Dilengkapi tombol/link langsung untuk membuka email terkait di Gmail.

---

## 🚀 Panduan Setup Langkah-demi-Langkah

### 1. Dapatkan Token Bot & Chat ID Telegram
1. Buka aplikasi **Telegram**, cari akun resmi **[@BotFather](https://t.me/BotFather)**.
2. Kirim pesan `/newbot`, lalu ikuti instruksi (beri nama bot dan username berakhiran `bot`).
3. Anda akan mendapatkan **HTTP API Bot Token** (contoh: `7123456789:AAH...`).
4. Buka bot yang baru dibuat tersebut dan tekan tombol **Start** (`/start`).
5. Untuk mengetahui **Chat ID** akun Telegram Anda:
   - Cari akun bot **[@userinfobot](https://t.me/userinfobot)** di Telegram.
   - Kirim pesan apa saja atau klik `/start`.
   - Bot tersebut akan membalas dengan `Id: 123456789` (angka inilah Chat ID Anda).

---

### 2. Dapatkan Google Gemini API Key
1. Buka [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Login dengan akun Google Anda.
3. Klik **Create API key** lalu salin kuncinya.

---

### 3. Dapatkan `credentials.json` untuk Gmail API
1. Buka [Google Cloud Console](https://console.cloud.google.com/).
2. Buat Project baru (misal: `Email-Agent`).
3. Aktifkan **Gmail API**:
   - Buka menu **APIs & Services** > **Library**.
   - Cari `Gmail API`, lalu klik **Enable**.
4. Konfigurasi **OAuth Consent Screen**:
   - Buka **APIs & Services** > **OAuth consent screen**.
   - Pilih User Type: **External**, lalu klik **Create**.
   - Masukkan App Name (misal: `Gmail Agent`), User support email, dan Developer contact email.
   - Di bagian **Test users**, tambahkan alamat email Gmail Anda yang ingin dipantau.
   - Klik **Save and Continue**.
5. Buat **OAuth Client ID**:
   - Buka **APIs & Services** > **Credentials**.
   - Klik **+ CREATE CREDENTIALS** > **OAuth client ID**.
   - Pilih Application type: **Desktop app**.
   - Beri nama (misal: `Desktop Client`), lalu klik **Create**.
   - Klik tombol **Download JSON** pada kredensial yang dibuat.
   - Ubah nama file yang diunduh menjadi `credentials.json` dan letakkan di dalam folder proyek ini (`d:\Code\email-agent\credentials.json`).

---

### 4. Konfigurasi File `.env`
Salin file `.env.example` menjadi `.env`, lalu isi token Anda:

```bash
cp .env.example .env
```

Contoh isi `.env`:
```env
TELEGRAM_BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxx
CHECK_INTERVAL_SECONDS=60
MARK_AS_READ=True
```

---

### 5. Menjalankan Agent

1. **Jalankan pertama kali untuk otentikasi Gmail**:
   ```powershell
   .\venv\Scripts\python.exe main.py --once
   ```
   *Browser akan otomatis terbuka untuk meminta izin akun Gmail Anda. Klik **Lanjutkan** / **Izinkan**. Setelah berhasil, file `token.json` akan dibuat otomatis sehingga Anda tidak perlu login ulang.*

2. **Jalankan agent secara berkelanjutan (Daemon mode)**:
   ```powershell
   .\venv\Scripts\python.exe main.py
   ```
   *Agent akan mulai mengecek Gmail setiap 60 detik dan mengirimkan notifikasi ke Telegram jika ada email baru!*

