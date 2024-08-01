from typing import Literal, TypedDict


class EDRQuery(TypedDict):
    data_queries: list[dict]


class RiseCatalogItems(TypedDict):
    data: list[dict[Literal["type"] : str, Literal["id"] : str]]


class RiseLocationDatapoint(TypedDict):
    relationships: dict[Literal["catalogItems"] : RiseCatalogItems]
    id: str
    type: Literal["Location"]


class RiseLocationResponse(TypedDict):
    links: dict[
        Literal["self"] | Literal["first"] | Literal["last"] | Literal["next"] : str
    ]
    meta: dict[
        Literal["totalItems"] : int,
        Literal["itemsPerPage"] : int,
        Literal["currentPage"] : int,
    ]

    data: list[RiseLocationDatapoint]


class EDRResponse(TypedDict):
    type: Literal["FeatureCollection"]
    features: list[
        dict[
            Literal["type"] : Literal["Feature"],
            Literal["id"] : str,
            Literal["properties"] : dict,
        ],
        Literal["geometry"] : dict,  # type: ignore
    ]


class LocationQueryOptions(TypedDict):
    id: int
    parameterName: list[str]
    crs: str
    datetime: str
