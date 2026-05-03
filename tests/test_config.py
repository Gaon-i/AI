from app.core.config import Settings


def test_settings_from_environment() -> None:
    settings = Settings()

    assert settings.app_env == "test"
    assert settings.app_name == "gaon-i-ai-test"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_url == "sqlite+pysqlite:///:memory:"
    assert settings.chat_answer_model == "gpt-4o-mini"
    assert settings.chat_single_dormitory_top_k == 3
    assert settings.chat_grouped_dormitory_top_k == 3
    assert settings.chat_grouped_dormitories == ["제1학생생활관", "제2학생생활관", "제3학생생활관"]
    assert settings.regulation_chunk_max_length == 400
