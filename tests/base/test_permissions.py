"""The RBAC matrix itself (R-RBAC-01, BUILD_PLAN §14)."""

import pytest

from app.permissions import MATRIX, ROLES, can, permissions_for


def test_admin_can_manage_catalog_staff_and_discounts():
    assert can("admin", "catalog:write")
    assert can("admin", "staff:manage")
    assert can("admin", "discount:write")
    assert can("admin", "clock:admin")
    assert can("admin", "billing:run")


def test_staff_cannot_administer():
    assert can("staff", "catalog:read")
    assert can("staff", "sub:write")
    assert can("staff", "invoice:write")
    assert can("staff", "billing:run")
    assert not can("staff", "catalog:write")
    assert not can("staff", "staff:manage")
    assert not can("staff", "discount:write")
    assert not can("staff", "clock:admin")
    assert not can("staff", "portal:own")


def test_customer_has_only_the_portal():
    assert permissions_for("customer") == {"portal:own"}
    for permission in MATRIX:
        if permission != "portal:own":
            assert not can("customer", permission)


def test_unknown_permission_is_an_error():
    with pytest.raises(KeyError):
        can("admin", "nope:nope")


def test_every_matrix_row_has_at_least_one_role():
    for permission, roles in MATRIX.items():
        assert roles, permission
        assert roles <= set(ROLES)
