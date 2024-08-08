import json

import pytest

from pygeoapi.provider.rise_edr_helpers import (
    LocationHelper,
    fetch_url_group,
    flatten_values,
    fetch_url,
    RISECache,
    CacheInterface,
    merge_pages,
)


import asyncio

import requests
import time


def test_get_catalogItems():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)
        items = LocationHelper.get_catalogItems(data)
        assert len(items) == 25


def test_fetch():
    url = "https://data.usbr.gov/rise/api/catalog-item/128562"
    resp = requests.get(
        url,
        headers={"accept": "application/vnd.api+json"},
    )
    assert resp.json()

    async_resp = asyncio.run(fetch_url(url))
    assert async_resp == resp.json()


def test_remove_location():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)
        dropped = LocationHelper.drop_location(data, 6902)
        assert len(data["data"]) - 1 == len(dropped["data"])
        assert dropped["data"][0]["attributes"]["_id"] != 6902


def test_fetch_group():
    urls = [
        "https://data.usbr.gov/rise/api/catalog-item/128562",
        "https://data.usbr.gov/rise/api/catalog-item/128563",
        "https://data.usbr.gov/rise/api/catalog-item/128564",
    ]

    resp = asyncio.run(fetch_url_group(urls))
    assert len(resp) == 3
    assert None not in resp


def test_get_parameters():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)
        items = LocationHelper.get_catalogItems(data)
        assert len(items) == 25
        assert len(flatten_values(items)) == 236

    with open("tests/data/rise/location.json") as f:
        data = json.load(f)
        locationsToParams = LocationHelper.get_parameters(data)
        assert len(locationsToParams.keys()) > 0
        # Test it contains a random catalog item from the location
        assert RISECache.contains("https://data.usbr.gov/rise/api/catalog-item/128573")
        assert "18" in flatten_values(locationsToParams)  # type: ignore


def test_fetch_all_pages():
    url = "https://data.usbr.gov/rise/api/location"
    pages = RISECache.get_or_fetch_all_pages(url)

    # There are 6 pages so we should get 6 responses
    assert len(pages) == 6
    for url, resp in pages.items():
        # 100 is the max number of items you can query
        # so we should get 100 items per page
        assert resp["meta"]["itemsPerPage"] == 100


def test_merge_pages():
    fetched_mock = {
        "https://data.usbr.gov/rise/api/location2": {
            "data": [
                {"id": "https://data.usbr.gov/rise/api/catalog-item/128564"},
                {"id": "https://data.usbr.gov/rise/api/catalog-item/128565"},
            ]
        },
        "https://data.usbr.gov/rise/api/location1": {
            "data": [
                {"id": "https://data.usbr.gov/rise/api/catalog-item/128562"},
                {"id": "https://data.usbr.gov/rise/api/catalog-item/128563"},
            ]
        },
    }

    merged = merge_pages(fetched_mock)
    for url, content in merged.items():
        assert content is not None
        assert content["data"]
        assert len(content["data"]) == 4


def test_integration_merge_pages():
    url = "https://data.usbr.gov/rise/api/location"

    pages = RISECache.get_or_fetch_all_pages(url, force_fetch=True)
    merged = merge_pages(pages)
    for url, content in merged.items():
        assert content is not None
        assert content["data"]
        assert len(content["data"]) == 592
        break


def test_fetch_all_only_fetches_one_if_one_page():
    url = "https://data.usbr.gov/rise/api/location/1"
    pages = RISECache.get_or_fetch_all_pages(url, force_fetch=True)
    assert len(pages) == 1

    res = requests.get(url, headers={"accept": "application/vnd.api+json"}).json()
    assert res["data"] == pages[url]["data"]


def test_cache():
    url = "https://data.usbr.gov/rise/api/catalog-item/128562"

    start = time.time()
    RISECache.clear(url)
    remote_res = asyncio.run(RISECache.get_or_fetch(url))
    assert remote_res
    network_time = time.time() - start

    assert RISECache.contains(url)

    start = time.time()
    RISECache.clear(url)
    assert not RISECache.contains(url)
    disk_res = asyncio.run(RISECache.get_or_fetch(url))
    assert disk_res
    disk_time = time.time() - start

    assert disk_time < network_time
    assert remote_res == disk_res


def test_interface():
    with pytest.raises(TypeError):
        _ = CacheInterface()  # type: ignore
