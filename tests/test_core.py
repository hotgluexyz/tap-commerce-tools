"""Public extraction contract, including tied timestamps and nested payloads."""

import json
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from tap_commerce_tools.tap import TapCommerceTools

CONFIG = {
    "project_key": "demo",
    "client_id": "client",
    "client_secret": "secret",
    "scope": "view_products:demo",
    "page_size": 2,
}


@responses.activate
def test_pagination_nested_fields_and_incremental_boundary():
    stamp = "2026-10-26T12:00:00.000Z"
    nested = {
        "published": True,
        "current": {
            "name": {"en": "Boot"},
            "masterVariant": {
                "id": 1,
                "sku": "BOOT-8",
                "attributes": [{"name": "color", "value": "Forest"}],
                "prices": [{"value": {"centAmount": 12995, "currencyCode": "USD"}}],
            },
        },
    }
    responses.post(
        "https://auth.us-east-2.aws.commercetools.com/oauth/token",
        json={"access_token": "token", "expires_in": 3600},
    )
    url = "https://api.us-east-2.aws.commercetools.com/demo/products"
    rows = [{"id": x, "lastModifiedAt": stamp, "masterData": nested} for x in ["a", "b", "c"]]
    responses.get(url, json={"results": rows[:2]})
    responses.get(url, json={"results": rows[2:]})
    tap = TapCommerceTools(config=CONFIG | {"start_date": stamp})
    result = list(tap.streams["products"].get_records(None))
    assert result == rows
    query = parse_qs(urlparse(str(responses.calls[-1].request.url)).query)
    assert query["sort"] == ["lastModifiedAt asc", "id asc"]
    assert 'id > "b"' in query["where"][0]
    assert "lastModifiedAt >=" in query["where"][0]
    assert "offset" not in query
    assert responses.calls[0].request.headers["Authorization"].startswith("Basic ")
    assert responses.calls[1].request.headers["Authorization"] == "Bearer token"


@responses.activate
def test_sync_preserves_arbitrary_nested_attributes(capsys):
    responses.post(
        "https://auth.us-east-2.aws.commercetools.com/oauth/token",
        json={"access_token": "token", "expires_in": 3600},
    )
    product = {
        "id": "p1",
        "lastModifiedAt": "2026-10-26T12:00:00Z",
        "masterData": {
            "current": {
                "name": {"de": "Schuh"},
                "masterVariant": {
                    "sku": "S1",
                    "attributes": [{"name": "custom", "value": {"nested": [1, 2]}}],
                },
            }
        },
    }
    responses.get(
        "https://api.us-east-2.aws.commercetools.com/demo/products", json={"results": [product]}
    )
    tap = TapCommerceTools(config=CONFIG)
    stream = tap.streams["products"]
    stream.sync()
    records = [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.startswith('{"type": "RECORD"')
    ]
    assert records[0]["record"]["masterData"] == product["masterData"]


@pytest.mark.parametrize("size", [0, 501])
def test_page_size_bounds(size):
    with pytest.raises(ValueError, match="page_size"):
        TapCommerceTools(config=CONFIG | {"page_size": size})
