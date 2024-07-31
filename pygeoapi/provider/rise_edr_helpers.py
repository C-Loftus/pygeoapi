from datetime import datetime
from typing import ClassVar, Protocol
from pygeoapi.provider.base import ProviderQueryError
import asyncio
import aiohttp
from .rise_api_types import RiseLocationDatapoint, RiseLocationResponse
from .rise_edr import RiseEDRProvider
import json
import shelve


async def fetch_url(url: str) -> dict:
    headers = {"accept": "application/vnd.api+json"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, headers=headers) as response:
            return await response.json()



async def fetch_url_group(urls: list[str]) -> list[dict]:
    result = []

    for await task in (*[fetch_url(url) for url in urls])


class RISECache(Protocol):
    db: ClassVar[shelve.Shelf] = "risedb"

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
    async def get_or_fetch_group(urls: list[str], force_fetch=False) -> list[dict]:
        """Send a get request or grab it locally if it already exists in the cache"""

        with shelve.open(RISECache.db) as db:
            urls_not_in_cache = [url for url in urls if url not in db or force_fetch]
            urls_in_cache = [url for url in urls if url in db and not force_fetch]

            remote_fetch = fetch_url_group(urls_not_in_cache)

            local_fetch = [db[url] for url in urls_in_cache]

            return local_fetch + await remote_fetch

    @staticmethod
    def reset():
        with shelve.open(RISECache.db, "w") as db:
            for key in db:
                del db[key]

    @staticmethod
    def clear(url: str):
        with shelve.open(RISECache.db, "w") as db:
            del db[url]


def flatten(input: dict[str, list[str]]) -> list[str]:
    output = []
    for k, v in input.items():
        for i in v:
            output.append(i)

    return output


def dumpToDisk(data):
    with open("tests/data/rise/testoutput.json", "w") as f:
        f.write(data)


class Location:
    @classmethod
    def get_catalogItems(
        cls, location_response: RiseLocationResponse
    ) -> dict[str, list[str]]:
        lookup: dict[str, list[str]] = {}
        if not isinstance(location_response["data"], list):
            location_response["data"] = [location_response["data"]]

        for loc in location_response["data"]:
            locationNumber = loc["id"].removeprefix("/rise/api/location/")
            items = []

            for catalogItem in loc["relationships"]["catalogItems"]["data"]:
                items.append(RiseEDRProvider.BASE_API + catalogItem["id"])

            lookup[locationNumber] = items

        return lookup

    @classmethod
    def get_parameters(cls, location_response: RiseLocationResponse) -> list[str]:
        catalogItems = Location.get_catalogItems(location_response)

        allItems = flatten(catalogItems)

        params = asyncio.run(RISECache.get_or_fetch_group(allItems))

        p = [CatalogItem.get_parameter(item) for item in params]
        return p


class CatalogItem:
    @classmethod
    def get_parameter(cls, data: dict) -> str:
        assert isinstance(data, dict), dumpToDisk(data)

        return (
            data["data"]["attributes"]["parameterName"]
            if data["data"]["attributes"]["parameterName"] != "null"
            else None
        )

    # def filter_by_date(self, location_response: dict, datetime_: str) -> dict:
    #     """
    #     Filter by date
    #     """
    #     if not data["data"][0]["attributes"]["last"]:
    #         raise ProviderQueryError("Can't filter by date")

    #     dateRange = datetime_.split("/")

    #     if _START_AND_END := len(dateRange) == 2:  # noqa F841
    #         start, end = dateRange

    #         # python does not accept Z at the end of the datetime even though that is a valid ISO 8601 datetime
    #         if start.endswith("Z"):
    #             start = start.replace("Z", "+00:00")

    #         if end.endswith("Z"):
    #             end = end.replace("Z", "+00:00")

    #         start = (
    #             datetime.datetime.min
    #             if start == ".."
    #             else datetime.datetime.fromisoformat(start)
    #         )
    #         end = (
    #             datetime.datetime.max
    #             if end == ".."
    #             else datetime.datetime.fromisoformat(end)
    #     )
    #     start, end = (
    #         start.replace(tzinfo=datetime.timezone.utc),
    #         end.replace(tzinfo=datetime.timezone.utc),
    #     )

    #     if start > end:
    #         raise ProviderQueryError(
    #             "Start date must be before end date but got {} and {}".format(
    #                 start, end
    #             )
    #         )

    #     return

    # elif _ONLY_MATCH_ONE_DATE := len(dateRange) == 1:  # noqa

    #     # By casting to a string we can use .str.contains to coarsely check.
    #     # We want 2019-10 to match 2019-10-01, 2019-10-02, etc.
    #     return df[dates.astype(str).str.startswith(datetime_)]
    # else:
    #     raise ProviderQueryError(
    #         "datetime_ must be a date or date range with two dates separated by '/' but got {}".format(
    #             datetime_
    #         )
    #     )
