import asyncio
import logging
from typing import Any

import httpx
from telegram import Update
from telegram.constants import ChatAction
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src import config
from src.languages import get_lang_pack

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

BOT_LANG = "es"


async def call_agrochat_api(question: str) -> dict[str, Any]:
    url = f"{config.API_BASE_URL}/query"
    payload = {
        "question": question,
        "lang": BOT_LANG,
        "top_k": config.TOP_K,
    }

    timeout = httpx.Timeout(60.0, connect=20.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def safe_send_chat_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )
    except Exception as e:
        logger.warning("send_chat_action failed (ignored): %s", e)


async def safe_reply_text(
    update: Update,
    text: str,
    max_retries: int = 3,
) -> None:
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            await update.message.reply_text(text)
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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang_pack = get_lang_pack(BOT_LANG)
    await safe_reply_text(update, lang_pack["bot_welcome"])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang_pack = get_lang_pack(BOT_LANG)
    await safe_reply_text(update, lang_pack["bot_help"])


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    lang_pack = get_lang_pack(BOT_LANG)

    question = update.message.text.strip()
    if not question:
        return

    try:
        await safe_send_chat_action(update, context)

        data = await call_agrochat_api(question)

        answer = data.get("answer", "No pude obtener una respuesta.")
        sources = data.get("sources", [])

        extra = ""
        if sources:
            top_sources = sources[:2]
            formatted = []
            for s in top_sources:
                formatted.append(f"- {s.get('file', 'desconocido')} (pág. {s.get('page', '?')})")
            extra = f"\n\n{lang_pack['bot_main_sources']}\n" + "\n".join(formatted)

        await safe_reply_text(update, answer + extra)

    except httpx.HTTPStatusError as e:
        logger.exception("API HTTP error")
        await safe_reply_text(
            update,
            lang_pack["bot_api_error"].format(status_code=e.response.status_code),
        )
    except Exception as e:
        logger.exception("Unexpected bot error")
        await safe_reply_text(
            update,
            lang_pack["bot_unexpected_error"].format(error=e),
        )


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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("Starting AgroChat Telegram bot...")
    application.run_polling()


if __name__ == "__main__":
    main()