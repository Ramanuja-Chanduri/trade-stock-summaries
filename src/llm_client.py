"""LLM client module for TradeSummaryAI.

Provides functions for direct LLM generation and web-search-augmented
generation using LangChain + OpenAI + DuckDuckGo.
"""

import os
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.tools import DuckDuckGoSearchResults

from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)

settings = get_settings()

llm = ChatGroq(model="openai/gpt-oss-20b", api_key=settings.GROQ_API_KEY, temperature=0.7)

embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

search_tool = DuckDuckGoSearchResults(max_results=5)


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

    logger.debug(f"Calling LLM with prompt length: {len(prompt)} chars")
    
    try:
        response = llm.invoke(messages)
        logger.debug(f"LLM response received, length: {len(response.content)} chars")
        return response.content
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
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
    logger.info(f"Starting web search for query: {prompt[:100]}...")
    
    # Step 1: Web search
    try:
        search_results = search_tool.invoke(prompt)
        logger.debug(f"Search completed, results length: {len(search_results)} chars")
    except Exception as e:
        logger.warning(f"Search failed: {e}")
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

    logger.debug(f"Calling LLM with search-augmented prompt, length: {len(enriched_prompt)} chars")
    
    try:
        response = llm.invoke(messages)
        logger.info(f"LLM with search completed, response length: {len(response.content)} chars")
        return response.content
    except Exception as e:
        logger.error(f"Error calling LLM with search: {e}")
        return f"Error calling LLM with search: {e}"


def get_embedding(text: str) -> list:
    """Return the embedding vector for a single text string."""
    logger.debug(f"Generating embedding for text length: {len(text)} chars")
    try:
        embedding = embeddings_model.embed_query(text)
        logger.debug(f"Embedding generated, dimensions: {len(embedding)}")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return []


def get_embeddings_batch(texts: List[str]) -> list:
    """Return embedding vectors for a list of text strings."""
    logger.debug(f"Generating embeddings batch for {len(texts)} texts")
    try:
        embeddings = embeddings_model.embed_documents(texts)
        logger.debug(f"Batch embeddings generated, count: {len(embeddings)}")
        return embeddings
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        return []
