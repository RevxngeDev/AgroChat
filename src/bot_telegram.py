import asyncio
import logging
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
from src.supabase_client import (
    get_or_create_user,
    update_user_lang,
    update_user_voice,
)
from src.speech_to_text import transcribe_audio_file
from src.text_to_speech import synthesize_speech_to_file_async

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

LANGUAGE_LABELS = {
    "es": "Español 🇪🇸",
    "en": "English 🇬🇧",
    "ru": "Русский 🇷🇺",
}


def get_user_lang(user_id: int | None) -> str:
    if user_id is None:
        return config.DEFAULT_LANG
    try:
        user = get_or_create_user(user_id)
        return user.get("lang") or config.DEFAULT_LANG
    except Exception as e:
        logger.warning("Failed to fetch user lang from Supabase: %s", e)
        return config.DEFAULT_LANG


def get_user_voice_reply_enabled(user_id: int | None) -> bool:
    if user_id is None:
        return False
    try:
        user = get_or_create_user(user_id)
        return bool(user.get("voice_enabled", False))
    except Exception as e:
        logger.warning("Failed to fetch user voice pref from Supabase: %s", e)
        return False


async def call_agrochat_api(question: str, lang: str, telegram_id: int | None = None) -> dict[str, Any]:
    url = f"{config.API_BASE_URL}/query"
    payload = {
        "question": question,
        "lang": lang,
        "top_k": config.TOP_K,
        "telegram_id": telegram_id,
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


async def safe_reply_text(update: Update, text: str, max_retries: int = 3, parse_mode: str | None = None) -> None:
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            if update.message:
                await update.message.reply_text(text, parse_mode=parse_mode)
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(text, parse_mode=parse_mode)
            return
        except Exception as e:
            if parse_mode and "parse entities" in str(e).lower():
                try:
                    if update.message:
                        await update.message.reply_text(text)
                    elif update.callback_query and update.callback_query.message:
                        await update.callback_query.message.reply_text(text)
                    return
                except (TimedOut, NetworkError):
                    pass
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


async def show_language_selector(update: Update, lang: str | None = None) -> None:
    if lang:
        lang_pack = get_lang_pack(lang)
        text = lang_pack["bot_select_language"]
    else:
        text = " / ".join(
            get_lang_pack(code)["bot_select_language"]
            for code in get_supported_languages()
        )

    keyboard = build_language_keyboard()

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_language_selector(update)


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    lang = get_user_lang(user_id)
    await show_language_selector(update, lang=lang)


async def voice_toggle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    lang = get_user_lang(user_id)
    lang_pack = get_lang_pack(lang)

    if user_id is None:
        return

    current = get_user_voice_reply_enabled(user_id)
    new_value = not current

    try:
        update_user_voice(user_id, new_value)
    except Exception as e:
        logger.exception("Failed to update voice preference: %s", e)
        await safe_reply_text(update, lang_pack["bot_unexpected_error"].format(error=e))
        return

    if new_value:
        await safe_reply_text(update, lang_pack["bot_voice_reply_enabled"])
    else:
        await safe_reply_text(update, lang_pack["bot_voice_reply_disabled"])
        

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

    try:
        update_user_lang(query.from_user.id, lang)
    except Exception as e:
        logger.exception("Failed to update language: %s", e)
        return

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

    top_sources = sources[:3]
    formatted = []
    for s in top_sources:
        formatted.append(
            f"  📄 {s.get('file', lang_pack['bot_unknown_file'])} "
            f"({lang_pack['bot_page_abbrev']} {s.get('page', '?')})"
        )

    return (
        f"\n\n{'─' * 28}\n"
        f"📚 *{lang_pack['bot_main_sources']}*\n"
        + "\n".join(formatted)
    )


async def _run_text_query(update: Update, question: str, lang: str) -> str:
    lang_pack = get_lang_pack(lang)

    user_id = update.effective_user.id if update.effective_user else None
    data = await call_agrochat_api(question, lang=lang, telegram_id=user_id)
    answer = data.get("answer", lang_pack["bot_no_answer"])
    sources = data.get("sources", [])
    extra = _format_sources(sources, lang_pack)

    final_text = f"🌱 {answer}{extra}"
    await safe_reply_text(update, final_text, parse_mode="Markdown")
    return final_text


async def _send_voice_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, lang: str) -> None:
    lang_pack = get_lang_pack(lang)
    temp_voice_path: Path | None = None

    try:
        if update.effective_chat:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.RECORD_VOICE,
            )

        config.TEMP_TTS_DIR.mkdir(parents=True, exist_ok=True)
        temp_voice_path = config.TEMP_TTS_DIR / f"{uuid4()}.mp3"

        await synthesize_speech_to_file_async(
            text=text,
            output_path=temp_voice_path,
            lang=lang,
        )

        if update.message:
            with temp_voice_path.open("rb") as audio_file:
                await update.message.reply_voice(voice=audio_file)

    except Exception as e:
        logger.exception("Voice reply generation error")
        await safe_reply_text(update, lang_pack["bot_voice_reply_error"].format(error=e))
    finally:
        if temp_voice_path and temp_voice_path.exists():
            try:
                temp_voice_path.unlink()
            except OSError:
                logger.warning("Could not delete temp TTS file: %s", temp_voice_path)

async def _send_voice_reply_safe(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, lang: str) -> None:
    """Wrapper for background voice generation. Errors are logged, not raised."""
    try:
        await _send_voice_reply(update, context, text, lang)
    except Exception as e:
        logger.exception("Background voice reply failed: %s", e)
        
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
        final_text = await _run_text_query(update, question, lang)

        if get_user_voice_reply_enabled(user_id):
            asyncio.create_task(
                _send_voice_reply_safe(update, context, final_text, lang)
            )

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

        await safe_reply_text(update, f"🎤 *{lang_pack['bot_voice_transcribed_as']}*\n_{transcript}_", parse_mode="Markdown")

        await safe_send_chat_action(update, context)
        final_text = await _run_text_query(update, transcript, lang)

        if get_user_voice_reply_enabled(user_id):
            asyncio.create_task(
                _send_voice_reply_safe(update, context, final_text, lang)
            )

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
    application.add_handler(CommandHandler("voice", voice_toggle_command))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern=r"^setlang:"))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    async def post_init(app: Application) -> None:
        default_pack = get_lang_pack("es")
        await app.bot.set_my_commands([
            ("start", default_pack["cmd_start"]),
            ("help", default_pack["cmd_help"]),
            ("language", default_pack["cmd_language"]),
            ("voice", default_pack["cmd_voice"]),
        ])

        for lang_code in get_supported_languages():
            lp = get_lang_pack(lang_code)
            await app.bot.set_my_commands([
                ("start", lp["cmd_start"]),
                ("help", lp["cmd_help"]),
                ("language", lp["cmd_language"]),
                ("voice", lp["cmd_voice"]),
            ], language_code=lang_code)

    application.post_init = post_init

    logger.info("Starting AgroChat Telegram bot...")
    application.run_polling()


if __name__ == "__main__":
    main()