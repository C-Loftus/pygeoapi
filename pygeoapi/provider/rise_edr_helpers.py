import datetime
import json
import logging
from typing import ClassVar, Protocol

from h11 import Data
from pygeoapi.provider.base import ProviderQueryError
import asyncio
import aiohttp
from pygeoapi.provider.rise_api_types import RiseLocationResponse
import shelve

LOGGER = logging.getLogger(__name__)


async def fetch_url(url: str) -> dict:
    headers = {"accept": "application/vnd.api+json"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, headers=headers) as response:
            return await response.json()


async def fetch_url_group(
    urls: list[str],
) -> dict[str, dict | Exception]:
    tasks = [asyncio.create_task(fetch_url(url)) for url in urls]

    results: dict[str, dict | Exception] = {url: {} for url in urls}

    for coroutine, url in zip(asyncio.as_completed(tasks), urls):
        result = await coroutine
        results[url] = result
        RISECache.set(url, result)

    return results


class RISECache(Protocol):
    db: ClassVar[str] = "tests/data/risedb"

    @staticmethod
    async def get_or_fetch(url, force_fetch=False) -> dict:
        """Send a get request or grab it locally if it already exists in the cache"""

        with shelve.open(RISECache.db) as db:
            if url in db and not force_fetch:
                return db[url]
            else:
                res = await fetch_url(url)
                db[url] = res
                return res

    @staticmethod
    async def get_or_fetch_group(
        urls: list[str], force_fetch=False
    ) -> dict[str, dict | Exception]:
        """Send a get request to all urls or grab it locally if it already exists in the cache"""

        with shelve.open(RISECache.db) as db:
            urls_not_in_cache = [url for url in urls if url not in db or force_fetch]
            urls_in_cache = [url for url in urls if url in db and not force_fetch]

            remote_fetch = fetch_url_group(urls_not_in_cache)

            local_fetch = {url: db[url] for url in urls_in_cache}

            local_fetch.update(await remote_fetch)

            return local_fetch

    @staticmethod
    def set(url: str, data):
        with shelve.open(RISECache.db, "w") as db:
            db[url] = data

    @staticmethod
    def reset():
        with shelve.open(RISECache.db, "w") as db:
            for key in db:
                del db[key]

    @staticmethod
    def clear(url: str):
        with shelve.open(RISECache.db, "w") as db:
            if url not in db:
                return

            del db[url]

    @staticmethod
    def contains(url: str) -> bool:
        with shelve.open(RISECache.db) as db:
            return url in db


def flatten_values(input: dict[str, list[str]]) -> list[str]:
    output = []
    for _, v in input.items():
        for i in v:
            output.append(i)

    return output


class LocationHelper:
    @staticmethod
    def get_catalogItems(
        location_response: dict,
    ) -> dict[str, list[str]]:
        lookup: dict[str, list[str]] = {}
        if not isinstance(location_response["data"], list):
            location_response["data"] = [location_response["data"]]

        for loc in location_response["data"]:
            id: str = loc["id"]
            locationNumber = id.removeprefix("/rise/api/location/")
            items = []

            for catalogItem in loc["relationships"]["catalogItems"]["data"]:
                items.append("https://data.usbr.gov" + catalogItem["id"])

            lookup[locationNumber] = items

        return lookup

    @staticmethod
    def get_parameters(
        allLocations: dict,
    ) -> dict[str, list[str | None]]:
        locationsToCatalogItems = LocationHelper.get_catalogItems(allLocations)

        locationToParams: dict[str, list[str | None]] = {}

        for location, catalogItems in locationsToCatalogItems.items():
            urlItemMapper = asyncio.run(RISECache.get_or_fetch_group(catalogItems))

            try:
                allParams = [
                    CatalogItem.get_parameter(item)  # type: ignore seems to be an error with pylance
                    for item in urlItemMapper.values()
                ]
            except KeyError:
                with open("tests/data/rise/debug.json", "w") as f:
                    json.dump(urlItemMapper, f)
                raise ProviderQueryError("Could not get parameters")

            allParams = list(filter(lambda x: x is not None, allParams))

            locationToParams[location] = allParams

        # should have the same number of locations in each
        assert len(locationToParams) == len(locationsToCatalogItems)
        return locationToParams

    @staticmethod
    def drop_location(json_with_multiple_locations: dict, location_id: int) -> dict:
        allLocations: list[dict] = json_with_multiple_locations["data"]

        allLocations = [
            loc for loc in allLocations if loc["attributes"]["_id"] != location_id
        ]

        new = json_with_multiple_locations.copy()
        new.update({"data": allLocations})

        return new

    @staticmethod
    def filter_by_date(location_response: dict, datetime_: str) -> dict:
        """
        Filter by date
        """
        if not location_response["data"][0]["attributes"]:
            raise ProviderQueryError("Can't filter by date")

        filteredResp = location_response.copy()

        dateRange = datetime_.split("/")

        if len(dateRange) == 2:  # noqa F841
            start, end = dateRange

            # python does not accept Z at the end of the datetime even though that is a valid ISO 8601 datetime
            if start.endswith("Z"):
                start = start.replace("Z", "+00:00")

            if end.endswith("Z"):
                end = end.replace("Z", "+00:00")

            start = (
                datetime.datetime.min
                if start == ".."
                else datetime.datetime.fromisoformat(start)
            )
            end = (
                datetime.datetime.max
                if end == ".."
                else datetime.datetime.fromisoformat(end)
            )
            start, end = (
                start.replace(tzinfo=datetime.timezone.utc),
                end.replace(tzinfo=datetime.timezone.utc),
            )

            if start > end:
                raise ProviderQueryError(
                    "Start date must be before end date but got {} and {}".format(
                        start, end
                    )
                )

            for i, location in enumerate(filteredResp["data"]):
                updateDate = datetime.datetime.fromisoformat(
                    location["attributes"]["updateDate"]
                )
                if updateDate < start or updateDate > end:
                    filteredResp["data"].pop(i)

        elif len(dateRange) == 1:  # noqa
            # By casting to a string we can use .str.contains to coarsely check.
            # We want 2019-10 to match 2019-10-01, 2019-10-02, etc.

            for i, location in enumerate(filteredResp["data"]):
                if not str(location["attributes"]["updateDate"]).startswith(
                    dateRange[0]
                ):
                    filteredResp["data"].pop(i)

        else:
            raise ProviderQueryError(
                "datetime_ must be a date or date range with two dates separated by '/' but got {}".format(
                    datetime_
                )
            )

        return filteredResp


class CatalogItem:
    @classmethod
    def get_parameter(cls, data: dict) -> str | None:
        parameterName = (
            data["data"]["attributes"]["parameterName"]
            if data["data"]["attributes"]["parameterName"] != "null"
            else None
        )
   
        return parameterName
