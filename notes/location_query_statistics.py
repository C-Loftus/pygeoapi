import asyncio
import requests
from pygeoapi.provider.rise_edr_helpers import (
    LocationHelper,
    fetch_url_group,
    flatten_values,
)
import time

url = "https://data.usbr.gov/rise/api/location"
headers = {"accept": "application/vnd.api+json"}
response = requests.get(
    url,
    headers=headers,
).json()

items = LocationHelper.get_catalogItemURLs(response)

counter = {i: len(v) for i, v in items.items()}

# {'6902': 2, '6888': 1, '6889': 12, '6885': 2, '282': 16, '3091': 118, '6882': 1, '3712': 1, '3660': 1, '3654': 1, '388': 6, '3652': 1, '3658': 2, '3657': 1, '3656': 1, '3648': 1, '268': 5, '257': 7, '498': 3, '3670': 2, '424': 6, '3674': 2, '3640': 3, '3585': 13, '3584': 30}
print(counter)


delta: list[float] = []

for i in range(6):
    start = time.time()
    resp = asyncio.run(fetch_url_group(flatten_values(items)))
    delta.append(time.time() - start)

# [5.935041666030884, 3.5702786445617676, 3.530980348587036, 36.61881160736084, 6.0607383251190186, 19.794275283813477]
print(delta)
