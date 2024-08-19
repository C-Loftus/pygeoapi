import json

import pytest
import shapely.wkt

from pygeoapi.provider.base import ProviderQueryError
from pygeoapi.provider.rise_api_types import LocationResponse
from pygeoapi.provider.rise_edr_helpers import (
    CatalogItem,
    CacheInterface,
    LocationHelper,
    fetch_url_group,
    flatten_values,
    fetch_url,
    RISECache,
    getResultUrlFromCatalogUrl,
    merge_pages,
    parse_bbox,
    parse_z,
    ZType,
)

import shapely

import asyncio

import requests
import time


def test_get_catalogItems():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)
        items = LocationHelper.get_catalogItemURLs(data)
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
        items = LocationHelper.get_catalogItemURLs(data)
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
        assert len(content["data"]) == 593
        break


def test_fetch_all_only_fetches_one_if_one_page():
    url = "https://data.usbr.gov/rise/api/location/1"
    pages = RISECache.get_or_fetch_all_pages(url, force_fetch=True)
    assert len(pages) == 1

    res = requests.get(url, headers={"accept": "application/vnd.api+json"}).json()
    assert res["data"] == pages[url]["data"]


def test_interface():
    with pytest.raises(TypeError):
        _ = CacheInterface()  # type: ignore


def test_z_parse():
    assert (ZType.SINGLE, [10]) == parse_z("10")
    assert (ZType.RANGE, [10, 20]) == parse_z("10/20")
    assert (ZType.ENUMERATED_LIST, [10, 20, 30]) == parse_z("10,20,30")

    assert (ZType.ENUMERATED_LIST, [100, 150]) == parse_z("R2/100/50")

    with pytest.raises(ProviderQueryError):
        parse_z("10/20/30")

    with pytest.raises(ProviderQueryError):
        parse_z("10//30")

    with pytest.raises(ProviderQueryError):
        parse_z("10,20,30,")


def test_shapely_sanity_check():
    geo: dict = {
        "type": "Point",
        "coordinates": [-104.855255, 39.651378],
    }

    result = shapely.geometry.shape(geo)

    wkt = "POLYGON((-79 40,-79 38,-75 38,-75 41,-79 40))"

    wkt_parsed = shapely.wkt.loads(wkt)
    assert not wkt_parsed.contains(result)

    assert int(float("4530.000000")) == 4530
    location_6902_geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [-111.49544, 36.94029],
                [-111.49544, 36.99597],
                [-111.47861, 36.99597],
                [-111.47861, 36.94029],
                [-111.49544, 36.94029],
            ]
        ],
    }

    point_inside = "POINT(-111.48 36.95)"
    point_inside = shapely.wkt.loads(point_inside)

    assert shapely.geometry.shape(location_6902_geom).contains(point_inside)

    point_outside = "POINT(-111.5 46.95)"
    point_outside = shapely.wkt.loads(point_outside)

    assert not shapely.geometry.shape(location_6902_geom).contains(point_outside)


def test_wkt_filter():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)

        res = LocationHelper.filter_by_wkt(data, wkt=None, z="4530")

        assert res["data"][0]["attributes"]["_id"] == 6888
        assert len(res["data"]) == 1
        wkt = "POLYGON((-79 40,-79 38,-75 38,-75 41,-79 40))"

        # Query that should not return anything
        res = LocationHelper.filter_by_wkt(data, wkt, z="4530")

        assert len(res["data"]) == 0

        locations_inside_this = "POINT(-106.849378 33.821858)"

        res = LocationHelper.filter_by_wkt(data, wkt=locations_inside_this, z=None)
        assert len(res["data"]) == 1
        assert res["data"][0]["attributes"]["_id"] == 6888

        locations_inside_this = (
            "POLYGON((-150 -150,-150 150,150 150,150 -150,-150 -150))"
        )
        # all locations should be returned if we have a
        res = LocationHelper.filter_by_wkt(data, wkt=locations_inside_this, z=None)
        assert len(res["data"]) == 25


def test_parse_bbox():
    bbox = ["-6.0", "50.0", "-4.35", "52.0"]
    parse_result = parse_bbox(bbox)
    shapely_bbox = parse_result[0]
    assert shapely_bbox
    zval = parse_result[1]
    assert not zval

    wkt = "POINT(-5.0 51)"
    single_point = shapely.wkt.loads(wkt)

    parse_result = parse_bbox(bbox)
    if parse_result[0]:
        assert parse_result[0].contains(single_point)
    else:
        assert False


def test_limit_items():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)

        res1 = LocationHelper.filter_by_limit(data, limit=1)
        assert len(res1["data"]) == 1

        res2 = LocationHelper.filter_by_limit(data, limit=10)
        assert len(res2["data"]) == 10
        assert (
            res2["data"][0]["attributes"]["_id"] == res1["data"][0]["attributes"]["_id"]
        )


def test_filter_by_id():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)

        res = LocationHelper.filter_by_id(data, identifier="6902")
        assert res["data"][0]["attributes"]["_id"] == 6902

        res = LocationHelper.filter_by_id(data, identifier="6903")
        assert len(res["data"]) == 0


def test_get_or_fetch_group():
    group = [
        "https://data.usbr.gov/rise/api/catalog-item/128632",
        "https://data.usbr.gov/rise/api/location?page=1&itemsPerPage=25",
    ]

    urlToContent = asyncio.run(RISECache.get_or_fetch_group(group))

    assert len(urlToContent.values()) == 2
    assert urlToContent[group[1]]["data"][0]["id"] == "/rise/api/location/509"


def test_fill_catalogItems():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)
        assert len(data["data"]) == 25

        res = LocationHelper.filter_by_id(data, identifier="6902")
        assert res["data"][0]["attributes"]["_id"] == 6902
        assert len(res["data"]) == 1
        assert (
            res["data"][0]["relationships"]["catalogItems"]["data"][0]["id"]
            == "/rise/api/catalog-item/128632"
        )

        # Fill in the catalog items and make sure that the only two
        # remaining catalog items are the catalog items associated with location
        # 6902 since we previously filtered to just that location

        expanded = LocationHelper.fill_catalogItems(res)

        assert expanded["data"][0]["relationships"]["catalogItems"] is not None

        assert len(expanded["data"][0]["relationships"]["catalogItems"]["data"]) == 2
        assert (
            expanded["data"][0]["relationships"]["catalogItems"]["data"][0]["id"]
            == "/rise/api/catalog-item/128632"
        )
        assert (
            expanded["data"][0]["relationships"]["catalogItems"]["data"][1]["id"]
            == "/rise/api/catalog-item/128633"
        )


# def test_get_results():
#     with open("tests/data/rise/location.json") as f:
#         data: LocationResponse = json.load(f)

#         # "locationName": "Turquoise Lake and Sugar Loaf Dam",
#         one_location = LocationHelper.filter_by_id(data, identifier="498")

#         catItems = LocationHelper.get_catalogItemURLs(one_location)

#         for location in catItems:
#             for item in catItems[location]:
#                 # we have the entire api url but we only want the id so
#                 # we can pass the id to the result endpoint
#                 raw_item = item.removeprefix(
#                     "https://data.usbr.gov/rise/api/catalog-item/"
#                 )

#                 res = CatalogItem.get_results(raw_item)
#                 assert res is not None
#                 assert res[0]["attributes"]["result"] == 34681  # type: ignore

#                 # only test the first one for the sake of brevity
#                 break


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


def test_make_result():
    url = "https://data.usbr.gov/rise/api/catalog-item/128632"
    res = getResultUrlFromCatalogUrl(url)
    resp = requests.get(res)
    assert resp.ok


def test_expand_with_results():
    with open("tests/data/rise/location.json") as f:
        data = json.load(f)

        # filter just 268 which contains catalog item 4 which has results
        res = LocationHelper.filter_by_id(data, identifier="268")

        expanded = LocationHelper.fill_catalogItems(res, add_results=True)

        assert expanded["data"][0]["relationships"]["catalogItems"] is not None

        assert len(expanded["data"][0]["relationships"]["catalogItems"]["data"]) == 5

    ids = [
        item["id"]
        for item in expanded["data"][0]["relationships"]["catalogItems"]["data"]
    ]
    assert "/rise/api/catalog-item/4" in ids
    assert "/rise/api/catalog-item/141" in ids
    assert "/rise/api/catalog-item/142" in ids
    assert "/rise/api/catalog-item/144" in ids
    assert "/rise/api/catalog-item/11279" in ids


def test_fields_to_covjson():
    field_ids = RISECache.get_parameters().keys()
    length = len(field_ids)
    assert length == len(set(field_ids))

    assert requests.get(
        "https://data.usbr.gov/rise/api/parameter/4225",
        headers={"accept": "application/vnd.api+json"},
    ).ok

    res = LocationHelper._fields_to_covjson(only_include_ids=["4223"])
    x = 5
