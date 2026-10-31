"""End-to-end: signup -> login -> signed-in page -> logout (the G1 path)."""


def test_signup_login_logout_flow(client):
    signup = client.post(
        "/signup",
        data={
            "name": "Meera Iyer",
            "email": "meera@example.com",
            "password": "MeeraPass#1",
        },
        follow_redirects=False,
    )
    assert signup.status_code == 303
    assert signup.headers["location"] == "/login?signed_up=1"

    login = client.post(
        "/login",
        data={"email": "meera@example.com", "password": "MeeraPass#1"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    page = client.get("/")
    assert page.status_code == 200
    assert "meera@example.com" in page.text
    assert "customer" in page.text

    out = client.post("/logout", follow_redirects=False)
    assert out.status_code == 303
    assert client.get("/", follow_redirects=False).headers["location"] == "/login"
