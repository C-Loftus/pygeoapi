# =================================================================
#
# Authors: Colton Loftus
#
# Copyright (c) 2024 Colton Loftus
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

import requests
import pytest

from pygeoapi.provider.rise_edr import RiseEDRProvider


@pytest.fixture()
def config():
    return {
        "name": "gpkg",
        "type": "feature",
        "data": "tests/data/hu02.gpkg",
        "id_field": "HUC2",
    }


def test_location_locationId(config):
    p = RiseEDRProvider(config)
    out = p.locations(location_id=6902)
    assert len(out["features"]) == 1
    out = p.locations(location_id=1)
    assert len(out["features"]) == 1
    # invalid location should return nothing
    out = p.locations(location_id=1111111111111111)
    assert len(out["features"]) == 0


def test_get_fields(config):
    p = RiseEDRProvider(config)
    fields = p.get_fields()
    assert "DUMMY_PARAM" not in fields
    assert "18" in fields

    assert requests.get(
        "https://data.usbr.gov/rise/api/parameter?page=1&itemsPerPage=25",
        headers={"accept": "application/vnd.api+json"},
    ).json()["meta"]["totalItems"] == len(fields)


def test_location_select_properties(config):
    # Currently in pygeoapi we use select_properties as the
    # keyword argument. This is hold over from OAF it seems.

    p = RiseEDRProvider(config)

    out = p.locations(select_properties="DUMMY-PARAM")
    assert len(out["features"]) == 0

    out = p.locations(select_properties="18")
    assert len(out["features"]) > 0


def test_location_datetime(config):
    p = RiseEDRProvider(config)
    out = p.locations(datetime_="2024-03-29T15:49:57+00:00")
    for i in out["features"]:
        if i["id"] == 6902:
            break
    else:
        assert False

    out = p.locations(datetime="2024-03-29/..")
    for i in out["features"]:
        if i["id"] == 6902:
            break
    else:
        assert False


# def test_area():
#     p = RiseEDRProvider(config)

#     out = p.area()
#     assert len(out["features"]) > 0


def test_item():
    pass


def test_cube():
    pass
