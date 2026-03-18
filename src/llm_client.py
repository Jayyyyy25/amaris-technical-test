"""
LLM Client

Thin wrapper around the Groq SDK.
All other modules call this — none of them import groq directly.

Responsibilities:
- Load and validate the API key
- Expose a single `complete()` method
- Translate SDK errors into clean RuntimeErrors
- Expose `is_available()` so the UI can gate LLM features gracefully
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq, APIError, APIConnectionError, RateLimitError
from streamlit import json

load_dotenv()

# Default model — fast, free-tier friendly, 8 192-token context
DEFAULT_MODEL = "llama-3.1-8b-instant"


class GroqClient:
    """Wrapper around the Groq chat-completions API.

    Parameters
    ----------
    api_key:
        Groq API key.  Falls back to the ``GROQ_API_KEY`` environment
        variable (loaded from ``.env`` automatically).
    model:
        Model ID to use for every completion request.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self._api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model    = model
        self._client: Groq | None = None

        if self._api_key:
            self._client = Groq(api_key=self._api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return ``True`` if an API key is configured and the client is ready."""
        return bool(self._api_key and self._client is not None)

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Send a chat-completion request and return the response text.

        Parameters
        ----------
        system_prompt:
            Instructions and context for the model (role, rules, data).
        user_message:
            The actual user request or question.
        temperature:
            Sampling temperature.  Use ``0.1`` for factual Q&A,
            ``0.4`` for narrative summaries.
        max_tokens:
            Maximum tokens in the response.

        Returns
        -------
        str
            The model's reply, stripped of leading/trailing whitespace.

        Raises
        ------
        RuntimeError
            Wraps any Groq SDK error with a user-readable message.
        """
        if not self.is_available():
            raise RuntimeError(
                "Groq API key is not configured. "
                "Add GROQ_API_KEY to your .env file or enter it in the sidebar."
            )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()

        except RateLimitError:
            raise RuntimeError(
                "Groq rate limit reached. Please wait a moment and try again."
            )
        except APIConnectionError:
            raise RuntimeError(
                "Could not connect to the Groq API. Check your internet connection."
            )
        except APIError as exc:
            raise RuntimeError(f"Groq API error: {exc}") from exc
