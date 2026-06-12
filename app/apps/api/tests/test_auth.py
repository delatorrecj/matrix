"""Auth + rate limit + CORS tests against the real app (matrix_api/auth.py wiring).

Everything is env-gated and defaults OFF, so the first block proves the
zero-config path stays wide open (local dev / demo). The WS success path mocks
the kernel boundary (_get_trajectory, module.score, synthesize) like the rest of
the API tests treat it -- no Redis/SUMO/Gemini needed at runtime, but importing
matrix_api.main pulls in the kernel modules, which need the eclipse-sumo wheel.
In bare mode this module skips cleanly -- tests/test_auth_unit.py covers the
pure auth primitives bare.
"""
import pytest

pytest.importorskip("sumo", reason="eclipse-sumo not installed (bare env)")

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from matrix_kernel.results import DimensionResult  # noqa: E402
from matrix_kernel.trajectory import Frame, Trajectory  # noqa: E402

from matrix_api import auth  # noqa: E402
from matrix_api import db  # noqa: E402
from matrix_api import main as api_main  # noqa: E402
from matrix_api.main import app  # noqa: E402

ENV_VARS = (
    "MATRIX_AUTH_ENABLED",
    "MATRIX_API_KEYS",
    "MATRIX_RATE_LIMIT_ENABLED",
    "MATRIX_RATE_LIMIT_PER_MIN",
    "MATRIX_ALLOWED_ORIGINS",
)


@pytest.fixture(autouse=True)
def clean_auth_env(monkeypatch):
    """Each test starts from the zero-config default and an empty limiter."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    auth.reset_rate_limiter()
    yield
    auth.reset_rate_limiter()


@pytest.fixture
def client():
    # These tests probe auth/rate-limit behavior through GET /runs/r-1, which
    # returns an honest 404 for unknown runs since the persistence layer landed —
    # seed the run so 200 means "authorized", not "stub endpoint".
    db.save_run("s-auth-probe", run_id="r-1", status="done")
    return TestClient(app)


def _enable_auth(monkeypatch, keys="test-key-1, test-key-2"):
    monkeypatch.setenv("MATRIX_AUTH_ENABLED", "true")
    monkeypatch.setenv("MATRIX_API_KEYS", keys)


def _fake_result(dimension="behavioral", equation_id="BEH-1"):
    return DimensionResult(
        dimension=dimension,
        metric="fake metric",
        equation_id=equation_id,
        value=1.0,
        range=(0.5, 1.5),
        unit="trips/day",
        confidence="M",
        input_dataset_ids=["OSM-ILO"],
    )


@pytest.fixture
def mocked_kernel(monkeypatch):
    """Stub the kernel boundary so the WS happy path needs no Redis/SUMO/Gemini."""
    traj = Trajectory(edge_counts={"e1": 3}, frames=[Frame(tick=0.0, agents=[])])
    monkeypatch.setattr(api_main, "_get_trajectory", lambda scenario_id: traj)
    monkeypatch.setattr(api_main.behavioral, "score", lambda t: [_fake_result("behavioral", "BEH-1")])
    monkeypatch.setattr(api_main.ecological, "score", lambda t: [_fake_result("ecological", "ECO-2")])
    monkeypatch.setattr(api_main.social, "score", lambda t: [_fake_result("social", "SOC-1")])
    monkeypatch.setattr(api_main.economic, "score", lambda t: [_fake_result("economic", "ECON-1")])
    monkeypatch.setattr(
        api_main.societal, "score", lambda t, **kw: [_fake_result("societal", "SOCI-1")]
    )
    monkeypatch.setattr(api_main, "synthesize", lambda results: ("narrative [BEH-1]", ["BEH-1"]))


def _drain_ws(websocket):
    """Read events until DONE; return the list of event types seen."""
    types = []
    while True:
        data = websocket.receive_json()
        types.append(data["type"])
        if data["type"] == "DONE":
            return types


# ---------------------------------------------------------------- default: open

def test_default_everything_open(client):
    """Zero config -> no auth, no rate limit (local dev / demo path)."""
    assert client.get("/health").status_code == 200
    for _ in range(5):
        assert client.get("/runs/r-1").status_code == 200


def test_default_ws_open(client, mocked_kernel):
    with client.websocket_connect("/simulate/demo") as websocket:
        types = _drain_ws(websocket)
    assert types[0] == "ACCEPTED"
    assert types[-1] == "DONE"


# ----------------------------------------------------------------- bearer auth

def test_auth_enabled_missing_key_401(client, monkeypatch):
    _enable_auth(monkeypatch)
    res = client.get("/runs/r-1")
    assert res.status_code == 401
    assert res.headers["WWW-Authenticate"] == "Bearer"


def test_auth_enabled_wrong_key_401(client, monkeypatch):
    _enable_auth(monkeypatch)
    res = client.get("/runs/r-1", headers={"Authorization": "Bearer nope"})
    assert res.status_code == 401


def test_auth_enabled_wrong_scheme_401(client, monkeypatch):
    _enable_auth(monkeypatch)
    res = client.get("/runs/r-1", headers={"Authorization": "Basic test-key-1"})
    assert res.status_code == 401


def test_auth_enabled_valid_key_ok(client, monkeypatch):
    _enable_auth(monkeypatch)
    # second key in the comma-separated list, with surrounding whitespace stripped
    res = client.get("/runs/r-1", headers={"Authorization": "Bearer test-key-2"})
    assert res.status_code == 200


def test_auth_enabled_no_keys_configured_fails_closed(client, monkeypatch):
    monkeypatch.setenv("MATRIX_AUTH_ENABLED", "true")  # no MATRIX_API_KEYS
    res = client.get("/runs/r-1", headers={"Authorization": "Bearer anything"})
    assert res.status_code == 401


def test_exempt_routes_stay_open(client, monkeypatch):
    _enable_auth(monkeypatch)
    assert client.get("/health").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
    # /validation is exempt by path; the route lands in a later PR, so just
    # prove auth doesn't intercept it (404 from the router, never 401).
    assert client.get("/validation").status_code != 401


# ----------------------------------------------------------------- rate limit

def test_rate_limit_per_key_429_with_retry_after(client, monkeypatch):
    _enable_auth(monkeypatch)
    monkeypatch.setenv("MATRIX_RATE_LIMIT_PER_MIN", "3")
    headers = {"Authorization": "Bearer test-key-1"}
    for _ in range(3):
        assert client.get("/runs/r-1", headers=headers).status_code == 200
    res = client.get("/runs/r-1", headers=headers)
    assert res.status_code == 429
    assert int(res.headers["Retry-After"]) >= 1
    # buckets are per key: a different key is not throttled
    other = client.get("/runs/r-1", headers={"Authorization": "Bearer test-key-2"})
    assert other.status_code == 200


def test_rate_limit_ip_fallback_when_auth_disabled(client, monkeypatch):
    monkeypatch.setenv("MATRIX_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("MATRIX_RATE_LIMIT_PER_MIN", "2")
    assert client.get("/runs/r-1").status_code == 200
    assert client.get("/runs/r-1").status_code == 200
    res = client.get("/runs/r-1")
    assert res.status_code == 429
    assert int(res.headers["Retry-After"]) >= 1


def test_rate_limit_can_be_disabled_with_auth_on(client, monkeypatch):
    _enable_auth(monkeypatch)
    monkeypatch.setenv("MATRIX_RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("MATRIX_RATE_LIMIT_PER_MIN", "1")
    headers = {"Authorization": "Bearer test-key-1"}
    for _ in range(3):
        assert client.get("/runs/r-1", headers=headers).status_code == 200


def test_rate_limit_skips_exempt_routes(client, monkeypatch):
    monkeypatch.setenv("MATRIX_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("MATRIX_RATE_LIMIT_PER_MIN", "1")
    for _ in range(3):
        assert client.get("/health").status_code == 200


# ----------------------------------------------------------------------- CORS

def test_cors_preflight_allows_default_origin(client):
    res = client.options(
        "/scenario",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_preflight_rejects_unlisted_origin(client):
    res = client.options(
        "/scenario",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.status_code == 400
    assert "access-control-allow-origin" not in res.headers


def test_cors_simple_request_mirrors_allowed_origin(client):
    res = client.get("/health", headers={"Origin": "http://127.0.0.1:3000"})
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


# ------------------------------------------------------------------- WS auth

def test_ws_missing_key_rejected_1008(client, monkeypatch):
    _enable_auth(monkeypatch)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/simulate/demo"):
            pass
    assert exc_info.value.code == 1008


def test_ws_bad_key_rejected_1008(client, monkeypatch):
    _enable_auth(monkeypatch)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/simulate/demo?api_key=nope"):
            pass
    assert exc_info.value.code == 1008


def test_ws_non_ascii_key_rejected_1008_not_crash(client, monkeypatch):
    # compare_digest would raise TypeError on non-ASCII str; must be a clean 1008.
    _enable_auth(monkeypatch)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/simulate/demo?api_key=caf%C3%A9"):
            pass
    assert exc_info.value.code == 1008


def test_ws_valid_query_param_key_streams(client, monkeypatch, mocked_kernel):
    _enable_auth(monkeypatch)
    with client.websocket_connect("/simulate/demo?api_key=test-key-1") as websocket:
        types = _drain_ws(websocket)
    assert types[0] == "ACCEPTED"
    assert types.count("DIMENSION_RESULT") == 5
    assert types[-2] == "SYNTHESIS"
    assert types[-1] == "DONE"


def test_ws_valid_bearer_header_streams(client, monkeypatch, mocked_kernel):
    _enable_auth(monkeypatch)
    with client.websocket_connect(
        "/simulate/demo", headers={"Authorization": "Bearer test-key-2"}
    ) as websocket:
        types = _drain_ws(websocket)
    assert types[0] == "ACCEPTED"
    assert types[-1] == "DONE"


def test_ws_rate_limited_rejected_1013(client, monkeypatch, mocked_kernel):
    _enable_auth(monkeypatch)
    monkeypatch.setenv("MATRIX_RATE_LIMIT_PER_MIN", "1")
    with client.websocket_connect("/simulate/demo?api_key=test-key-1") as websocket:
        _drain_ws(websocket)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/simulate/demo?api_key=test-key-1"):
            pass
    assert exc_info.value.code == 1013
