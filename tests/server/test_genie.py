from server.data.genie import GenieClient


def test_genie_requires_env():
    client = GenieClient()
    try:
        client.generate_sql("count hospitals")
    except RuntimeError as exc:
        assert "Genie" in str(exc)
