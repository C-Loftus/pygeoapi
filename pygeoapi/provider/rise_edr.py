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
from typing import ClassVar
import json
import requests

from pygeoapi.provider.base import ProviderQueryError
from pygeoapi.provider.base_edr import BaseEDRProvider
from pygeoapi.provider.rise_api_types import LocationQueryOptions, RiseLocationResponse


LOGGER = logging.getLogger(__name__)


class RiseEDRProvider(BaseEDRProvider):
    """Base EDR Provider"""

    LOCATION_API: ClassVar[str] = "https://data.usbr.gov/rise/api/location"
    BASE_API: ClassVar[str] = "https://data.usbr.gov"

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

    
     
    # def _filter_by_location():


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
        queryOptions: LocationQueryOptions = {}

        if kwargs.get("locationId"):
            # If we know the id befor
            queryOptions["id"] = kwargs.get("locationId")
        if kwargs.get("crs"):
            queryOptions["crs"] = kwargs.get("crs")

        response = requests.get(
            RiseEDRProvider.LOCATION_API, headers={"accept": "application/vnd.api+json"}, params=queryOptions
        )

        if not response.ok:
            raise ProviderQueryError
        else:
            # get it into standard json format temporarily so we can filter the same way regardless of final out format
            response: RiseLocationResponse = response.json() 

        if parametersToQueryBy := kwargs.get("parameterName"):
            params = self._get_parameters_from_location(response)

            for name in parametersToQueryBy:
                if name not in params:
                    response = None

        if kwargs.get("datetime"):
            tmp_req = self._filter_by_date(response, kwargs.get("datetime"))

        match kwargs.get("f"):
            case "json" | _:
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
            return getattr(self, kwargs.get("query_type"))(**kwargs)
        except AttributeError:
            raise NotImplementedError("Query not implemented!")
