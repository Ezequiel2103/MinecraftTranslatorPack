from ai.ai_translator import OllamaTranslator


class FakeResponse:
    output_text = "Texto local"


class FakeResponses:
    def create(self, model, input):
        assert model == "qwen2.5:3b-instruct"
        assert "Translate" in input
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def main():
    translator = OllamaTranslator(
        model="qwen2.5:3b-instruct",
        client=FakeClient()
    )
    result = translator.translate(
        "Text",
        "en",
        "es"
    )

    assert result == {
        "translation": "Texto local",
        "source": "ollama"
    }
    print("Ollama translator adapter OK")


if __name__ == "__main__":
    main()
