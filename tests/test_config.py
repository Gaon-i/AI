from app.core.config import Settings


def test_settings_from_environment() -> None:
    settings = Settings()

    assert settings.app_env == "test"
    assert settings.app_name == "gaon-i-ai-test"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_url == "sqlite+pysqlite:///:memory:"
