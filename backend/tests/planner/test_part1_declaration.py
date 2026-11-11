"""Part 1: the tool declaration Gemini reads (练习册 Part 1)."""
from google.genai import types


def declaration():
    from app.services.ai.search_tool import search_pois_declaration

    return search_pois_declaration()


def test_part1_name_and_required_query():
    d = declaration()
    assert d.name == "search_pois"
    assert d.parameters.type == types.Type.OBJECT
    assert d.parameters.required == ["query"]


def test_part1_every_parameter_has_the_right_type_and_a_description():
    props = declaration().parameters.properties
    assert set(props) == {"query", "k", "types", "indoor_only", "wheelchair"}
    assert props["query"].type == types.Type.STRING
    assert props["k"].type == types.Type.INTEGER
    assert props["types"].type == types.Type.ARRAY
    assert props["indoor_only"].type == types.Type.BOOLEAN
    assert props["wheelchair"].type == types.Type.BOOLEAN
    for name, schema in props.items():
        assert schema.description, f"{name} has no description: the model only knows what you write"


def test_part1_types_enum_comes_from_the_poi_type_enum():
    from app.models.poi_model import POIType

    items = declaration().parameters.properties["types"].items
    assert items.type == types.Type.STRING
    assert items.enum == [t.value for t in POIType]


def test_part1_description_says_when_to_call_it():
    text = declaration().description.lower()
    assert "recommend" in text, "say when to call it: recommendations / places that match a mood"
    assert "only" in text, "say that the planner may recommend only what the tool returns"
