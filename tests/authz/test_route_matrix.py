"""Every protected route declares a permission, and require() enforces it."""

from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.deps import require
from app.main import app
from app.permissions import MATRIX

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


def test_every_protected_route_declares_a_known_permission():
    problems = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or route.path in PUBLIC_PATHS:
            continue
        permissions = _declared_permissions(route)
        if not permissions:
            problems.append(f"{route.path} has no require(...) permission")
        for permission in permissions:
            if permission not in MATRIX:
                problems.append(f"{route.path} declares unknown permission {permission}")
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
