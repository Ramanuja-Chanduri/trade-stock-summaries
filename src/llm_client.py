"""LLM client module for TradeSummaryAI.

Provides functions for direct LLM generation and web-search-augmented
generation using LangChain + OpenAI + DuckDuckGo.
"""

import os
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.tools import DuckDuckGoSearchResults

# ---------------------------------------------------------------------------
# Clients (initialised at module level, lazily use OPENAI_API_KEY from env)
# ---------------------------------------------------------------------------

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=os.environ.get("OPENAI_API_KEY"),
)

embeddings_model = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.environ.get("OPENAI_API_KEY"),
)

search_tool = DuckDuckGoSearchResults(max_results=5)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Direct LLM call (no web search).

    Args:
        prompt: The user/human message to send.
        system_prompt: Optional system message prepended to the conversation.

    Returns:
        The LLM response text.
    """
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"Error calling LLM: {e}"


def call_llm_with_search(prompt: str) -> str:
    """Web-search-augmented LLM call.

    Step 1: Run a DuckDuckGo search using the prompt.
    Step 2: Combine search results with the original query.
    Step 3: Ask the LLM to summarise as a financial research analyst.

    Args:
        prompt: The search/research query.

    Returns:
        The LLM-summarised response informed by web search results.
    """
    # Step 1: Web search
    try:
        search_results = search_tool.invoke(prompt)
    except Exception:
        search_results = "No search results available"

    # Step 2: Build enriched prompt
    enriched_prompt = (
        f"Based on the following web search results, answer the query below.\n\n"
        f"--- Search Results ---\n{search_results}\n\n"
        f"--- Query ---\n{prompt}"
    )

    # Step 3: LLM summarisation
    system_prompt = "You are a financial research analyst"
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=enriched_prompt),
    ]

    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"Error calling LLM with search: {e}"


# ---------------------------------------------------------------------------
# Embedding helpers (for future use)
# ---------------------------------------------------------------------------

def get_embedding(text: str) -> list:
    """Return the embedding vector for a single text string."""
    try:
        return embeddings_model.embed_query(text)
    except Exception as e:
        return []


def get_embeddings_batch(texts: List[str]) -> list:
    """Return embedding vectors for a list of text strings."""
    try:
        return embeddings_model.embed_documents(texts)
    except Exception as e:
        return []
