"""Turn a POI row into the text we embed, plus a fingerprint of that text."""
import hashlib


# Google Places tags that carry no meaning for search.
NOISE_TAGS = {"yes"}


def build_poi_document(poi) -> str:
    """Build the text that represents one POI in the vector index.

    Lines, in order (skip a line, or a part of it, when its data is missing):
        <name>
        Type: <type>. Neighborhood: <neighborhood>.
        Tags: <tag>, <tag>.
        <summary>
        <description>
    Format details and edge cases: 练习册 Part 2.1 / 2.2.
    """
    result = []
    # name
    name = poi_engineering(poi.name)
    result.append(name)

    # type
    type = "Type: " + poi_engineering(poi.type) + "."

    # neighborhood
    if poi.neighborhood:
        neighborhood = " Neighborhood: " + poi_engineering(poi.neighborhood) + "."
    else:
        neighborhood = ""

    type_neighborhood = type + neighborhood
    result.append(type_neighborhood)

    # tag
    VALID_TAGS = []
    for t in poi.tags or []:
        t_refine = " ".join(t.split("_"))
        t_refine = poi_engineering(t_refine)
        if t in NOISE_TAGS or t_refine in VALID_TAGS:
            continue;
        else:
            VALID_TAGS.append(t_refine)

    if VALID_TAGS:
        tag = "Tags: " + ", ".join(VALID_TAGS) + "."
        result.append(tag)


    # summary
    if poi.summary :
        summary = poi_engineering(poi.summary)
        if summary:
            result.append(summary)

    # description
    if poi.description:
        description = poi_engineering(poi.description)
        if description:
            result.append(description)

    return "\n".join(result);


def poi_engineering(string) -> str:
    return " ".join(string.split())



def content_hash(document: str) -> str:
    """SHA-256 of the document as a 64-character hex string (练习册 Part 2.3)."""
    return hashlib.sha256(document.encode()).hexdigest()
