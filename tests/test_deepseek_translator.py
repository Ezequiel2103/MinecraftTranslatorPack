from ai.ai_translator import DeepSeekTranslator


class FakeMessage:
    content = "Texto traducido"


class FakeChoice:
    message = FakeMessage()


class FakeCompletion:
    choices = [FakeChoice()]


class FakeCompletions:
    def __init__(self):
        self.prompt = None
        self.model = None

    def create(self, model, messages):
        self.model = model
        self.prompt = messages[0]["content"]
        return FakeCompletion()


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def main():
    client = FakeClient()
    translator = DeepSeekTranslator(
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
        "source": "deepseek"
    }
    assert client.chat.completions.model == "test-model"
    assert "quest.description" in client.chat.completions.prompt
    assert "Machine → Máquina" in client.chat.completions.prompt
    assert "placeholder_mismatch" in client.chat.completions.prompt
    assert "Traducción rota" in client.chat.completions.prompt

    print("DeepSeek translator adapter OK")


if __name__ == "__main__":
    main()
