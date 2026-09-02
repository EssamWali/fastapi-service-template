from httpx import AsyncClient


async def test_missing_key_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/items")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_wrong_key_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/items", headers={"X-API-Key": "nope"})
    assert response.status_code == 401


async def test_valid_key_is_accepted(client: AsyncClient, auth: dict[str, str]) -> None:
    response = await client.get("/items", headers=auth)
    assert response.status_code == 200


async def test_error_body_includes_request_id(client: AsyncClient) -> None:
    response = await client.get("/items")
    assert response.json()["request_id"]
