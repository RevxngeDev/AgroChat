import asyncio
import logging
import os
from pathlib import Path
from uuid import uuid4
from typing import Any

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src import config
from src.languages import get_lang_pack, get_supported_languages
from src.speech_to_text import transcribe_audio_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

USER_LANGS: dict[int, str] = {}

LANGUAGE_LABELS = {
    "es": "Español 🇪🇸",
    "en": "English 🇬🇧",
    "ru": "Русский 🇷🇺",
}


def get_user_lang(user_id: int | None) -> str:
    if user_id is None:
        return config.DEFAULT_LANG
    return USER_LANGS.get(user_id, config.DEFAULT_LANG)


async def call_agrochat_api(question: str, lang: str) -> dict[str, Any]:
    url = f"{config.API_BASE_URL}/query"
    payload = {
        "question": question,
        "lang": lang,
        "top_k": config.TOP_K,
    }

    timeout = httpx.Timeout(60.0, connect=20.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def safe_send_chat_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if update.effective_chat:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING,
            )
    except Exception as e:
        logger.warning("send_chat_action failed (ignored): %s", e)


async def safe_reply_text(update: Update, text: str, max_retries: int = 3) -> None:
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            if update.message:
                await update.message.reply_text(text)
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(text)
            return
        except (TimedOut, NetworkError) as e:
            last_error = e
            wait_seconds = min(2 * attempt, 8)
            logger.warning(
                "Telegram send timeout/network error (attempt %d/%d): %s. Retrying in %.1fs",
                attempt,
                max_retries,
                e,
                wait_seconds,
            )
            await asyncio.sleep(wait_seconds)
        except Exception as e:
            raise e

    raise last_error


def build_language_keyboard() -> InlineKeyboardMarkup:
    supported = get_supported_languages()
    row = [
        InlineKeyboardButton(
            LANGUAGE_LABELS.get(lang_code, lang_code.upper()),
            callback_data=f"setlang:{lang_code}",
        )
        for lang_code in supported
    ]
    return InlineKeyboardMarkup([row])


async def show_language_selector(update: Update) -> None:
    text = "Seleccione el idioma / Select a language / Выберите язык:"
    keyboard = build_language_keyboard()

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_language_selector(update)


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_language_selector(update)


async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if not query.from_user:
        return

    data = query.data or ""
    if not data.startswith("setlang:"):
        return

    lang = data.split(":", 1)[1].strip()
    if lang not in get_supported_languages():
        return

    USER_LANGS[query.from_user.id] = lang
    lang_pack = get_lang_pack(lang)

    try:
        await query.edit_message_text(text=f"✅ {LANGUAGE_LABELS.get(lang, lang.upper())}")
    except Exception:
        pass

    await safe_reply_text(update, lang_pack["bot_welcome"])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    lang = get_user_lang(user_id)
    lang_pack = get_lang_pack(lang)
    await safe_reply_text(update, lang_pack["bot_help"])


def _format_sources(sources: list[dict[str, Any]], lang_pack: dict) -> str:
    if not sources:
        return ""

    top_sources = sources[:2]
    formatted = []
    for s in top_sources:
        formatted.append(
            f"- {s.get('file', lang_pack['bot_unknown_file'])} "
            f"({lang_pack['bot_page_abbrev']} {s.get('page', '?')})"
        )

    return f"\n\n{lang_pack['bot_main_sources']}\n" + "\n".join(formatted)


async def _run_text_query(update: Update, question: str, lang: str) -> None:
    lang_pack = get_lang_pack(lang)

    data = await call_agrochat_api(question, lang=lang)
    answer = data.get("answer", "No pude obtener una respuesta.")
    sources = data.get("sources", [])
    extra = _format_sources(sources, lang_pack)

    await safe_reply_text(update, answer + extra)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id if update.effective_user else None
    lang = get_user_lang(user_id)

    question = update.message.text.strip()
    if not question:
        return

    try:
        await safe_send_chat_action(update, context)
        await _run_text_query(update, question, lang)
    except httpx.HTTPStatusError as e:
        lang_pack = get_lang_pack(lang)
        logger.exception("API HTTP error")
        await safe_reply_text(update, lang_pack["bot_api_error"].format(status_code=e.response.status_code))
    except Exception as e:
        lang_pack = get_lang_pack(lang)
        logger.exception("Unexpected bot error")
        await safe_reply_text(update, lang_pack["bot_unexpected_error"].format(error=e))


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        return

    user_id = update.effective_user.id if update.effective_user else None
    lang = get_user_lang(user_id)
    lang_pack = get_lang_pack(lang)

    temp_file_path: Path | None = None

    try:
        await safe_reply_text(update, lang_pack["bot_voice_processing"])

        config.TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

        voice = update.message.voice
        telegram_file = await voice.get_file()

        temp_file_path = config.TEMP_AUDIO_DIR / f"{uuid4()}.ogg"
        await telegram_file.download_to_drive(custom_path=str(temp_file_path))

        transcript = transcribe_audio_file(temp_file_path)

        if not transcript.strip():
            await safe_reply_text(update, lang_pack["bot_voice_empty"])
            return

        await safe_reply_text(
            update,
            f"{lang_pack['bot_voice_transcribed_as']}\n{transcript}",
        )

        await safe_send_chat_action(update, context)
        await _run_text_query(update, transcript, lang)

    except httpx.HTTPStatusError as e:
        logger.exception("API HTTP error after voice transcription")
        await safe_reply_text(update, lang_pack["bot_api_error"].format(status_code=e.response.status_code))
    except Exception as e:
        logger.exception("Voice processing error")
        await safe_reply_text(update, lang_pack["bot_voice_error"].format(error=e))
    finally:
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except OSError:
                logger.warning("Could not delete temp audio file: %s", temp_file_path)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled telegram error", exc_info=context.error)


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN no está configurado en .env")

    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .connect_timeout(20.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(10.0)
        .get_updates_connect_timeout(20.0)
        .get_updates_read_timeout(30.0)
        .get_updates_write_timeout(30.0)
        .get_updates_pool_timeout(10.0)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern=r"^setlang:"))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("Starting AgroChat Telegram bot...")
    application.run_polling()


if __name__ == "__main__":
    main()