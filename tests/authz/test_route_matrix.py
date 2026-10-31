"""Every protected route declares a permission, and require() enforces it."""

from __future__ import annotations

import re

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.config import settings
from app.deps import require
from app.main import app
from app.permissions import DEMO_ONLY, MATRIX, can

PUBLIC_PATHS = {"/", "/login", "/signup", "/forgot", "/logout", "/health", "/reset/{token}"}


def _declared_permissions(route: APIRoute) -> list[str]:
    found = []
    stack = list(route.dependant.dependencies)
    while stack:
        dependency = stack.pop()
        permission = getattr(dependency.call, "permission", None)
        if permission:
            found.append(permission)
        stack.extend(dependency.dependencies)
    return found


def _protected_routes() -> list[APIRoute]:
    return [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path not in PUBLIC_PATHS
    ]


def _concrete_path(path: str) -> str:
    """Replace {param} placeholders with a value that simply does not exist."""
    return re.sub(r"\{[^}]+\}", "1", path)


def _matrix_allows(role: str, permissions: list[str]) -> bool:
    """What §14 says this role may do, including the DEMO_MODE restriction."""
    for permission in permissions:
        if permission in DEMO_ONLY and not settings.demo_mode:
            return False
        if not can(role, permission):
            return False
    return True


def test_every_protected_route_declares_a_known_permission():
    problems = []
    for route in _protected_routes():
        permissions = _declared_permissions(route)
        if not permissions:
            problems.append(f"{route.path} has no require(...) permission")
        for permission in permissions:
            if permission not in MATRIX:
                problems.append(f"{route.path} declares unknown permission {permission}")
    assert problems == []


@pytest.mark.parametrize("role", ["admin", "staff", "customer"])
def test_every_route_answers_exactly_as_the_matrix_says(role, create_user):
    """Walk the whole app as one role and compare each answer with §14.

    A role the matrix allows must never be refused (403). A role it does not
    allow must always be refused, whatever the handler would have done.
    """
    email = f"{role}@example.com"
    create_user(role=role, email=email)

    client = TestClient(app, base_url="http://testserver", raise_server_exceptions=False)
    response = client.post(
        "/login",
        data={"email": email, "password": "GoodPass#123"},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text

    problems = []
    for route in _protected_routes():
        permissions = _declared_permissions(route)
        allowed = _matrix_allows(role, permissions)
        path = _concrete_path(route.path)
        for method in sorted(route.methods):
            body = {} if method in {"GET", "HEAD"} else {"data": {}}
            result = client.request(method, path, follow_redirects=False, **body)
            if allowed and result.status_code == 403:
                problems.append(
                    f"{method} {path}: {role} was refused but §14 allows {permissions}"
                )
            if not allowed and result.status_code != 403:
                problems.append(
                    f"{method} {path}: {role} got {result.status_code}, "
                    f"expected 403 for {permissions}"
                )
    assert problems == []


def _guard_app() -> FastAPI:
    mini = FastAPI()

    @mini.get("/guard/admin")
    def admin_only(user=Depends(require("staff:manage"))):
        return {"role": user.role}

    @mini.get("/guard/staff")
    def staff_only(user=Depends(require("sub:read"))):
        return {"role": user.role}

    return mini


def _as(role: str, create_user, login) -> TestClient:
    email = f"{role}@example.com"
    create_user(role=role, email=email)
    login(email)
    from app.main import app as main_app

    main_client = TestClient(main_app, base_url="http://testserver")
    response = main_client.post(
        "/login", data={"email": email, "password": "GoodPass#123"}, follow_redirects=False
    )
    assert response.status_code == 303
    mini = TestClient(_guard_app(), base_url="http://testserver")
    for cookie in main_client.cookies.jar:
        mini.cookies.set(cookie.name, cookie.value)
    return mini


def test_require_allows_admin_and_blocks_staff(create_user, login):
    admin = _as("admin", create_user, login)
    assert admin.get("/guard/admin").status_code == 200
    assert admin.get("/guard/staff").status_code == 200

    staff = _as("staff", create_user, login)
    assert staff.get("/guard/admin").status_code == 403
    assert staff.get("/guard/staff").status_code == 200

    customer = _as("customer", create_user, login)
    assert customer.get("/guard/admin").status_code == 403
    assert customer.get("/guard/staff").status_code == 403


def test_require_redirects_browser_and_401s_api():
    mini = TestClient(_guard_app(), base_url="http://testserver")
    browser = mini.get("/guard/staff", headers={"Accept": "text/html"}, follow_redirects=False)
    assert browser.status_code == 303
    assert browser.headers["location"].startswith("/login")
    api = mini.get("/guard/staff", headers={"Accept": "application/json"})
    assert api.status_code == 401
