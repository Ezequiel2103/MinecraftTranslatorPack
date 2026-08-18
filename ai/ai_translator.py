import json
import os
from urllib.request import Request, urlopen

from ai.prompt_builder import build_batch_translation_prompt, build_translation_prompt
from translation.api_usage import (
    DEFAULT_CHARACTER_LIMIT,
    record_usage,
    would_exceed
)


class QuotaExceededError(Exception):
    """
    Raised when sending this text would exceed a provider's configured
    usage quota. Callers should stop asking that provider for more
    translations rather than retry — retrying wastes time and cannot
    succeed until the quota resets.
    """


def parse_batch_json_response(raw_text):
    """
    Parses a batch-translation reply into {id: translation}, tolerating
    the ways an LLM can fail to "return only JSON" (markdown code fences,
    a stray sentence before/after). Returns {} if nothing usable is
    found — callers treat every id as missing and fall back to
    translating it individually rather than guessing at a bad parse.
    """

    text = raw_text.strip()

    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

    return {}


class AITranslator:
    """
    Base interface for AI translation providers.
    """

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):
        raise NotImplementedError(
            "AI translation provider not configured."
        )

    def translate_batch(
        self,
        texts_by_id,
        source_language,
        target_language,
        terminology=None,
        context=None
    ):
        """
        Translates many texts at once. The default just calls translate()
        once per text — always correct, no real batching benefit.
        Providers that can send several texts in a single request
        override this for the actual cost/speed win, so calling this
        method is always safe regardless of which provider is active.
        """

        return {
            item_id: self.translate(
                text, source_language, target_language,
                terminology=terminology, context=context
            )
            for item_id, text in texts_by_id.items()
        }


class OpenAITranslator(AITranslator):
    """OpenAI Responses API provider loaded only when explicitly selected."""

    def __init__(
        self,
        model=None,
        client=None,
        base_url=None,
        api_key=None
    ):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")

        if client is None:
            try:
                from openai import OpenAI
            except ImportError as error:
                raise RuntimeError(
                    "The OpenAI SDK is required for the openai provider. "
                    "Install it with: pip install openai"
                ) from error

            client = OpenAI(
                base_url=base_url,
                api_key=api_key
            ) if base_url or api_key else OpenAI()

        self.client = client

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):
        prompt = build_translation_prompt(
            text,
            source_language,
            target_language,
            terminology=terminology,
            context=context
        )

        if previous_translation or validation_error:
            prompt += "\nRetry information:\n"

            if previous_translation:
                prompt += (
                    f"Previous translation:\n{previous_translation}\n"
                )

            if validation_error:
                prompt += f"Validation error: {validation_error}\n"

            prompt += "Correct the specific validation problem.\n"

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        translation = response.output_text.strip()

        return {
            "translation": translation,
            "source": "openai"
        }

    def ask(self, prompt):
        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        return response.output_text.strip()

    def translate_batch(
        self,
        texts_by_id,
        source_language,
        target_language,
        terminology=None,
        context=None
    ):
        prompt = build_batch_translation_prompt(
            texts_by_id, source_language, target_language,
            terminology=terminology
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        parsed = parse_batch_json_response(response.output_text)

        return {
            item_id: {
                "translation": parsed.get(item_id),
                "source": "openai_batch"
            }
            for item_id in texts_by_id
        }


class OllamaTranslator(OpenAITranslator):
    """Local Ollama provider through its native HTTP API."""

    def __init__(self, model=None, client=None):
        self.model = model or os.getenv(
            "OLLAMA_MODEL",
            "qwen2.5:3b-instruct"
        )
        self.base_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434"
        ).rstrip("/")
        self.client = client

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):
        prompt = build_translation_prompt(
            text,
            source_language,
            target_language,
            terminology=terminology,
            context=context
        )

        if previous_translation or validation_error:
            prompt += "\nRetry information:\n"

            if previous_translation:
                prompt += (
                    f"Previous translation:\n{previous_translation}\n"
                )

            if validation_error:
                prompt += f"Validation error: {validation_error}\n"

            prompt += "Correct the specific validation problem.\n"

        if self.client is not None:
            response = self.client.responses.create(
                model=self.model,
                input=prompt
            )
            translation = response.output_text.strip()
        else:
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {
                    "num_predict": 256,
                    "temperature": 0.2
                }
            }).encode("utf-8")
            request = Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))

            translation = result.get("response", "").strip()

        return {
            "translation": translation,
            "source": "ollama"
        }

    def ask(self, prompt):
        if self.client is not None:
            response = self.client.responses.create(
                model=self.model,
                input=prompt
            )
            return response.output_text.strip()

        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "num_predict": 16,
                "temperature": 0.0
            }
        }).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))

        return result.get("response", "").strip()

    def translate_batch(
        self,
        texts_by_id,
        source_language,
        target_language,
        terminology=None,
        context=None
    ):
        prompt = build_batch_translation_prompt(
            texts_by_id, source_language, target_language,
            terminology=terminology
        )

        if self.client is not None:
            response = self.client.responses.create(
                model=self.model,
                input=prompt
            )
            raw_text = response.output_text
        else:
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {
                    "num_predict": 4096,
                    "temperature": 0.2
                }
            }).encode("utf-8")
            request = Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))

            raw_text = result.get("response", "")

        parsed = parse_batch_json_response(raw_text)

        return {
            item_id: {
                "translation": parsed.get(item_id),
                "source": "ollama_batch"
            }
            for item_id in texts_by_id
        }


class ClaudeTranslator(AITranslator):
    """Anthropic Claude provider loaded only when explicitly selected."""

    def __init__(
        self,
        model=None,
        client=None,
        api_key=None
    ):
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

        if client is None:
            try:
                from anthropic import Anthropic
            except ImportError as error:
                raise RuntimeError(
                    "The Anthropic SDK is required for the claude provider. "
                    "Install it with: pip install anthropic"
                ) from error

            client = Anthropic(api_key=api_key) if api_key else Anthropic()

        self.client = client

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):
        prompt = build_translation_prompt(
            text,
            source_language,
            target_language,
            terminology=terminology,
            context=context
        )

        if previous_translation or validation_error:
            prompt += "\nRetry information:\n"

            if previous_translation:
                prompt += (
                    f"Previous translation:\n{previous_translation}\n"
                )

            if validation_error:
                prompt += f"Validation error: {validation_error}\n"

            prompt += "Correct the specific validation problem.\n"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        translation = response.content[0].text.strip()

        return {
            "translation": translation,
            "source": "claude"
        }

    def ask(self, prompt):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    def translate_batch(
        self,
        texts_by_id,
        source_language,
        target_language,
        terminology=None,
        context=None
    ):
        prompt = build_batch_translation_prompt(
            texts_by_id, source_language, target_language,
            terminology=terminology
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        parsed = parse_batch_json_response(response.content[0].text)

        return {
            item_id: {
                "translation": parsed.get(item_id),
                "source": "claude_batch"
            }
            for item_id in texts_by_id
        }


class DeepSeekTranslator(AITranslator):
    """DeepSeek provider through its OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        model=None,
        client=None,
        api_key=None
    ):
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if client is None:
            try:
                from openai import OpenAI
            except ImportError as error:
                raise RuntimeError(
                    "The OpenAI SDK is required for the deepseek provider. "
                    "Install it with: pip install openai"
                ) from error

            client = OpenAI(
                base_url=os.getenv(
                    "DEEPSEEK_BASE_URL",
                    "https://api.deepseek.com"
                ),
                api_key=api_key or os.getenv("DEEPSEEK_API_KEY")
            )

        self.client = client

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):
        prompt = build_translation_prompt(
            text,
            source_language,
            target_language,
            terminology=terminology,
            context=context
        )

        if previous_translation or validation_error:
            prompt += "\nRetry information:\n"

            if previous_translation:
                prompt += (
                    f"Previous translation:\n{previous_translation}\n"
                )

            if validation_error:
                prompt += f"Validation error: {validation_error}\n"

            prompt += "Correct the specific validation problem.\n"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        translation = response.choices[0].message.content.strip()

        return {
            "translation": translation,
            "source": "deepseek"
        }

    def ask(self, prompt):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip()

    def translate_batch(
        self,
        texts_by_id,
        source_language,
        target_language,
        terminology=None,
        context=None
    ):
        prompt = build_batch_translation_prompt(
            texts_by_id, source_language, target_language,
            terminology=terminology
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        parsed = parse_batch_json_response(response.choices[0].message.content)

        return {
            item_id: {
                "translation": parsed.get(item_id),
                "source": "deepseek_batch"
            }
            for item_id in texts_by_id
        }


class GoogleTranslateTranslator(AITranslator):
    """
    Google Cloud Translation API (v2, plain API key — no SDK dependency).
    Unlike the other providers this isn't an LLM: it has no idea what
    "terminology" or "context" mean, it just translates the literal text
    it's given, which suits short, context-free strings like item/block
    names well. It tracks its own monthly character usage (see
    translation/api_usage.py) and refuses to place a call that would go
    over the configured limit, so a run stops itself before the free
    tier could ever actually be exceeded.
    """

    API_URL = "https://translation.googleapis.com/language/translate/v2"

    def __init__(self, api_key=None, char_limit=None):
        self.api_key = api_key or os.getenv("GOOGLE_TRANSLATE_API_KEY")
        self.char_limit = char_limit or DEFAULT_CHARACTER_LIMIT

        if not self.api_key:
            raise RuntimeError(
                "Google Translate requires an API key "
                "(GOOGLE_TRANSLATE_API_KEY)."
            )

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):
        if would_exceed(len(text), self.char_limit):
            raise QuotaExceededError(
                "Se alcanzó el límite mensual de caracteres gratis de "
                f"Google Translate ({self.char_limit})."
            )

        payload = json.dumps({
            "q": text,
            "source": source_language,
            "target": target_language,
            "format": "text"
        }).encode("utf-8")

        request = Request(
            f"{self.API_URL}?key={self.api_key}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        translation = result["data"]["translations"][0]["translatedText"]
        record_usage(len(text))

        return {
            "translation": translation,
            "source": "google_translate"
        }

    def ask(self, prompt):
        raise NotImplementedError(
            "Google Translate is a translation-only engine; it can't "
            "answer arbitrary prompts."
        )

    def translate_batch(
        self,
        texts_by_id,
        source_language,
        target_language,
        terminology=None,
        context=None
    ):
        ids = list(texts_by_id.keys())
        texts = [texts_by_id[item_id] for item_id in ids]
        total_chars = sum(len(text) for text in texts)

        if would_exceed(total_chars, self.char_limit):
            raise QuotaExceededError(
                "Se alcanzó el límite mensual de caracteres gratis de "
                f"Google Translate ({self.char_limit})."
            )

        payload = json.dumps({
            "q": texts,
            "source": source_language,
            "target": target_language,
            "format": "text"
        }).encode("utf-8")

        request = Request(
            f"{self.API_URL}?key={self.api_key}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        translations = result["data"]["translations"]

        # Google's v2 API returns translations in the same order as the
        # input array (a documented contract, unlike free-text LLM output)
        # — but if that ever doesn't hold, treat every id as missing
        # rather than risk pairing the wrong translation with a text.
        if len(translations) != len(ids):
            return {
                item_id: {"translation": None, "source": "google_batch"}
                for item_id in ids
            }

        record_usage(total_chars)

        return {
            item_id: {
                "translation": entry["translatedText"],
                "source": "google_translate_batch"
            }
            for item_id, entry in zip(ids, translations)
        }


class MockAITranslator(AITranslator):
    """
    Temporary translator used for testing.
    """

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):
        return {
            "translation": f"[AI] {text}",
            "source": "ai_mock"
        }

    def ask(self, prompt):
        return "CORRECT"


class RetryMockAITranslator(AITranslator):
    """
    Mock translator that intentionally fails once
    and then returns a valid translation.
    """

    def __init__(self):
        self.attempts = {}

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):

        attempt = self.attempts.get(
            text,
            0
        )

        self.attempts[text] = attempt + 1

        # First attempt intentionally fails
        if attempt == 0:

            return {
                "translation": "Traducción incorrecta",
                "source": "ai_retry_mock"
            }

        # Second attempt succeeds
        return {
            "translation": "Presiona %s para abrir %sMáquina\\n¡Bienvenido!",
            "source": "ai_retry_mock"
        }
