"""Azure OpenAI client wrapper"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from typing_extensions import Literal

load_dotenv()


@lru_cache(maxsize=1)
def get_llm_client(
    type: Literal["gpt5-full", "gpt4.1-mini"] = "gpt5-full",
) -> AzureChatOpenAI:
    """
    Get Azure OpenAI client (cached singleton).

    Returns:
        AzureChatOpenAI client instance

    Raises:
        ValueError: If required environment variables are missing
    """
    api_key = os.getenv("AZURE_LLM_API_KEY")
    endpoint = os.getenv("AZURE_LLM_ENDPOINT")

    if not api_key:
        raise ValueError("AZURE_LLM_API_KEY environment variable not set")
    if not endpoint:
        raise ValueError("AZURE_LLM_ENDPOINT environment variable not set")

    if type == "gpt5-full":
        llm = AzureChatOpenAI(
            api_key=api_key,  # type: ignore
            azure_endpoint=endpoint,  # type: ignore
            azure_deployment="gpt-5",  # type: ignore
            api_version="2024-08-01-preview",  # type: ignore
            verbose=False,
            reasoning_effort="low",
        )
    elif type == "gpt4.1-mini":
        llm = AzureChatOpenAI(
            api_key=api_key,  # type: ignore
            azure_endpoint=endpoint,  # type: ignore
            azure_deployment="gpt-4-1-mini",  # type: ignore
            api_version="2024-08-01-preview",  # type: ignore
            verbose=False,
            temperature=0,
        )

    return llm
