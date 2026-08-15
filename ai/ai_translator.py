import json
import os
from urllib.request import Request, urlopen

from ai.prompt_builder import build_translation_prompt


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
