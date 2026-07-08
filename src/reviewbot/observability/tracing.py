from functools import lru_cache

from langfuse.langchain import CallbackHandler


@lru_cache(maxsize=1)
def get_callback_handler() -> CallbackHandler:
    return CallbackHandler()
