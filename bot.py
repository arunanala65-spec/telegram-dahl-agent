"""
Aruna — Agent AI di Telegram, otaknya Dahl Inference
====================================================
Agent AI seperti Muse, tapi lewat Telegram. Otak: Dahl Inference
(OpenAI-compatible, https://inference.dahl.global/v1).

Cara pakai di Telegram:
  Kirim pesan apa saja, Aruna jawab.
  /start — sapaan + panduan
  /help — bantuan
  /reset — hapus ingatan chat ini, mulai baru
  /model — lihat model yang dipakai
  /model MiniMaxAI/MiniMax-M2.7 — ganti model (per chat)

Yang dibutuhkan (env var, JANGAN tulis di kode/repo/chat):
  BOT_TOKEN — token bot dari @BotFather
  DAHL_API_KEY — key dari https://inference.dahl.global/account
  DAHL_MODEL — opsional, default MiniMaxAI/MiniMax-M2.7
  ALLOWED_USER_IDS — opsional, ID Telegram yang boleh pakai, pisah spasi.
    Kosong = semua orang bisa pakai. Untuk agent pribadi, isi ID kamu.
  MAX_HISTORY — opsional, default 20 pesan terakhir per chat

Catatan jujur:
- Ini agent teks saja. Dahl tidak bisa gambar/video, dan bot ini tidak
  punya akses ke file, kalender, atau akun kamu seperti Muse di sini.
  Kemampuan tambahannya (tools) harus dikode satu per satu.
- Token Dahl gratis 100 juta sekali dari pool akun. Key baru jawab 402
  kalau token belum dialokasikan ke key itu di /account.
"""

import asyncio
import logging
import os
import time

import httpx
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------- Config ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DAHL_API_KEY = os.environ.get("DAHL_API_KEY", "").strip()
DAHL_BASE_URL = os.environ.get("DAHL_BASE_URL", "https://inference.dahl.global/v1").rstrip("/")
DEFAULT_MODEL = os.environ.get("DAHL_MODEL", "MiniMaxAI/MiniMax-M2.7").strip()
ALLOWED_USER_IDS = {
    int(x)
    for x in os.environ.get("ALLOWED_USER_IDS", "").replace(",", " ").split()
    if x.strip().isdigit()
}
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "20"))
DAHL_TIMEOUT = 60

SYSTEM_PROMPT = (
    "Kamu Aruna, asisten AI pribadi Rudy Alfa di Telegram. "
    "Jawab dalam Bahasa Indonesia, singkat, jelas, dan hangat seperti teman. "
    "Bantu jawab pertanyaan, menulis, merangkum, membuat ide, dan menjelaskan hal sulit dengan sederhana. "
    "Kalau tidak tahu, bilang tidak tahu, jangan mengarang. "
    "Jangan klaim kamu bisa mengakses file, kalender, email, atau akun pengguna, karena kamu hanya bisa mengobrol di chat ini."
)

KNOWN_MODELS = [
    "MiniMaxAI/MiniMax-M2.7",
    "deepseek-ai/DeepSeek-V4-Flash-0731",
    "zai-org/GLM-5.3-Flash",
]

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("aruna-telegram-agent")

# Ingatan per chat: {chat_id: {"model": str, "messages": [{"role": str, "content": str}]}}
_chats: dict[int, dict] = {}


def get_chat(chat_id: int) -> dict:
    state = _chats.get(chat_id)
    if state is None:
        state = {"model": DEFAULT_MODEL, "messages": []}
        _chats[chat_id] = state
    return state


def is_allowed(update: Update) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return update.effective_user is not None and update.effective_user.id in ALLOWED_USER_IDS


def split_text(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts


async def ask_dahl(state: dict, user_text: str) -> str:
    """Kirim riwayat chat ke Dahl, kembalikan jawaban teks."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(state["messages"][-MAX_HISTORY:])
    messages.append({"role": "user", "content": user_text})

    async with httpx.AsyncClient(timeout=DAHL_TIMEOUT) as client:
        resp = await client.post(
            f"{DAHL_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DAHL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": state["model"],
                "messages": messages,
            },
        )
    if resp.status_code == 200:
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return "Maaf, jawaban Dahl kosong. Coba lagi ya."
        return (content or "").strip() or "Maaf, jawaban Dahl kosong. Coba lagi ya."
    if resp.status_code == 401:
        return "Key Dahl tidak valid (401). Cek DAHL_API_KEY di hosting, lalu coba lagi."
    if resp.status_code == 402:
        return (
            "Token Dahl di key ini habis / belum dialokasikan (402). "
            "Buka https://inference.dahl.global/account lalu alokasikan token dari pool akun ke key ini."
        )
    if resp.status_code == 429:
        return "Dahl lagi penuh (429). Tunggu sebentar lalu coba lagi, atau ganti model dengan /model."
    if resp.status_code == 404:
        return (
            f"Model {state['model']} tidak tersedia saat ini (404). "
            "Coba /model lalu pilih model lain dari daftar."
        )
    return f"Dahl error {resp.status_code}. Coba lagi sebentar lagi."


START_TEXT = """Halo! Aku Aruna, agent AI kamu di Telegram. 👋

Kirim saja pesan apa pun, aku jawab. Aku ingat obrolan kita di chat ini sampai kamu /reset.

Perintah:
• /help — bantuan
• /reset — hapus ingatan, mulai baru
• /model — lihat / ganti model Dahl

Aku agent teks saja: bisa jawab, menulis, merangkum, dan memberi ide. Aku tidak bisa buat gambar/video dan tidak bisa akses file atau akunmu.
"""

HELP_TEXT = """Bantuan — Aruna

• Kirim pesan biasa untuk ngobrol / bertanya.
• /reset — hapus riwayat chat ini.
• /model — lihat model Dahl yang dipakai sekarang.
• /model <nama> — ganti model, contoh:
  /model deepseek-ai/DeepSeek-V4-Flash-0731

Model yang biasanya tersedia:
• MiniMaxAI/MiniMax-M2.7
• deepseek-ai/DeepSeek-V4-Flash-0731
• zai-org/GLM-5.3-Flash

Kalau aku jawab token habis (402), token Dahl harus dialokasikan dulu di https://inference.dahl.global/account.
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("Maaf, bot ini privat.")
        return
    await update.message.reply_text(START_TEXT)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text(HELP_TEXT)


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    chat_id = update.effective_chat.id
    _chats.pop(chat_id, None)
    await update.message.reply_text("Ingatan di chat ini sudah dihapus. Mulai baru ya.")


async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    state = get_chat(update.effective_chat.id)
    args = context.args or []
    if not args:
        await update.message.reply_text(
            f"Model sekarang: {state['model']}\n\nPilihan umum:\n" + "\n".join(f"• {m}" for m in KNOWN_MODELS)
            + "\n\nGanti dengan: /model <nama>"
        )
        return
    wanted = args[0].strip()
    state["model"] = wanted
    await update.message.reply_text(f"Model diganti ke: {wanted}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("Maaf, bot ini privat.")
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    state = get_chat(update.effective_chat.id)
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        reply = await ask_dahl(state, text)
    except httpx.TimeoutException:
        await update.message.reply_text("Dahl timeout. Coba lagi ya.")
        return
    except Exception as e:  # noqa: BLE001 - sampaikan error apa adanya, tanpa bocor rahasia
        log.exception("Dahl call failed: %s", type(e).__name__)
        await update.message.reply_text("Maaf, ada error saat menghubungi Dahl. Coba lagi sebentar lagi.")
        return
    # Simpan ke ingatan hanya kalau jawabannya bukan pesan error konfigurasi
    if not reply.startswith(("Key Dahl tidak valid", "Token Dahl di key ini habis")):
        state["messages"].append({"role": "user", "content": text})
        state["messages"].append({"role": "assistant", "content": reply})
        state["messages"] = state["messages"][-MAX_HISTORY:]
    for part in split_text(reply):
        await update.message.reply_text(part)


def _start_keepalive_server():
    """Server HTTP kecil supaya hosting Web Service Free tidak menganggap bot mati."""
    port = int(os.environ.get("PORT", "0") or 0)
    if not port:
        return
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a):
            pass

    threading.Thread(target=HTTPServer(("0.0.0.0", port), H).serve_forever, daemon=True).start()
    log.info("Keep-alive HTTP jalan di port %s", port)


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN belum diisi. Isi env var BOT_TOKEN dari @BotFather.")
    if not DAHL_API_KEY:
        raise SystemExit("DAHL_API_KEY belum diisi. Isi env var DAHL_API_KEY dari https://inference.dahl.global/account")
    _start_keepalive_server()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Aruna jalan (polling). Model default: %s", DEFAULT_MODEL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
