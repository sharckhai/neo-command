from server.config import settings


def test_settings_defaults():
    assert settings.pipeline_target in {"local", "databricks"}
