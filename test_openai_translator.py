from ai.ai_translator import OpenAITranslator


class FakeResponse:
    output_text = "Texto traducido"


class FakeResponses:
    def __init__(self):
        self.prompt = None
        self.model = None

    def create(self, model, input):
        self.model = model
        self.prompt = input
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def main():
    client = FakeClient()
    translator = OpenAITranslator(
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
        "source": "openai"
    }
    assert client.responses.model == "test-model"
    assert "quest.description" in client.responses.prompt
    assert "Machine → Máquina" in client.responses.prompt
    assert "placeholder_mismatch" in client.responses.prompt
    assert "Traducción rota" in client.responses.prompt

    print("OpenAI translator adapter OK")


if __name__ == "__main__":
    main()
