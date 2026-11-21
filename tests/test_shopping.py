import json
from unittest.mock import AsyncMock

import pytest
from cookidoo_api import CookidooAdditionalItem, CookidooIngredientItem
from fastmcp import Client

import server


@pytest.fixture
def api(monkeypatch):
    api = AsyncMock()
    service = AsyncMock()
    service.client.return_value = api
    monkeypatch.setattr(server, "_cookidoo_service", service)
    return api


async def call(name, **kwargs):
    async with Client(server.mcp) as client:
        result = await client.call_tool(name, kwargs)
        return result.content[0].text


async def test_list_combines_items_and_recipes(api):
    api.get_ingredient_items.return_value = [CookidooIngredientItem("i", "Milk", False, "1 l")]
    api.get_additional_items.return_value = [CookidooAdditionalItem("a", "Bread", True)]
    api.get_shopping_list_recipes.return_value = []
    data = json.loads(await call("get_shopping_list"))
    assert data["ingredients"][0]["description"] == "1 l"
    assert data["additional_items"][0]["is_owned"] is True


async def test_mark_and_validate_ids(api):
    item = CookidooAdditionalItem("a", "Bread", False)
    api.get_additional_items.return_value = [item]
    api.edit_additional_items_ownership.return_value = [item]
    await call("set_shopping_items_owned", ids=["a"], owned=True, item_type="additional")
    assert api.edit_additional_items_ownership.await_args.args[0][0].is_owned is True
    api.edit_additional_items_ownership.reset_mock()
    with pytest.raises(Exception, match="not found"):
        await call(
            "set_shopping_items_owned", ids=["a", "missing"], owned=True, item_type="additional"
        )
    api.edit_additional_items_ownership.assert_not_awaited()


async def test_custom_recipe_routing(api):
    api.add_ingredient_items_for_custom_recipes.return_value = []
    await call("add_recipes_to_shopping_list", recipe_ids=["r1"], custom=True)
    api.add_ingredient_items_for_custom_recipes.assert_awaited_once_with(["r1"])
    await call("remove_recipes_from_shopping_list", recipe_ids=["r1"], custom=False)
    api.remove_ingredient_items_for_recipes.assert_awaited_once_with(["r1"])
