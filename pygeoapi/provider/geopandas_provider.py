# =================================================================
#
# Authors: Tom Kralidis <tomkralidis@gmail.com>
#
# Copyright (c) 2022 Tom Kralidis
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

from collections import OrderedDict
import geopandas
from shapely import intersects
import shapely.geometry as geo
import json
import logging
from typing import Literal, Optional
from enum import Enum
from http import HTTPStatus

from pygeoapi.error import GenericError
from pygeoapi.provider.base import BaseProvider, ProviderItemNotFoundError, ProviderQueryError, SchemaType
from pygeoapi.util import get_typed_value

LOGGER = logging.getLogger(__name__)


from typing import TypedDict
from collections import defaultdict

class Feature(TypedDict):
    type: Literal['Feature']
    geometry: dict
    properties: dict

PossibleGeometries = geo.LineString | geo.multilinestring.MultiLineString | geo.multipoint.MultiPoint | geo.multipolygon.MultiPolygon | geo.point.Point | geo.polygon.LinearRing | geo.polygon.Polygon

class GeoPandasProvider(BaseProvider):
    """GeoPandas provider"""

    _data: Optional[geopandas.GeoDataFrame] = None

    def __init__(self, provider_def: dict):
        """
        Initialize object

        :param provider_def: provider definition

        :returns: pygeoapi.provider.base.GeoPandasProvider
        """

        super().__init__(provider_def)
        self._data = geopandas.read_file(provider_def['data'])
             
        # These fields should not be returned in the property list for a query
        self._exclude_from_fields: list[str] = []

        # Check if it was specified in the config
        if "geometry" in provider_def:
            if provider_def["geometry"]["x_field"] and provider_def["geometry"]["y_field"]:
                self.geometry_x = provider_def['geometry']['x_field']
                self.geometry_y = provider_def['geometry']['y_field']
                self._exclude_from_fields.append(self.geometry_x)
                self._exclude_from_fields.append(self.geometry_y)

        # If we don't have x,y coords as separate columns then look for a geometry column
        elif "geometry" in self._data.columns:
            self.geometry_col = "geometry"
            self._exclude_from_fields.append(self.geometry_col)
            
        # If we don't have any of the above, find the first geometry column and assume that is where the geometry is 
        else:
            for col in self._data.columns:
                if hasattr(col, "geom_type"):
                    self.geometry_col = col
                    self._exclude_from_fields.append(self.geometry_col)
                    break
            else:
                raise ValueError("Could not find geometry column")

        self._data[self.id_field] = self._data[self.id_field].astype(str)
        
        if "stn_id" in self._data.columns:
            self._data["stn_id"] = self._data["stn_id"].astype('int64')
        if "value" in self._data.columns:
            self._data["value"] = self._data["value"].astype('float64')

        self._exclude_from_properties: list[str] = self._exclude_from_fields + [self.id_field]

        self.fields = self.get_fields()

        
    def get_fields(self) -> dict[str, any]:
        """
        Get provider field information (names, types)

        Example response: {'field1': 'string', 'field2': 'number'}}

        :returns: dict of field names and their associated JSON Schema types
        """
        if len(self._data) == 0:
            raise ValueError('Data not loaded')
        

        field_mapper =  {col: self._data[col].dtype.name for col in self._data.columns 
                         if col not in self._exclude_from_fields
                         }
        
       # Pandas has a different ãmes for types than the pygeoapi spec expects
        pandas_dtypes_to_ours = {
            'float64': 'number',
            'int64': 'integer',
            'object': 'string'
        }

        pandas_default = defaultdict(lambda: 'string')
        pandas_default.update(pandas_dtypes_to_ours)

        
        our_types_names = {k: {
            "type": pandas_default[v]
            }
        for k, v in field_mapper.items()
        }

        return our_types_names

    # def get_schema(self, schema_type: SchemaType = SchemaType.item):
    #     """
    #     Get provider schema model

    #     :param schema_type: `SchemaType` of schema (default is 'item')

    #     :returns: tuple pair of `str` of media type and `dict` of schema
    #               (i.e. JSON Schema)
    #     """
        

    # def get_data_path(self, baseurl, urlpath, dirpath):
    #     """
    #     Gets directory listing or file description or raw file dump

    #     :param baseurl: base URL of endpoint
    #     :param urlpath: base path of URL
    #     :param dirpath: directory basepath (equivalent of URL)

    #     :returns: `dict` of file listing or `dict` of GeoJSON item or raw file
    #     """



    # def get_metadata(self):
    #     """
    #     Provide data/file metadata

    #     :returns: `dict` of metadata construct (format
    #               determined by provider/standard)
    #     """

    #     raise NotImplementedError()

    # we want to support bbox and datetime_
    def query(self, offset=0, limit=10, resulttype: Literal['results', 'hits']='results',
            identifier=None, bbox: list[float] =[], datetime_=None, properties: list[tuple[str, str]] = [],
            select_properties=[], skip_geometry=False, q=None):
        """
        Query data with GeoPandas

        :param offset: starting record to return (default 0)
        :param limit: number of records to return (default 10)
        :param datetime_: temporal (datestamp or extent)
        :param identifier: feature id
        :param resulttype: return results or hit limit (default results)
        :param properties: Properties with specific values to select list of tuples (name, value)
        :param select_properties: list of general properties to select regardless of values
        :param skip_geometry: bool of whether to skip geometry (default False)
        :param q: full-text search term(s)

        :returns: dict of GeoJSON FeatureCollection
        """

        found, result = False, False
        feature_collection: dict[str, str | list | int] = {
            'type': 'FeatureCollection',
            'features': [],
            "numberMatched": 0,
            "numberReturned": 0
        }

        if identifier is not None:
            # If we are querying for just one feature, we may have a different limit than the default
            # TODO should this be min? So min or this limit and limit in the function call?
            limit = self.query(resulttype='hits')['numberMatched']

        # Create a dummy backup that we can overwrite
        df: geopandas.GeoDataFrame = self._data

        if properties:
            for prop in properties:
                # Only keep rows where the property is the right value
                (column_name, val_to_filter_by) = prop

                # We need to convert this to a string since it appears the properties are always strings,
                # but our dataframe contains integers or floats
                df = df[df[column_name].astype(str) == val_to_filter_by]

        if resulttype == 'hits':
            # If we are querying for just the number matched, we don't
            # need to further process the df and can simply return len
            feature_collection['numberMatched'] = len(df)
            return feature_collection
        

        for _, row in df.iterrows():

            if hasattr(self, 'geometry_x') and hasattr(self, 'geometry_y'):
                coordinates = list(map(float, [row[self.geometry_x], row[self.geometry_y]]))
            elif hasattr(self, 'geometry_col'):
                coordinates: list[PossibleGeometries] = row[self.geometry_col]

            feature = {'type': 'Feature', 'id': str(row[self.id_field])}

            if skip_geometry:
                feature['geometry'] = None
            else:
                feature['geometry'] = {
                    'type': 'Point',
                    'coordinates': coordinates
                }
            
            feature['properties'] = OrderedDict()

            for key, value in row.items():
                properties_to_keep = set(self.properties).union(set(select_properties))
                KEEP_ALL = len(properties_to_keep) == 0

                if KEEP_ALL or key in properties_to_keep:
                    feature['properties'][key] = value

            if bbox:
                if not feature[self.geometry_col]:
                    continue
                minx, miny, maxx, maxy = bbox
                polygon = [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy), (minx, miny)]
                if not intersects(feature[self.geometry_col]["coordinates"], geo.Polygon(polygon)):
                    continue


            # After filtering out specific properties, filter out 
            # geometry and id which are never included
            feature['properties'] = {k: v for k, v in feature['properties'].items() if k not in self._exclude_from_properties}

            if identifier and feature[self.id_field] == identifier:
                found = True
                result = feature

            feature_collection['features'].append(feature)
            feature_collection['numberMatched'] = len(feature_collection['features'])
        
        if identifier:
            return None if not found else result

        feature_collection['features'] = feature_collection['features'][offset:offset + limit]
        feature_collection['numberReturned'] = len(feature_collection['features'])

        return feature_collection


    def get(self, identifier, **kwargs):
        """
        query the provider by id

        :param identifier: feature id

        :returns: dict of single GeoJSON feature
        """
        res: geopandas.GeoSeries = self._data[self._data[self.id_field].astype(str) == identifier].squeeze(axis=0)
        if res.empty:
            err = f'item {identifier} not found'
            LOGGER.error(err)
            raise ProviderItemNotFoundError(err)

        feature: Feature = {}
        feature['type'] = 'Feature'
        feature['id'] = res[self.id_field]
        feature["properties"] = {
          k: v for k, v in res.items()
        }
        return feature



    def create(self, item):
        """
        Create a new item

        :param item: `dict` of new item

        :returns: identifier of created item
        """

        self._data = self._data.append(item, ignore_index=True)

        return self._data[self.id_field].iloc[-1]


    def update(self, identifier, item: dict[str, any]):
        """
        Updates an existing item

        :param identifier: feature id
        :param item: `dict` of partial or full item

        :returns: `bool` of update result
        """

        if not self._data:
            LOGGER.error("Tried to update a GeoPandasProvider without the dataframe loaded")
            return False

        if identifier not in self._data.index:
            return False 

        for key, value in item.items():
            self._data.at[identifier, key] = value

        return True 

    
    def delete(self, identifier):
        """
        Deletes an existing item

        :param identifier: item id

        :returns: `bool` of deletion result
        """
        try:
            self._data = self._data[self._data[self.id_field] != identifier]
            return True
        except Exception as e:
            LOGGER.error(e)
            return False

    def __repr__(self):
        return f'<GeoPandasProvider> {self.type}'
