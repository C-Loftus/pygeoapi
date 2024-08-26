import requests
import pytest

from pygeoapi.provider.rise import RiseProvider
from pygeoapi.provider.rise_edr import RiseEDRProvider


@pytest.fixture()
def config():
    return {
        "cache": "shelf",
    }


def test_location_locationId(config):
    p = RiseEDRProvider(config)
    out = p.locations(location_id=1, format_="covjson")
    # Returns 3 since we have 3 parameters in the location
    assert len(out["coverages"]) == 3
    # invalid location should return nothing
    out = p.locations(location_id=1111111111111111)
    assert len(out["coverages"]) == 0

    geojson_out: dict = p.locations(location_id=1, format_="geojson")  # type: ignore For some reason mypy complains
    assert geojson_out["type"] == "Feature"
    assert geojson_out["id"] == 1


def test_get_fields(config):
    p = RiseEDRProvider(config)
    fields = p.get_fields()

    # test to make sure a particular field is there
    assert fields["2"]["title"] == "Lake/Reservoir Elevation"

    assert requests.get(
        "https://data.usbr.gov/rise/api/parameter?page=1&itemsPerPage=25",
        headers={"accept": "application/vnd.api+json"},
    ).json()["meta"]["totalItems"] == len(fields)


def test_location_select_properties(config):
    # Currently in pygeoapi we use select_properties as the
    # keyword argument. This is hold over from OAF it seems.

    p = RiseEDRProvider(config)

    out = p.locations(select_properties="DUMMY-PARAM", format_="geojson")
    assert len(out["features"]) == 0  # type: ignore ; issues with pyright union types

    out = p.locations(select_properties="18", format_="geojson")
    assert len(out["features"]) > 0  # type: ignore

    out = p.locations(select_properties="2", format_="geojson")
    for f in out["features"]:  # type: ignore
        if f["id"] == 1:
            break
    else:
        # if location 1 isn't in the responses, then something is wrong
        assert False


def test_location_datetime(config):
    p = RiseEDRProvider(config)
    out = p.locations(datetime_="2024-03-29T15:49:57+00:00", format_="geojson")
    for i in out["features"]:  # type: ignore
        if i["id"] == 6902:
            break
    else:
        assert False

    out = p.locations(datetime="2024-03-29/..", format_="geojson")
    for i in out["features"]:  # type: ignore
        if i["id"] == 6902:
            break
    else:
        assert False


# def test_area():
#     p = RiseEDRProvider(config)

#     out = p.area()
#     assert len(out["features"]) > 0


def test_item(config):
    p = RiseProvider(config)
    out = p.items(itemId="1")
    out = out
    assert out["id"] == 1
    assert out["type"] == "Feature"


def test_cube(config):
    p = RiseEDRProvider(config)

    # random location near corpus christi should return only one feature
    out = p.area(
        wkt="POLYGON ((-98.96918309080456 28.682352643651612, -98.96918309080456 26.934669197978764, -94.3740448509505 26.934669197978764, -94.3740448509505 28.682352643651612, -98.96918309080456 28.682352643651612))"
    )

    assert out["type"] == "FeatureCollection"
    assert len(out["features"]) == 1
    assert out["features"][0]["id"] == 291


def test_polygon_output():
    # location id 3526 is a polygon
    p = RiseEDRProvider(config)

    out = p.locations(location_id=3526, format_="covjson")

    assert out["type"] == "CoverageCollection"


@pytest.fixture()
def redis_config():
    return {
        "cache": "redis",
    }
