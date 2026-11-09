"""Six hand-made POIs for Parts 5 and 6.

Vector axes: [art, nature, history]. Queries in QUERIES use the same axes, so the
expected cosine ranking can be worked out by hand (练习册 Part 5 has the table).
"""
from tests.rag.support import pad

POIS = [
    # slug, type, tags, accessibility, vector, document
    ("museum-of-modern-art", "museum", ["art_museum", "indoor"], ["wheelchair"], (0.9, 0.1, 0.3),
     ("Museum of Modern Art\nType: museum.\nTags: art museum, indoor.\n"
      "Modern and contemporary art: paintings, sculpture and design.")),
    ("the-met-cloisters", "museum", ["art_museum", "indoor"], [], (0.6, 0.2, 0.75),
     ("The Met Cloisters\nType: museum.\nTags: art museum, indoor.\n"
      "Medieval art and architecture in Fort Tryon Park.")),
    ("tenement-museum", "museum", ["history_museum", "indoor"], [], (0.15, 0.05, 1.0),
     ("Tenement Museum\nType: museum.\nTags: history museum, indoor.\n"
      "Immigrant life on the Lower East Side.")),
    ("central-park", "park", ["park", "outdoor"], ["wheelchair"], (0.1, 1.0, 0.1),
     "Central Park\nType: park.\nTags: park, outdoor.\nMeadows, lakes and woodland walks."),
    # Tagged indoor by mistake, exactly like the real row.
    ("the-ramble-central-park", "park", ["indoor"], [], (0.2, 0.9, 0.3),
     "The Ramble\nType: park.\nTags: indoor.\nA wild woodland for bird watching."),
]

INACTIVE = ("old-gallery", "gallery", ["indoor"], [], (1.0, 0.0, 0.0),
            "Old Gallery\nType: gallery.\nModern art, closed for good.")

QUERIES = {
    "modern art": (1.0, 0.0, 0.0),
    "a walk in nature": (0.0, 1.0, 0.0),
    "local history": (0.0, 0.0, 1.0),
    # A query the fake embedding gets wrong on purpose (points at nature).
    "immigrant history": (0.0, 1.0, 0.0),
}


def load(add_poi, add_embedding):
    from app.models.poi_model import POIType

    for slug, type_, tags, labels, vector, document in POIS + [INACTIVE]:
        poi = add_poi(slug, type=POIType(type_), tags=tags, accessibility_labels=labels,
                      is_active=slug != INACTIVE[0])
        add_embedding(poi, pad(*vector), document=document)
