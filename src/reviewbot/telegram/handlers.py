import asyncio
import logging
from typing import Any, Coroutine

import httpx
from langfuse import get_client
from telegram import Update
from telegram.ext import ContextTypes

from reviewbot.config import settings
from reviewbot.memory.episodic import delete_events_older_than
from reviewbot.memory.semantic import clear_facts
from reviewbot.observability.eval import LOW_CONFIDENCE_THRESHOLD, score_review
from reviewbot.observability.tracing import get_callback_handler
from reviewbot.telegram.formatting import split_for_telegram

logger = logging.getLogger(__name__)

IN_FLIGHT_TASKS_KEY = "in_flight_tasks"


def _is_authorized(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id == settings.telegram_allowed_user_id


def _track_task(context: ContextTypes.DEFAULT_TYPE, coro: Coroutine[Any, Any, None]) -> "asyncio.Task[None]":
    """Wraps coro in a Task registered in bot_data so shutdown can wait for
    it to finish instead of dropping it mid-review."""
    tasks: set[asyncio.Task[None]] = context.application.bot_data.setdefault(IN_FLIGHT_TASKS_KEY, set())
    task = asyncio.create_task(coro)
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return task


async def _run_review(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_input: str) -> None:
    assert update.message is not None and update.effective_chat is not None
    chat_id = update.effective_chat.id
    await update.message.chat.send_action("typing")

    graph = context.application.bot_data["graph"]
    handler = get_callback_handler()
    config = {
        "configurable": {"thread_id": str(chat_id)},
        "callbacks": [handler],
    }
    result = await graph.ainvoke({"chat_id": chat_id, "raw_input": raw_input}, config=config)
    reply = result["reply"]

    if result.get("source") == "pr":
        score, reason = await asyncio.to_thread(score_review, result.get("review_target", ""), reply)
        trace_id = getattr(handler, "last_trace_id", None)
        if trace_id:
            get_client().create_score(trace_id=trace_id, name="review_quality", value=score, comment=reason)

        if score < LOW_CONFIDENCE_THRESHOLD:
            reply = f"⚠️ Low-confidence review (score {score:.2f}): {reason}\n\n{reply}"
        else:
            reply = f"{reply}\n\n(review quality score: {score:.2f})"

    for chunk in split_for_telegram(reply):
        await update.message.reply_text(chunk, parse_mode="HTML")


async def _run_review_safely(
    update: Update, context: ContextTypes.DEFAULT_TYPE, raw_input: str, fallback: str
) -> None:
    assert update.message is not None
    try:
        await _run_review(update, context, raw_input)
    except httpx.HTTPStatusError as e:
        logger.exception("review failed")
        status = e.response.status_code
        if status == 404:
            message = "PR not found — check the URL, or if it's a private repo, set GITHUB_TOKEN."
        elif status == 403:
            message = "GitHub rate limit hit — try again later, or set GITHUB_TOKEN for a higher limit."
        else:
            message = f"GitHub returned an error ({status}) fetching that PR."
        await update.message.reply_text(message)
    except httpx.TimeoutException:
        logger.exception("review failed")
        await update.message.reply_text("GitHub took too long to respond — try again.")
    except Exception:
        logger.exception("review failed")
        await update.message.reply_text(fallback)


async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    assert update.message is not None
    if not context.args:
        await update.message.reply_text("Usage: /review <github PR url>")
        return

    pr_url = context.args[0]
    await _track_task(
        context, _run_review_safely(update, context, pr_url, "Something went wrong fetching or reviewing that PR.")
    )


async def new_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    assert update.message is not None and update.effective_chat is not None
    chat_id = update.effective_chat.id
    checkpointer = context.application.bot_data["checkpointer"]
    await checkpointer.adelete_thread(str(chat_id))
    await update.message.reply_text(
        "Started a new session — working memory cleared. Your review history and learned "
        "facts are still there; only this chat's ongoing conversation context was reset."
    )


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    assert update.message is not None and update.effective_chat is not None
    chat_id = update.effective_chat.id
    await asyncio.to_thread(clear_facts, chat_id)
    await update.message.reply_text(
        "Cleared all learned facts about your codebase/preferences. Review history and "
        "working memory are untouched — only the long-term semantic notes were wiped."
    )


async def prune_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    assert update.message is not None and update.effective_chat is not None
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /prune <days> — deletes review history older than N days.")
        return

    days = int(context.args[0])
    chat_id = update.effective_chat.id
    deleted = await asyncio.to_thread(delete_events_older_than, chat_id, days)
    await update.message.reply_text(
        f"Deleted {deleted} review record(s) older than {days} day(s). "
        "Learned facts and working memory are untouched."
    )


async def plain_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    assert update.message is not None
    text = update.message.text
    if not text or not text.strip():
        return

    await _track_task(context, _run_review_safely(update, context, text, "Something went wrong reviewing that."))
