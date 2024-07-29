# =================================================================
#
# Authors: Colton Loftus
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
import logging
import json
import requests

from pygeoapi.provider.base import ProviderQueryError
from pygeoapi.provider.base_edr import BaseEDRProvider
from typing import Literal, TypedDict

class EDRQuery(TypedDict):
    data_queries: list[dict]


class EDRResponse(TypedDict):
    type: Literal["FeatureCollection"]
    features: list[
        dict[
            Literal["type"]: Literal["Feature"],
            Literal['id']: str,
            Literal['properties']: dict
        ],
        Literal['geometry']: dict
    ]


LOGGER = logging.getLogger(__name__)


# We need to cache the natural language name of the parameter from the id so we 
# don't need to query the API each time
class ParameterCache():

    def __init__(self):
        self.cache = {}

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        else:
            return None

    def set(self, key, value):
        self.cache[key] = value


class RiseEDRProvider(BaseEDRProvider):
    """Base EDR Provider"""

    API = "https://data.usbr.gov/rise/api/"


    query_types = []

    def __init__(self, provider_def):
        """
        Initialize object

        :param provider_def: provider definition

        :returns: pygeoapi.provider.base_edr.RiseEDRProvider
        """

        super().__init__(provider_def)

        self.instances = []

    def _param_id_from_name(self, id):
        pass


    def _filter_by_date(
        self, data: dict, datetime_: str
    ) -> dict:
        """
        Filter by date
        """
        if not data['data'][0]["attributes"]["last"]:
            raise ProviderQueryError("Can't filter by date")



        dateRange = datetime_.split('/')

        if _START_AND_END := len(dateRange) == 2:  # noqa F841
            start, end = dateRange

            # python does not accept Z at the end of the datetime even though that is a valid ISO 8601 datetime
            if start.endswith('Z'):
                start = start.replace('Z', '+00:00')

            if end.endswith('Z'):
                end = end.replace('Z', '+00:00')

            start = (
                datetime.datetime.min
                if start == '..'
                else datetime.datetime.fromisoformat(start)
            )
            end = (
                datetime.datetime.max
                if end == '..'
                else datetime.datetime.fromisoformat(end)
            )
            start, end = (
                start.replace(tzinfo=datetime.timezone.utc),
                end.replace(tzinfo=datetime.timezone.utc),
            )

            if start > end:
                raise ProviderQueryError(
                    'Start date must be before end date but got {} and {}'.format(
                        start, end
                    )
                )

            return df[(df[self.time_field] >= start) & (df[self.time_field] <= end)]

        elif _ONLY_MATCH_ONE_DATE := len(dateRange) == 1:  # noqa
            dates: geopandas.GeoSeries = df[self.time_field]

            # By casting to a string we can use .str.contains to coarsely check.
            # We want 2019-10 to match 2019-10-01, 2019-10-02, etc.
            return df[dates.astype(str).str.startswith(datetime_)]
        else:
            raise ProviderQueryError(
                "datetime_ must be a date or date range with two dates separated by '/' but got {}".format(
                    datetime_
                )
            )


    def _get_parameters(self, catalogItems: list):
        params = set()
    
        for catalogItem in catalogItems['data']:
            # make a request for each catalog item
            req_url = f'{self.API}{catalogItem["id"].removeprefix("/rise/api/")}'
            tmp_req = requests.get(req_url, headers= {'accept': 'application/vnd.api+json'})
            params.add(tmp_req.json()['data']['attributes']['parameterName'])

        return params
    

    @BaseEDRProvider.register()
    def location(self, **kwargs):
        """
        Extract data from location

        :param locationId: location id in RISE
        :param datetime : temporal (datestamp or extent)
        :param parameter-name : parameter name
        :param crs : coordinate reference system string 
        :f data format for output 

        :returns: coverage data as specified format
        """
        url = self.API + "location"

        class QueryOptions(TypedDict):
            id: int
            parameterName: list[str]
            crs: str
            datetime: str

        queryOptions: QueryOptions = {}

        if kwargs.get('locationId'):
            queryOptions['id'] = kwargs.get('locationId')
        if kwargs.get('crs'):
            queryOptions['crs'] = kwargs.get('crs')


        response = requests.get(url, headers= {'accept': 'application/vnd.api+json'}, params=queryOptions)

        if not response.ok:
            raise ProviderQueryError
        else:
            # get it into standard json format temporarily so we can filter the same way regardless of final out format
            response = response.json()
        
        
        if queryParams := kwargs.get('parameterName'):
            params  = self._get_parameters(response["data"][0]["relationships"]["catalogItems"])

            # queryParams['parameterName'] = [ self._param_id_from_name(name) for name in allParams.split(",") ]
            for name in queryParams:
                if name not in params:
                    response = None

        if kwargs.get('datetime'):
            tmp_req = self._filter_by_date(response, kwargs.get('datetime'))


        match kwargs.get('f'):
            case 'json' | _:
                return response
        

    def get_query_types(self):
        """
        Provide supported query types

        :returns: `list` of EDR query types
        """

        return self.query_types

    def query(self, **kwargs):
        """
        Extract data from collection collection

        :param query_type: query type
        :param wkt: `shapely.geometry` WKT geometry
        :param datetime_: temporal (datestamp or extent)
        :param select_properties: list of parameters
        :param z: vertical level(s)
        :param format_: data format of output
        :param bbox: bbox geometry (for cube queries)
        :param within: distance (for radius querires)
        :param within_units: distance units (for radius querires)

        :returns: coverage data as `dict` of CoverageJSON or native format
        """

        try:
            return getattr(self, kwargs.get('query_type'))(**kwargs)
        except AttributeError:
            raise NotImplementedError('Query not implemented!')
