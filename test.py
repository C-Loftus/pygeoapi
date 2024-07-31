import urllib.parse
import urllib.request
from datetime import date
import json

params = {}
params['after'] = '2020-05-28'
params['before'] = date.today().strftime("%Y-%m-%d")
params['filename'] = 'Lake Mead Hoover Dam and Powerplant Daily Lake/Reservoir Storage-af Time Series Data'
params['order'] = 'ASC'
params['type'] = 'json'  # Request JSON data
params['itemId'] = 6124
url = "https://data.usbr.gov/rise/api/result/download?"

# Construct the URL with query parameters
full_url = url + urllib.parse.urlencode(params)

# Fetch data
with urllib.request.urlopen(full_url) as response:
    data = response.read().decode('utf-8')

# Write data to JSON file
with open('data.json', 'w') as json_file:
    json_file.write(data)
