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

import datetime
import json

import pytest
from pytest import param
import requests
import shapely

from pygeoapi.provider.base import ProviderItemNotFoundError

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
    out = p.location(locationId=6902)
    assert out["links"]["self"] == "/rise/api/location?id=6902"
    assert len(out["data"]) == 1
    out = p.location(locationId=1)
    assert out["links"]["self"] == "/rise/api/location?id=1"
    assert len(out["data"]) == 1


def test_location_parameterName(config):
    p = RiseEDRProvider(config)
    out = p.location(parameterName="DUMMY-PARAM")
    assert len(out["data"]) == 0

    out = p.location(parameterName="Streamflow")
    assert out["data"][0]["id"] == "/rise/api/location/3658"


def test_location_datetime(config):
    p = RiseEDRProvider(config)
    out = p.location(datetime="2024-03-29T15:49:57+00:00")
    assert out["data"][0]["id"] == "/rise/api/location/6902"


def test_item():
    pass


def test_area():
    pass


def test_cube():
    pass
