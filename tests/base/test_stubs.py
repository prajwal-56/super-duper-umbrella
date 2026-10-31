"""The stub reporter works (and proves the guard can see markers)."""

from scripts.check_stubs import MARKER, scan


def test_marker_pattern_matches():
    assert MARKER.search('raise NotImplementedError("CONTRACT-STUB owner=B")')


def test_scan_returns_a_mapping():
    found = scan()
    assert isinstance(found, dict)
    for owner, locations in found.items():
        assert owner in {"A", "B", "C", "D"}
        assert locations
