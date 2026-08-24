from ai.ai_translator import ClaudeTranslator


class FakeContentBlock:
    text = "Texto traducido"


class FakeMessage:
    content = [FakeContentBlock()]


class FakeMessages:
    def __init__(self):
        self.prompt = None
        self.model = None

    def create(self, model, max_tokens, messages):
        self.model = model
        self.prompt = messages[0]["content"]
        return FakeMessage()


class FakeClient:
    def __init__(self):
        self.messages = FakeMessages()


def main():
    client = FakeClient()
    translator = ClaudeTranslator(
        model="test-model",
        client=client
    )

    result = translator.translate(
        "Press __MTP_PROTECTED_0__",
        "en",
        "es",
        terminology={"Machine": "Máquina"},
        context="quest.description",
        previous_translation="Traducción rota",
        validation_error="placeholder_mismatch"
    )

    assert result == {
        "translation": "Texto traducido",
        "source": "claude"
    }
    assert client.messages.model == "test-model"
    assert "quest.description" in client.messages.prompt
    assert "Machine → Máquina" in client.messages.prompt
    assert "placeholder_mismatch" in client.messages.prompt
    assert "Traducción rota" in client.messages.prompt

    print("Claude translator adapter OK")


if __name__ == "__main__":
    main()
