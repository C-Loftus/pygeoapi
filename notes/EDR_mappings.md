# EDR Mappings Overview


In order for an endpoint to implement EDR, it needs to implement multiple query types. The main challenge is that the current output format of RISE requires joining data across multiple API queries to complete the EDR query.

> Note: In this document I am primarily focused on location queries. However, we will also want to implement other query types, probably at least locations, items, area, and cube. 
> 
> The challenges mapping RISE location queries into EDR are similar to the challenges with other types of queries. 

## Locations Query as an Example EDR Mapping Challenge

To query locations in RISE we use the `/location` endpoint. The `/location` endpoint returns a list of locations. However it does not contain all the info we need to implement the EDR query. 

- The EDR spec expects a location query to be able to be filtered by a `parameter-name` 
    - Thus, we need to get the list of the parameters associated with each location. 
        - parameter names are defined within the `/catalog-item` endpoint
    - We can only get this by fetching the catalog item associated with each location
    - As the result we end up needing to fetch every single catalog item in order to get the list of parameters for each location
        - This is roughly 250 queries

_`/location` returns a list of locations. Each location returns a list of catalog items. Each catalog item is associated with one `parameterName` which can be potentially null._

```mermaid
graph TD;
    A[/location/] --> B[List of Locations];
    B --> C[Location 1];
    B --> D[Location 2];
    B --> E[Location 3];
    B --> Z[Location ...N];
    C --> F[List of Catalog Items for Location 1];
    D --> G[List of Catalog Items for Location 2];
    E --> H[List of Catalog Items for Location 3];
    F --> I[Catalog Item 1A];
    F --> J[Catalog Item 1B];
    G --> K[Catalog Item 2A];
    G --> L[Catalog Item 2B];
    H --> M[Catalog Item 3A];
    H --> N[Catalog Item 3B];
    H --> O[Catalog Item 3C];
    H --> W[Catalog Item 3..M];

```

**How to construct an EDR location query with a `parameter-name` filter**

1. Query `/location`
2. Send ~250 independent fetch calls; one to each catalog item
3. Block until the last fetch returns
    > NOTE: If one fetch doesn't return, the query is incomplete
4. Filter the `/location` response by the passed in `parameter-name`

    
## Location Query Time Complexity

Each location query that requires a parameter filter usually ends up being ~5s, but sometimes there is unexpected [latency](#latency). In summary it requires:

- ~2s for location query
- ~3s to block until the last catalog item query (all are done independently, but one slow query slows everything down)
- 2s + 3s = ~5s in total to resolve the query

The number of queries is O(N) on the number of catalog items. 
- To generalize this, any time we want to filter on a value not included in the endpoint, our time complexity ends up being
- O(1) + O(N) 
    - _(Repeat extra O(N) if we have to join at multiple layers)_


## Other Challenges

### Error handling

Sometimes the API will return an internal server error without a description of what occured. This can be replicated by running the tests which query the following catalog items. The other catalog items return without issue.

If we are fetching multiple catalog items, then the query is incomplete and fails even if one fails.

```json
    "https://data.usbr.gov/rise/api/catalog-item/11007": {
        "type": "https://tools.ietf.org/html/rfc2616#section-10",
        "title": "An error occurred",
        "detail": "Internal Server Error"
    },
    "https://data.usbr.gov/rise/api/catalog-item/11013": {
        "type": "https://tools.ietf.org/html/rfc2616#section-10",
        "title": "An error occurred",
        "detail": "Internal Server Error"
    },
    "https://data.usbr.gov/rise/api/catalog-item/11050": {
        "type": "https://tools.ietf.org/html/rfc2616#section-10",
        "title": "An error occurred",
        "detail": "Internal Server Error"
    }
```

> Note: there was a previous issue where the API output data saying it was down for maintenace. However, this is no longer able to be reproduced. The following error arose starting around August 4.

### Latency

Latency is variable and not well defined without caching. In [the query statistics script](./location_query_statistics.py) the latency to complete a parameter-query varies between `[5.935041666030884, 3.5702786445617676, 3.530980348587036, 36.61881160736084, 6.0607383251190186, 19.794275283813477]`. This is significant variability.

Caching would reduce this but add more complexity.

## Joining multiple API calls deep

So far I have not encountered any EDR queries that require fetching json twice. i.e. `fetch json -> get key -> fetch json -> get key` chaining.

However, if we have to supported nested joins like this it adds complexlity with error handling. 

## Optimization Options

In order to implement EDR within the current schema of the RISE API, we need to join data across API endpoints. However during the process of fetching that data, most queries are independent.  Thus, there are options for optimization

- Fetch data needed for joins in parallel using `async`. 
    - **Baseline optimization described above**: needed for queries to be usable. 
    - Requires lots of data to be fetched unnecessarily.
- Cache the dependent data
    - Greatly reduces latency but adds complexity regarding when to invalidate the local cache with the new upstream data.
- Change the underlying API to Out put additional data needed for EDR queries
    - This should not require taking anything away, but it may cause the API to output duplicate data or deviate from the current patterns. 






