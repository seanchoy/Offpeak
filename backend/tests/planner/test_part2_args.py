"""Part 2: never trust the model's arguments (练习册 Part 2)."""
import pytest


def parse(args, **kwargs):
    from app.services.ai.search_tool import parse_search_args

    return parse_search_args(args, **kwargs)


def test_part2_only_a_query_gives_the_defaults():
    from app.services.rag.retriever import SearchFilters

    request = parse({"query": "  quiet art  "})
    assert request.query == "quiet art"
    assert request.k == 5
    assert request.filters == SearchFilters()


@pytest.mark.parametrize("args", [{}, {"query": ""}, {"query": "   "}, {"query": 42}, {"query": None}])
def test_part2_a_missing_or_blank_query_is_an_argument_error(args):
    from app.services.ai.search_tool import ToolArgumentError

    with pytest.raises(ToolArgumentError):
        parse(args)


def test_part2_tool_argument_error_is_a_value_error():
    from app.services.ai.search_tool import ToolArgumentError

    assert issubclass(ToolArgumentError, ValueError)


@pytest.mark.parametrize(
    ("k", "expected"),
    [(3, 3), (3.0, 3), (0, 1), (-2, 1), (50, 8), (8, 8), (2.5, 5), ("3", 5), (True, 5), (None, 5)],
)
def test_part2_k_is_clamped_to_1_to_8_and_odd_values_fall_back_to_5(k, expected):
    assert parse({"query": "art", "k": k}).k == expected


def test_part2_types_keep_known_values_once_in_order():
    from app.models.poi_model import POIType

    request = parse({"query": "art", "types": ["museum", "zoo", "Gallery", "museum", " park "]})
    assert request.filters.types == (POIType.museum, POIType.gallery, POIType.park)


def test_part2_a_single_type_string_is_accepted_and_unknown_types_mean_no_filter():
    from app.models.poi_model import POIType

    assert parse({"query": "art", "types": "museum"}).filters.types == (POIType.museum,)
    assert parse({"query": "art", "types": ["zoo", "aquarium"]}).filters.types == ()


def test_part2_only_a_real_true_switches_a_filter_on():
    request = parse({"query": "art", "indoor_only": True, "wheelchair": "true"})
    assert request.filters.indoor_only is True
    assert request.filters.wheelchair is False


def test_part2_a_wheelchair_user_always_gets_the_wheelchair_filter():
    assert parse({"query": "art"}, wheelchair_user=True).filters.wheelchair is True
    assert parse({"query": "art", "wheelchair": False}, wheelchair_user=True).filters.wheelchair is True


def test_part2_unknown_arguments_are_ignored():
    assert parse({"query": "art", "city": "Paris", "limit": 2}).k == 5
