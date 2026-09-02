from httpx import AsyncClient


async def _create(client: AsyncClient, auth: dict[str, str], name: str) -> dict[str, object]:
    response = await client.post("/items", json={"name": name}, headers=auth)
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_and_read_roundtrip(client: AsyncClient, auth: dict[str, str]) -> None:
    created = await _create(client, auth, "widget")
    fetched = await client.get(f"/items/{created['id']}", headers=auth)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "widget"


async def test_duplicate_name_conflicts(client: AsyncClient, auth: dict[str, str]) -> None:
    await _create(client, auth, "widget")
    response = await client.post("/items", json={"name": "widget"}, headers=auth)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_unknown_id_is_404(client: AsyncClient, auth: dict[str, str]) -> None:
    response = await client.get("/items/00000000-0000-0000-0000-000000000000", headers=auth)
    assert response.status_code == 404


async def test_validation_error_names_the_field(client: AsyncClient, auth: dict[str, str]) -> None:
    response = await client.post("/items", json={"name": ""}, headers=auth)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_list_paginates_and_filters(client: AsyncClient, auth: dict[str, str]) -> None:
    for name in ("alpha", "beta", "gamma"):
        await _create(client, auth, name)

    page = (await client.get("/items?limit=2", headers=auth)).json()
    assert page["total"] == 3
    assert len(page["items"]) == 2

    filtered = (await client.get("/items?q=alph", headers=auth)).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["name"] == "alpha"


async def test_patch_updates_only_supplied_fields(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await _create(client, auth, "widget")
    response = await client.patch(
        f"/items/{created['id']}", json={"description": "now with a description"}, headers=auth
    )
    assert response.status_code == 200
    assert response.json()["name"] == "widget"
    assert response.json()["description"] == "now with a description"


async def test_delete_then_get_is_404(client: AsyncClient, auth: dict[str, str]) -> None:
    created = await _create(client, auth, "widget")
    assert (await client.delete(f"/items/{created['id']}", headers=auth)).status_code == 204
    assert (await client.get(f"/items/{created['id']}", headers=auth)).status_code == 404


async def test_cache_is_invalidated_on_update(client: AsyncClient, auth: dict[str, str]) -> None:
    created = await _create(client, auth, "widget")
    await client.get(f"/items/{created['id']}", headers=auth)  # warm the cache
    await client.patch(f"/items/{created['id']}", json={"name": "renamed"}, headers=auth)
    fetched = await client.get(f"/items/{created['id']}", headers=auth)
    assert fetched.json()["name"] == "renamed"
