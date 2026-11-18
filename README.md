# Aruna — Agent AI di Telegram (otak: Dahl Inference)

Agent AI seperti Muse, tapi lewat Telegram. Otaknya Dahl Inference, model teks
(`MiniMaxAI/MiniMax-M2.7` default, bisa ganti ke DeepSeek V4 Flash / GLM-5.3-Flash).

## Cara pakai

Kirim pesan apa saja, Aruna jawab dan ingat obrolan di chat itu.

- `/start` — sapaan
- `/help` — bantuan
- `/reset` — hapus ingatan chat ini
- `/model` — lihat model yang dipakai
- `/model <nama>` — ganti model, contoh `/model deepseek-ai/DeepSeek-V4-Flash-0731`

## Yang dibutuhkan

Buat bot dulu di Telegram: buka [@BotFather](https://t.me/BotFather), kirim `/newbot`,
ikuti namanya, simpan tokennya.

Dahl: key dari https://inference.dahl.global/account. Alokasikan token dari
pool akun ke key itu di halaman yang sama, kalau tidak key akan jawab 402.

## Env var (jangan tulis nilainya di repo/chat)

```
BOT_TOKEN=
DAHL_API_KEY=
DAHL_MODEL=MiniMaxAI/MiniMax-M2.7
ALLOWED_USER_IDS=
MAX_HISTORY=20
```

`ALLOWED_USER_IDS` opsional: ID Telegram yang boleh pakai, pisah spasi.
Kosong = semua orang bisa pakai. Untuk agent pribadi, isi ID kamu.

## Jalankan lokal

```
pip install -r requirements.txt
BOT_TOKEN=... DAHL_API_KEY=... python bot.py
```

## Deploy gratis

Sama seperti bot IMAP checker kemarin: FadeHost Free, `python bot.py`,
repo GitHub public, env var `BOT_TOKEN` + `DAHL_API_KEY`.

## Batasan jujur

- Teks saja. Dahl tidak bisa gambar/video.
- Tidak punya akses ke file, kalender, email, atau akun pengguna seperti
  Muse di sini. Tools tambahan harus dikode satu per satu.
- Ingatan hanya di memori proses (hilang kalau bot restart) dan dibatasi
  `MAX_HISTORY` pesan terakhir per chat.
