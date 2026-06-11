import os

import pytest
from fastapi.testclient import TestClient

# Full-env test: needs eclipse-sumo (matrix_api.main imports the kernel), the
# redis client AND a reachable Redis with the demo scenario cached (docker
# compose up). In bare mode it skips cleanly -- tests/test_runtime_hardening.py
# covers the pipeline against mocked kernel seams.
pytest.importorskip("sumo", reason="eclipse-sumo not installed (bare env)")
redis = pytest.importorskip("redis", reason="redis client not installed (bare env)")


def _redis_up() -> bool:
    try:
        client = redis.from_url(
            os.environ.get("MATRIX_REDIS_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        try:
            return bool(client.ping())
        finally:
            client.close()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _redis_up(), reason="Redis not reachable (full-env test)")

from matrix_api.main import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)

def test_ws_stream_all_modules(client):
    """Test the WebSocket progressive pipeline (S8)."""
    # This uses the demo scenario since we pass "demo" which is cached
    with client.websocket_connect("/simulate/demo") as websocket:
        # 1. ACCEPTED
        data = websocket.receive_json()
        assert data["type"] == "ACCEPTED"
        assert data["scenario_id"] == "demo"
        
        # 2. PLAYBACK_FRAME (variable number depending on the trajectory)
        frames_received = 0
        while True:
            data = websocket.receive_json()
            if data["type"] == "PLAYBACK_FRAME":
                frames_received += 1
                assert "tick" in data
                assert "agents" in data
            else:
                break
                
        # 3. DIMENSION_RESULT
        # The first non-frame event should be a DIMENSION_RESULT
        dim_results = []
        if data["type"] == "DIMENSION_RESULT":
            dim_results.append(data)
            
        # Continue collecting DIMENSION_RESULTs
        while True:
            data = websocket.receive_json()
            if data["type"] == "DIMENSION_RESULT":
                dim_results.append(data)
            else:
                break
                
        # Total equations across all 5 modules:
        # BEH (3) + ECO (4) + SOC (3) + ECON (3) + SOCI (4) = 17
        assert len(dim_results) == 17
        
        dimensions_seen = {r["dimension"] for r in dim_results}
        assert dimensions_seen == {"behavioral", "ecological", "social", "economic", "societal"}
        
        for r in dim_results:
            assert "equation_id" in r
            assert "input_dataset_ids" in r
            assert "value" in r
            assert "confidence" in r
            
        # 4. SYNTHESIS
        assert data["type"] == "SYNTHESIS"
        assert "narrative" in data
        assert "citations" in data
        
        # 5. DONE
        data = websocket.receive_json()
        assert data["type"] == "DONE"
        assert "duration_ms" in data
