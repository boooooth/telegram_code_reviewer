import asyncio
import logging
import signal

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from reviewbot.config import settings
from reviewbot.graph.build import build_graph
from reviewbot.telegram.handlers import (
    IN_FLIGHT_TASKS_KEY,
    forget_command,
    new_session_command,
    plain_message,
    prune_command,
    review_command,
)

SHUTDOWN_DRAIN_TIMEOUT = 30

BOT_COMMANDS = [
    ("review", "Review a GitHub PR: /review <url>"),
    ("new", "Start a new session (clears working memory)"),
    ("forget", "Clear learned facts about your codebase/preferences"),
    ("prune", "Delete review history older than N days: /prune <days>"),
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


async def run() -> None:
    async with AsyncSqliteSaver.from_conn_string(str(settings.checkpoint_db_path)) as checkpointer:
        app = ApplicationBuilder().token(settings.telegram_bot_token).build()
        app.bot_data["graph"] = build_graph(checkpointer)
        app.bot_data["checkpointer"] = checkpointer
        app.add_handler(CommandHandler("review", review_command))
        app.add_handler(CommandHandler("new", new_session_command))
        app.add_handler(CommandHandler("forget", forget_command))
        app.add_handler(CommandHandler("prune", prune_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_message))

        assert app.updater is not None
        updater = app.updater

        async with app:
            await app.start()
            await app.bot.set_my_commands(BOT_COMMANDS)
            await updater.start_polling()

            stop_event = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, stop_event.set)
                except NotImplementedError:
                    pass  # not supported on Windows; Ctrl+C still works via KeyboardInterrupt

            try:
                await stop_event.wait()
            finally:
                in_flight = app.bot_data.get(IN_FLIGHT_TASKS_KEY)
                if in_flight:
                    await asyncio.wait(in_flight, timeout=SHUTDOWN_DRAIN_TIMEOUT)
                await updater.stop()
                await app.stop()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
