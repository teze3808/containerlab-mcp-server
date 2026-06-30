import httpx

from containerlab_mcp.client import ContainerlabClient
from containerlab_mcp.config import Settings


def test_resolve_container_name_accepts_full_container_name() -> None:
    client = ContainerlabClient(
        Settings(api_url="https://example.test", username="u", password="p")
    )

    assert client.resolve_container_name("lab", "clab-lab-cx1") == "clab-lab-cx1"
    client.close()


def test_decode_response_returns_text_for_yaml() -> None:
    response = httpx.Response(
        200,
        headers={"content-type": "text/plain"},
        text="name: demo\n",
    )

    assert ContainerlabClient._decode_response(response) == "name: demo\n"
