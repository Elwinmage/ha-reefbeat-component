"""JSONPath filter ANDs written for the installed jsonpath-ng.

jsonpath-ng 1.9 only parses `&`; recent versions accept `&&` and deprecate
`&` (removed in 2.0). The integration writes `&&` and api.parse translates.
"""

from __future__ import annotations

import warnings
from unittest.mock import patch

from custom_components.redsea.reefbeat import api

DATA = {"data": [{"type": "ph", "uid": "a"}, {"type": "ph", "uid": "b"}]}


def test_normalize_filters_both_ways() -> None:
    path = "$.data[?(@.type=='ph' && @.uid=='a')]"
    assert api.normalize_filters(path, "&") == "$.data[?(@.type=='ph' & @.uid=='a')]"
    assert api.normalize_filters(path, "&&") == path
    old = "$.data[?(@.type=='ph' & @.uid=='a' & @.x==1)]"
    assert api.normalize_filters(old, "&&") == (
        "$.data[?(@.type=='ph' && @.uid=='a' && @.x==1)]"
    )
    # A literal holding "&" (a query string) is left alone
    literal = "$.sources[?(@.name=='/probe/offset?type=orp&uid=1')].data"
    assert api.normalize_filters(literal, "&") == literal
    assert api.normalize_filters(literal, "&&") == literal


def test_parse_without_deprecation_warning() -> None:
    api.parse.cache_clear()
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        found = api.parse("$.data[?(@.type=='ph' & @.uid=='b')]").find(DATA)
        assert [m.value["uid"] for m in found] == ["b"]
        found = api.parse("$.data[?(@.type=='ph' && @.uid=='a')]").find(DATA)
        assert [m.value["uid"] for m in found] == ["a"]
    api.parse.cache_clear()


def test_detect_and_operator() -> None:
    assert api._detect_and_operator() == "&&"

    def old_parser(expr: str) -> object:
        if "&&" in expr:
            raise ValueError("Parse error near token &")
        return object()

    with patch.object(api, "_parse", old_parser):
        assert api._detect_and_operator() == "&"
