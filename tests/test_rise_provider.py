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
import requests
import shapely

from pygeoapi.provider.base import ProviderItemNotFoundError

from pygeoapi.provider.rise_edr import RiseEDRProvider

@pytest.fixture()
def config():
    return {
        'name': 'gpkg',
        'type': 'feature',
        'data': 'tests/data/hu02.gpkg',
        'id_field': 'HUC2',
    }


def test_location_locationId(config):
    p = RiseEDRProvider(config)
    out = p.location(locationId=6902)
    assert out['links']['self'] == "/rise/api/location?id=6902"
    assert len(out['data']) == 1
    out = p.location(locationId=1)
    assert out['links']['self'] == "/rise/api/location?id=1"
    assert len(out['data']) == 1


def test_location_parameterName(config):
    p = RiseEDRProvider(config)
    out = p.location(parameterName='DUMMY-PARAM')
    assert out is None

    # Test to make sure we are returning the proper parameters for the location
    locationResponse = requests.get(RiseEDRProvider.API + "location/1", headers= {'accept': 'application/vnd.api+json'}).json()
    params = p._get_parameters_from_location(locationResponse)
    assert 'Lake/Reservoir Storage' in params

def test_location_datetime(config):
    pass

def test_item():
    pass

def test_area():
    pass

def test_cube():
    pass