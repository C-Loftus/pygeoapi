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
import requests

from pygeoapi.provider.base import ProviderGenericError, ProviderQueryError
from pygeoapi.provider.base_edr import BaseEDRProvider
from pygeoapi.provider.rise_edr_helpers import LocationHelper


LOGGER = logging.getLogger(__name__)


class RiseEDRProvider(BaseEDRProvider):
    """Base EDR Provider"""

    LOCATION_API: ClassVar[str] = "https://data.usbr.gov/rise/api/location"
    BASE_API: ClassVar[str] = "https://data.usbr.gov"

    def __init__(self, provider_def):
        """
        Initialize object

        :param provider_def: provider definition

        :returns: pygeoapi.provider.base_edr.RiseEDRProvider
        """

        super().__init__(provider_def)

        self.instances = []

    @BaseEDRProvider.register()
    def locations(self, **kwargs):
        """
        Extract data from location

        :param locationId: location id in RISE
        :param datetime : temporal (datestamp or extent)
        :param parameter-name : parameter name
        :param crs : coordinate reference system string
        :f data format for output

        :returns: coverage data as specified format
        """
        queryOptions = {}

        if kwargs.get("location_id"):
            # If we know the id befor
            queryOptions["id"] = kwargs.get("location_id")
        if kwargs.get("crs"):
            queryOptions["crs"] = kwargs.get("crs")

        response = requests.get(
            RiseEDRProvider.LOCATION_API,
            headers={"accept": "application/vnd.api+json"},
            params=queryOptions,
        )

        if not response.ok:
            raise ProviderQueryError(response.text)
        else:
            response = response.json()

        if kwargs.get("datetime_"):
            query_date: str = kwargs.get("datetime_")
            response = LocationHelper.filter_by_date(response, query_date)

        parametersToQueryBy = kwargs.get("select_properties")
        LOGGER.error(f"{kwargs}")

        # location 1 has parameter 1721

        if parametersToQueryBy:
            locationsToParams = LocationHelper.get_parameters(response)
            for param in parametersToQueryBy:
                for location, paramList in locationsToParams.items():
                    if param not in paramList:
                        print(f"dropping {location}")
                        response = LocationHelper.drop_location(response, int(location))
                        print(len(response["data"]))

        match kwargs.get("format_"):
            case "json" | _:
                features = []

                for location_feature in response["data"]:
                    feature_as_covjson = {
                        "type": "Feature",
                        "id": location_feature["attributes"]["_id"],
                        "properties": {
                            "Locations@iot.count": 1,
                            "Locations": [
                                {
                                    "location": location_feature["attributes"][
                                        "locationCoordinates"
                                    ]
                                }
                            ],
                        },
                        "geometry": location_feature["attributes"][
                            "locationCoordinates"
                        ],
                    }
                    features.append(feature_as_covjson)

                return {"type": "FeatureCollection", "features": features}

    def get_fields(self):
        if self._fields:
            return self._fields

        res = requests.get(
            "https://data.usbr.gov/rise/api/parameter?id=18",
            headers={"accept": "application/vnd.api+json"},
        )

        self._fields: dict = {}

        if not res.ok:
            raise ProviderGenericError(res.text)

        for item in res.json()["data"]:
            param = item["attributes"]
            # TODO check if this should be a string or a number
            self._fields[str(param["_id"])] = {
                "type": param["parameterUnit"],
                "title": param["parameterName"],
                "x-ogc-unit": param["parameterUnit"],
            }

        return self._fields

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

    def __repr__(self):
        return "<RiseEDRProvider>"
