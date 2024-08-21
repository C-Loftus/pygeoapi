# =================================================================
#
# Authors: Gregory Petrochenkov <gpetrochenkov@usgs.gov>
# Authors: Tom Kralidis <tomkralidis@gmail.com>
#
# Copyright (c) 2020 Gregory Petrochenkov
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

import json
import logging
from typing import Optional

import requests

from pygeoapi.provider.base import BaseProvider, ProviderNoDataError, ProviderQueryError
from pygeoapi.provider.rise_api_types import LocationResponse
from pygeoapi.provider.rise_edr import RiseEDRProvider
from pygeoapi.provider.rise_edr_helpers import (
    LocationHelper,
    RISECache,
    get_only_key,
    merge_pages,
)

LOGGER = logging.getLogger(__name__)


class RiseProvider(BaseProvider):
    """Rise Provider"""

    def __init__(self, provider_def):
        """
        Initialize object
        :param provider_def: provider definition
        """

        super().__init__(provider_def)

    def items(
        self,
        bbox: list = [],
        datetime_: Optional[str] = None,
        limit: Optional[int] = None,
        itemId: Optional[str] = None,
        offset: Optional[int] = 0,
        **kwargs,
    ):
        if itemId:
            # Instead of merging all location pages, just
            # fetch the location associated with the ID
            single_endpoint_response = requests.get(
                RiseEDRProvider.LOCATION_API,
                headers={"accept": "application/vnd.api+json"},
                params={"id": itemId},
            )

            if not single_endpoint_response.ok:
                raise ProviderQueryError(single_endpoint_response.text)
            else:
                response: LocationResponse = single_endpoint_response.json()

        else:
            all_location_responses = RISECache.get_or_fetch_all_pages(
                RiseEDRProvider.LOCATION_API
            )
            merged_response = merge_pages(all_location_responses)
            response: LocationResponse = get_only_key(merged_response)
            if response is None:
                raise ProviderNoDataError

        if datetime_:
            response = LocationHelper.filter_by_date(response, datetime_)

        if offset:
            response = LocationHelper.remove_before_offset(response, offset)

        if limit:
            response = LocationHelper.filter_by_limit(response, limit)

        # Even though bbox is required, it can be an empty list. If it is empty just skip filtering
        if bbox:
            response = LocationHelper.filter_by_bbox(response, bbox)

        geojson = LocationHelper.to_geojson(response, single_feature=itemId is not None)

        return geojson

    def query(self, **kwargs):
        return self.items(**kwargs)

    def get(self, identifier, **kwargs):
        """
        query CSV id

        :param identifier: feature id

        :returns: dict of single GeoJSON feature
        """
        return self.items(itemId=identifier, bbox=[], **kwargs)

    def get_fields(self, **kwargs):
        return RISECache.get_parameters()
