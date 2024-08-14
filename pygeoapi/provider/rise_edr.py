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

import logging
from typing import ClassVar, Optional
import requests

from pygeoapi.provider.base import (
    ProviderNoDataError,
    ProviderQueryError,
)
from pygeoapi.provider.base_edr import BaseEDRProvider
from pygeoapi.provider.rise_edr_helpers import (
    RISECache,
    get_only_key,
    merge_pages,
    LocationHelper,
)


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
        provider_def = {
            "name": "Rise EDR",
            "type": "feature",
            "data": "remote",
        }

        super().__init__(provider_def)

        self.instances = []

    @BaseEDRProvider.register()
    def locations(
        self,
        location_id: Optional[int] = None,
        datetime_: Optional[str] = None,
        select_properties: Optional[str] = None,
        crs: Optional[str] = None,
        format_: Optional[str] = None,
        **kwargs,
    ):
        """
        Extract data from location
        """
        LOGGER.error(f"{kwargs}")

        if location_id:
            # Instead of merging all location pages, just
            # fetch the location associated with the ID
            response = requests.get(
                RiseEDRProvider.LOCATION_API,
                headers={"accept": "application/vnd.api+json"},
                params={"id": location_id},
            )

            if not response.ok:
                raise ProviderQueryError(response.text)
            else:
                response = response.json()
        else:
            response = RISECache.get_or_fetch_all_pages(RiseEDRProvider.LOCATION_API)
            response = merge_pages(response)
            response = get_only_key(response)
            if response is None:
                raise ProviderNoDataError

        if datetime_:
            response = LocationHelper.filter_by_date(response, datetime_)

        # location 1 has parameter 1721
        if select_properties:
            response = LocationHelper.filter_by_properties(response, select_properties)

        base = (
            not crs
            and not format_
            and not select_properties
            and not datetime_
            and not location_id
        )

        if format_ == "geojson" or format_ == "json" or not base:
            return LocationHelper.to_geojson(response)
        else:
            return LocationHelper.to_covjson(response)

    def get_fields(self):
        if self._fields:
            return self._fields

        self._fields = RISECache.get_fields()

        return self._fields

    @BaseEDRProvider.register()
    def cube(
        self,
        bbox: list,
        datetime_: Optional[str] = None,
        select_properties: Optional[list] = None,
        z: Optional[str] = None,
        format_: Optional[str] = None,
        **kwargs,
    ):
        """
        Returns a data cube defined by bbox and z parameters

        :param bbox: `list` of minx,miny,maxx,maxy coordinate values as `float`
        :param datetime_: temporal (datestamp or extent)
        :param z: vertical level(s)
        :param format_: data format of output

        """
        response = RISECache.get_or_fetch_all_pages(RiseEDRProvider.LOCATION_API)
        response = merge_pages(response)
        response = get_only_key(response)
        if response is None:
            raise ProviderNoDataError

        if select_properties:
            response = LocationHelper.filter_by_properties(response, select_properties)

        if datetime_:
            response = LocationHelper.filter_by_date(response, datetime_)

        response = LocationHelper.filter_by_bbox(response, bbox, z)

        match format_:
            case "json" | "GeoJSON" | _:
                return LocationHelper.to_geojson(response)

    @BaseEDRProvider.register()
    def area(
        self,
        wkt: str,
        select_properties: list[str] = [],
        datetime_: Optional[str] = None,
        z: Optional[str] = None,
        format_: Optional[str] = None,
        **kwargs,
    ):
        """
        Extract and return coverage data from a specified area.

        :param wkt: Well-Known Text (WKT) representation of the
                    geometry for the area.
        :param select_properties: List of properties to include
                                  in the response.
        :param datetime_: Temporal filter for observations.

        :returns: A CovJSON CoverageCollection.
        """

        response = RISECache.get_or_fetch_all_pages(RiseEDRProvider.LOCATION_API)
        response = merge_pages(response)
        response = get_only_key(response)
        if response is None:
            raise ProviderNoDataError

        if select_properties:
            response = LocationHelper.filter_by_properties(response, select_properties)

        if datetime_:
            response = LocationHelper.filter_by_date(response, datetime_)

        response = LocationHelper.filter_by_wkt(response, wkt, z)

        match format_:
            case "json" | "GeoJSON" | "" | None:
                return LocationHelper.to_geojson(response)
            case "covjson":
                return LocationHelper.to_covjson(response)

    @BaseEDRProvider.register()
    def items(self, **kwargs):
        """
        Retrieve a collection of items.

        :param kwargs: Additional parameters for the request.
        :returns: A GeoJSON representation of the items.
        """
        # https://github.com/geopython/pygeoapi/issues/1748
        pass

    def __repr__(self):
        return "<RiseEDRProvider>"
