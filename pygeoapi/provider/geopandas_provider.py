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
import json
import logging
from typing import Literal, Optional
from enum import Enum
from http import HTTPStatus

from pygeoapi.error import GenericError
from pygeoapi.provider.base import BaseProvider, ProviderQueryError, SchemaType
from pygeoapi.util import get_typed_value

LOGGER = logging.getLogger(__name__)


class GeoPandasProvider(BaseProvider):
    """GeoPandas provider"""

    _data: Optional[geopandas.GeoDataFrame] = None

    def __init__(self, provider_def):
        """
        Initialize object

        :param provider_def: provider definition

        :returns: pygeoapi.provider.base.GeoPandasProvider
        """
        super().__init__(provider_def)
        self.geometry_x = provider_def['geometry']['x_field']
        self.geometry_y = provider_def['geometry']['y_field']
        self._data = geopandas.GeoDataFrame(provider_def['data'])
        self.fields = self.get_fields()
        
    def get_fields(self):
        """
        Get provider field information (names, types)

        Example response: {'field1': 'string', 'field2': 'number'}}

        :returns: dict of field names and their associated JSON Schema types
        """
        if not self._data:
            raise ValueError('Data not loaded')

        return {col: self._data[col].dtype for col in self._data.columns }

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
            identifier=None, bbox=[], datetime_=None, properties=[],
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

        found = False
        result = None
        feature_collection: dict[str, str | list | int] = {
            'type': 'FeatureCollection',
            'features': [],
            "numberMatched": 0,
            "numberReturned": 0
        }

        if identifier is not None:
            # If we are querying for just one feature, we may have a different limit than the default
            # TODO should this be min? So min or this limit and limit in the function call?
            limit = self.query(resulttype='hits').get('numberMatched')

        # Create a dummy backup that we can overwrite
        df: geopandas.GeoDataFrame = self._data

        if properties:
            for prop in properties:
                # Only keep rows where the property is the right value
                df = df[df[prop[0]] == prop[1]]

        if resulttype == 'hits':
            # If we are querying for just the number matched, we don't
            # need to further process the df and can simply return len
            feature_collection['numberMatched'] = len(df)
            return feature_collection

        for _, row in df.iterrows():
            try:
                coordinates = [
                    float(row[self.geometry_x]),
                    float(row[self.geometry_y]),
                ]
            except ValueError:
                msg = f'Skipping row with invalid geometry: {row[self.id_field]}'
                LOGGER.error(msg)
                continue

            feature = {'type': 'Feature', 'id': row[self.id_field]}

            if skip_geometry:
                feature['geometry'] = None
            else:
                feature['geometry'] = {
                    'type': 'Point',
                    'coordinates': coordinates
                }

            feature['properties'] = OrderedDict()

            #  TODO ASK little confused why we are filtering on self.properties not the properties passed in
            if all_properties := set(self.properties).union(set(select_properties)):
                for p in all_properties:
                    try:
                        feature['properties'][p] = row[p]
                    except KeyError as err:
                        LOGGER.error(err)
                        raise ProviderQueryError()
            else:
                for key, value in row.items():
                    LOGGER.debug(f'key: {key}, value: {value}')
                    feature['properties'][key] = value

            if identifier and feature['id'] == identifier:
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

        return self._data[self._data['id'] == identifier]


    def create(self, item):
        """
        Create a new item

        :param item: `dict` of new item

        :returns: identifier of created item
        """

        self._data = self._data.append(item, ignore_index=True)

        return self._data["id"].iloc[-1]


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
            self._data = self._data[self._data['id'] != identifier]
            return True
        except Exception as e:
            LOGGER.error(e)
            return False

    def __repr__(self):
        return f'<GeoPandasProvider> {self.type}'
