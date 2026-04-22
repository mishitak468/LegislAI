from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from langchain_core.runnables import RunnableConfig

ModelName = Literal["gemini", "claude", "gpt4o"]

DEFAULT_MODEL: ModelName = "gemini"


def get_llm(config: RunnableConfig | None = None):
    model_name: ModelName = DEFAULT_MODEL
    if config and "configurable" in config:
        model_name = config["configurable"].get("model", DEFAULT_MODEL)

    return _build_llm(model_name)


@lru_cache(maxsize=4)
def _build_llm(model_name: ModelName):
    if model_name == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.environ["GOOGLE_API_KEY"],
            temperature=0.2,
        )

    elif model_name == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            api_key=os.environ["ANTHROPIC_API_KEY"],
            temperature=0.2,
        )

    elif model_name == "gpt4o":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o",
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=0.2,
        )

    else:
        raise ValueError(
            f"Unknown model: {model_name}. Choose gemini | claude | gpt4o")
