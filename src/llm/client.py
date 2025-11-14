"""Azure OpenAI client wrapper"""

import os
from langchain_openai import AzureChatOpenAI
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_llm_client() -> AzureChatOpenAI:
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

    llm = AzureChatOpenAI(
        api_key=api_key,  # type: ignore
        azure_endpoint=endpoint,  # type: ignore
        azure_deployment="gpt-5",  # type: ignore
        api_version="2024-08-01-preview",  # type: ignore
        verbose=False,
        reasoning_effort="low",
    )

    return llm
