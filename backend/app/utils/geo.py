"""Belgian places with coordinates, for commuting-distance checks without an external geocoding API.

Covers the provincial capitals and larger towns. Unknown places simply skip the distance check
(the match explains that the distance could not be determined)."""

import math
import unicodedata

_PLACES: dict[str, tuple[float, float]] = {
    "brussel": (50.8503, 4.3517),
    "antwerpen": (51.2194, 4.4025),
    "gent": (51.0543, 3.7174),
    "brugge": (51.2093, 3.2247),
    "leuven": (50.8798, 4.7005),
    "mechelen": (51.0259, 4.4777),
    "hasselt": (50.9307, 5.3325),
    "genk": (50.9650, 5.5008),
    "maasmechelen": (50.9650, 5.6947),
    "tongeren": (50.7809, 5.4646),
    "sint-truiden": (50.8166, 5.1866),
    "aalst": (50.9378, 4.0403),
    "kortrijk": (50.8279, 3.2649),
    "oostende": (51.2154, 2.9286),
    "roeselare": (50.9465, 3.1227),
    "sint-niklaas": (51.1650, 4.1438),
    "turnhout": (51.3227, 4.9447),
    "geel": (51.1617, 4.9909),
    "lier": (51.1310, 4.5700),
    "vilvoorde": (50.9281, 4.4245),
    "zaventem": (50.8836, 4.4730),
    "diegem": (50.8960, 4.4400),
    "dendermonde": (51.0287, 4.1013),
    "beringen": (51.0499, 5.2269),
    "lommel": (51.2306, 5.3133),
    "ieper": (50.8503, 2.8850),
    "waregem": (50.8892, 3.4276),
    "liège": (50.6326, 5.5797),
    "namur": (50.4674, 4.8720),
    "charleroi": (50.4108, 4.4446),
    "mons": (50.4542, 3.9567),
    "louvain-la-neuve": (50.6681, 4.6118),
    "wavre": (50.7171, 4.6014),
    "nivelles": (50.5981, 4.3285),
    "tournai": (50.6056, 3.3878),
    "arlon": (49.6833, 5.8167),
    "verviers": (50.5891, 5.8623),
    "mouscron": (50.7436, 3.2139),
    "eupen": (50.6276, 6.0360),
    "luxembourg": (49.6116, 6.1319),
    "maastricht": (50.8514, 5.6910),
    "eindhoven": (51.4416, 5.4697),
}

_ALIASES = {
    "bruxelles": "brussel",
    "brussels": "brussel",
    "anvers": "antwerpen",
    "antwerp": "antwerpen",
    "gand": "gent",
    "ghent": "gent",
    "bruges": "brugge",
    "louvain": "leuven",
    "malines": "mechelen",
    "luik": "liège",
    "liege": "liège",
    "namen": "namur",
    "bergen": "mons",
    "doornik": "tournai",
    "nijvel": "nivelles",
    "waver": "wavre",
    "aarlen": "arlon",
    "courtrai": "kortrijk",
    "ostende": "oostende",
}


def _key(name: str) -> str:
    value = unicodedata.normalize("NFKC", name).strip().lower()
    value = value.split(",")[0].strip()
    return _ALIASES.get(value, value)


def coordinates(name: str | None) -> tuple[float, float] | None:
    if not name:
        return None
    key = _key(name)
    if key in _PLACES:
        return _PLACES[key]
    stripped = unicodedata.normalize("NFKD", key).encode("ascii", "ignore").decode()
    for place, coords in _PLACES.items():
        if unicodedata.normalize("NFKD", place).encode("ascii", "ignore").decode() == stripped:
            return coords
    return None


def distance_km(a: str | None, b: str | None) -> float | None:
    ca, cb = coordinates(a), coordinates(b)
    if ca is None or cb is None:
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, (*ca, *cb))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(h)), 1)


def same_place(a: str | None, b: str | None) -> bool:
    return bool(a and b and _key(a) == _key(b))


def known_places() -> list[str]:
    return sorted(_PLACES)
