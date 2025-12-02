"""Azure OpenAI client wrapper"""

import os
from typing import Union

from dotenv import load_dotenv
from langchain_core.runnables import Runnable
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel
from typing_extensions import Literal

load_dotenv()


def get_llm_client(
    type: Literal["gpt5.1-low", "gpt4.1-mini", "gpt4.1"] = "gpt5.1-low",
    output_structure: type[BaseModel] | None = None,
) -> Union[AzureChatOpenAI, Runnable]:
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

    if type == "gpt5.1-low":
        llm = AzureChatOpenAI(
            api_key=api_key,  # type: ignore
            azure_endpoint=endpoint,  # type: ignore
            azure_deployment="gpt-5.1",  # type: ignore
            api_version="",  # type: ignore
            verbose=False,
            reasoning_effort="low",
        )
    elif type == "gpt4.1-mini":
        llm = AzureChatOpenAI(
            api_key=api_key,  # type: ignore
            azure_endpoint=endpoint,  # type: ignore
            azure_deployment="gpt-4.1-mini",  # type: ignore
            api_version="2024-08-01-preview",  # type: ignore
            verbose=False,
            temperature=0,
        )
    elif type == "gpt4.1":
        llm = AzureChatOpenAI(
            api_key=api_key,  # type: ignore
            azure_endpoint=endpoint,  # type: ignore
            azure_deployment="gpt-4.1",  # type: ignore
            api_version="2024-08-01-preview",  # type: ignore
            verbose=False,
            temperature=0,
        )

    if output_structure:
        llm = llm.with_structured_output(output_structure)  # type: ignore

    return llm
