import json
from pygeoapi.provider.rise_edr_helpers import (
    LocationHelper,
    fetch_url_group,
    flatten_values,
    fetch_url,
    RISECache,
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
        assert "Streamflow" in flatten_values(locationsToParams)  # type: ignore

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