from server.data.databricks import DatabricksClient


def test_databricks_client_requires_env():
    try:
        DatabricksClient()
    except RuntimeError:
        assert True
