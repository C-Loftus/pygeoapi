# =================================================================
#
# Authors: Tom Kralidis <tomkralidis@gmail.com>
#
# Copyright (c) 2021 Tom Kralidis
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

import pytest
import geopandas as gpd
import shapely

from pygeoapi.provider.base import ProviderItemNotFoundError
from pygeoapi.provider.geopandas_provider import GeoPandasProvider

from .util import get_test_file_path

path = get_test_file_path('data/obs.csv')
stations_path = get_test_file_path('data/station_list.csv')


@pytest.fixture()
def config():
    return {
        'name': 'CSV',
        'type': 'feature',
        'data': path,
        'id_field': 'id',
        'geometry': {
            'x_field': 'long',
            'y_field': 'lat'
        }
    }


def test_csv_query(config):
    p = GeoPandasProvider(config)

    fields = p.get_fields()
    assert len(fields) == 4
    assert ['id', 'stn_id', 'datetime', 'value'] == list(fields.keys())
    assert fields['value']['type'] == 'number'
    assert fields['stn_id']['type'] == 'integer'

    results = p.query()
    assert len(results['features']) == 5
    assert results['numberMatched'] == 5
    assert results['numberReturned'] == 5
    assert results['features'][0]['id'] == '371'
    assert results['features'][0]['properties']['value'] == 89.9

    assert results['features'][0]['geometry']['coordinates'][0] == -75.0
    assert results['features'][0]['geometry']['coordinates'][1] == 45.0

    results = p.query(limit=1)
    assert len(results['features']) == 1
    assert results['features'][0]['id'] == '371'

    results = p.query(offset=2, limit=1)
    assert len(results['features']) == 1
    assert results['features'][0]['id'] == '238'
    # should just be stn_id, datetime and value
    assert len(results['features'][0]['properties']) == 3

    results = p.query(select_properties=['value'])
    assert len(results['features'][0]['properties']) == 1

    results = p.query(select_properties=['value', 'stn_id'])
    assert len(results['features'][0]['properties']) == 2

    results = p.query(skip_geometry=True)
    assert results['features'][0]['geometry'] is None

    results = p.query(properties=[('stn_id', '604')])
    assert len(results['features']) == 1
    assert results['numberMatched'] == 1
    assert results['numberReturned'] == 1

    results = p.query(properties=[('stn_id', '35')])
    assert len(results['features']) == 2
    assert results['numberMatched'] == 2
    assert results['numberReturned'] == 2

    results = p.query(properties=[('stn_id', '35'), ('value', '93.9')])
    assert len(results['features']) == 1

    config['properties'] = ['value', 'stn_id']
    p = GeoPandasProvider(config)
    results = p.query()
    assert len(results['features'][0]['properties']) == 2


def test_csv_get(config):
    p = GeoPandasProvider(config)

    result = p.get('964')
    assert result['id'] == '964'
    assert result['properties']['value'] == 99.9


def test_csv_get_not_existing_item_raise_exception(config):
    """Testing query for a not existing object"""
    p = GeoPandasProvider(config)
    with pytest.raises(ProviderItemNotFoundError):
        p.get('404')


@pytest.fixture()
def station_config():
    return {
        'name': 'CSV',
        'type': 'feature',
        'data': stations_path,
        'id_field': 'wigos_station_identifier',
        'geometry': {
            'x_field': 'longitude',
            'y_field': 'latitude'
        }
    }

def test_csv_get_station(station_config):
    p = GeoPandasProvider(station_config)

    results = p.query(limit=20)
    assert len(results['features']) == 20
    assert results['numberMatched'] == 79
    assert results['numberReturned'] == 20

    result = p.get('0-20000-0-16337')
    assert result['properties']['station_name'] == 'BONIFATI (16337-0)'

    result = p.get('0-454-2-AWSNAMITAMBO')
    assert result['properties']['station_name'] == 'NAMITAMBO'

hu02_path = get_test_file_path('data/hu02.gpkg')

@pytest.fixture()
def gpkg_config():
    return {
        'name': 'gpkg',
        'type': 'feature',
        'data': hu02_path,
        'id_field': 'HUC2',
    }

def test_intersection():
    gdf = gpd.read_file(hu02_path)
    gdf = gdf[gdf['HUC2'] == '01']
    
    minx, miny, maxx, maxy =  -73.0, 40.0, -71.0, 42.0
    polygon = shapely.geometry.Polygon([(minx, miny), (minx, maxy), (maxx, maxy), (maxx, miny)])
    huc_range : shapely.geometry.MultiPolygon = gdf["geometry"].iloc[0]

    assert isinstance(huc_range, shapely.geometry.MultiPolygon)
    assert isinstance(polygon, shapely.geometry.Polygon)
    assert shapely.intersects(polygon, huc_range) == True

def test_gpkg_query(gpkg_config):
    p = GeoPandasProvider(gpkg_config)

    results = p.query(limit=1)
    assert len(results['features']) == 1

    results = p.query(offset=1, limit=1)
    assert len(results['features']) == 1

    results = p.query(skip_geometry=True)
    assert results['features'][0]['geometry'] is None

    results = p.query(properties=[('uri', 'https://geoconnex.us/ref/hu02/07')])
    assert len(results['features']) == 1
    assert results['features'][0]['properties']['uri'] == 'https://geoconnex.us/ref/hu02/07'

    results = p.query(bbox=(0, 0, 0, 0), properties=[('uri', 'https://geoconnex.us/ref/hu02/07')])
    assert len(results['features']) == 0

    results = p.query(bbox=(-180, -90, -180, 90))
    assert len(results['features']) == 1


