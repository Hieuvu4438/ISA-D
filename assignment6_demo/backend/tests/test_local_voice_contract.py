from app.domain import TextRequest, SearchOptions
from app.application.query_service import QueryService


def test_local_voice_source_survives_validation_and_query():
    request = TextRequest(mode="voice", text="túi màu nâu", voice_source="local")
    assert request.voice_source == "local"

    class Encoder:
        def validate_text(self, text):
            return text

        def encode_texts(self, texts):
            return [[1.0] * 512]

    query = QueryService(Encoder()).build_text("voice", request.text, SearchOptions(), "local")
    assert query.voice_source == "local"
