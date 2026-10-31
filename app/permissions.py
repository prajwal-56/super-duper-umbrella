"""RBAC matrix (BUILD_PLAN §14) as data. A route hides nothing by itself: every route declares a permission."""

from __future__ import annotations

ROLES = ("admin", "staff", "customer")

# permission -> roles allowed
MATRIX: dict[str, frozenset[str]] = {
    "catalog:read": frozenset({"admin", "staff"}),
    "catalog:write": frozenset({"admin"}),
    "discount:read": frozenset({"admin", "staff"}),
    "discount:write": frozenset({"admin"}),
    "discount:attach": frozenset({"admin", "staff"}),
    "staff:manage": frozenset({"admin"}),
    "customer:write": frozenset({"admin", "staff"}),
    "sub:read": frozenset({"admin", "staff"}),
    "sub:write": frozenset({"admin", "staff"}),
    "billing:run": frozenset({"admin", "staff"}),
    "invoice:read": frozenset({"admin", "staff"}),
    "invoice:write": frozenset({"admin", "staff"}),
    "payment:read": frozenset({"admin", "staff"}),
    "payment:write": frozenset({"admin", "staff"}),
    "report:read": frozenset({"admin", "staff"}),
    "clock:admin": frozenset({"admin"}),
    "demo:admin": frozenset({"admin"}),
    "portal:own": frozenset({"customer"}),
}

# Permissions that only make sense while DEMO_MODE is on. The matrix still
# declares them; deps.require() additionally rejects them when demo mode is off.
DEMO_ONLY = frozenset({"clock:admin", "demo:admin"})


def can(role: str, permission: str) -> bool:
    """True when `role` holds `permission`."""
    if permission not in MATRIX:
        raise KeyError(f"unknown permission {permission!r}")
    return role in MATRIX[permission]


def permissions_for(role: str) -> set[str]:
    return {name for name, roles in MATRIX.items() if role in roles}
