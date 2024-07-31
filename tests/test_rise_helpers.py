import json
from pygeoapi.provider.rise_edr_helpers import (
    Location,
    fetch_url_group,
    flatten,
    fetch_url,
    RISECache,
)
from pygeoapi.provider import rise_edr
import asyncio

import requests
import time


def test_get_catalogItems():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)
        items = Location.get_catalogItems(data)
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


def test_fetch_group():
    urls = [
        "https://data.usbr.gov/rise/api/catalog-item/128562",
        "https://data.usbr.gov/rise/api/catalog-item/128563",
        "https://data.usbr.gov/rise/api/catalog-item/128564",
    ]

    resp = asyncio.run(fetch_url_group(urls))
    assert len(resp) == 3
    assert None not in resp


def test_cache():
    url = "https://data.usbr.gov/rise/api/catalog-item/128562"

    start = time.time()
    RISECache.clear(url)
    remote_res = asyncio.run(RISECache.get_or_fetch(url))
    assert remote_res
    network_time = time.time() - start

    start = time.time()
    RISECache.clear(url)
    disk_res = asyncio.run(RISECache.get_or_fetch(url))
    assert disk_res
    disk_time = time.time() - start

    assert disk_time < network_time
    assert remote_res == disk_res


def test_get_parameters():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)
        items = Location.get_catalogItems(data)
        assert len(items) == 25
        assert len(flatten(items)) == 236

    with open("tests/data/rise/location.json") as f:
        data = json.load(f)
        params = Location.get_parameters(data)
        assert len(params) == 0
