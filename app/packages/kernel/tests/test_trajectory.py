"""Tests for the frozen Trajectory schema helpers (PRD-F1)."""
from matrix_kernel.trajectory import Frame, Trajectory


def _frame(tick, agents):
    return Frame(tick=tick, agents=agents)


def test_observed_mode_share_counts_unique_agents():
    """Realized mode share counts each agent once (mode is deterministic per id), even when
    the same agent appears across multiple playback frames."""
    traj = Trajectory(
        edge_counts={},
        frames=[
            _frame(0.0, [
                {"id": "a", "lon": 0, "lat": 0, "mode": "jeepney"},
                {"id": "b", "lon": 0, "lat": 0, "mode": "jeepney"},
                {"id": "c", "lon": 0, "lat": 0, "mode": "walk"},
            ]),
            # 'a' reappears (same mode) -> must not be double-counted; 'd' is new.
            _frame(1.0, [
                {"id": "a", "lon": 0, "lat": 0, "mode": "jeepney"},
                {"id": "d", "lon": 0, "lat": 0, "mode": "walk"},
            ]),
        ],
    )
    share = traj.observed_mode_share()
    assert share == {"jeepney": 0.5, "walk": 0.5}  # 2 jeepney, 2 walk over 4 unique agents


def test_observed_mode_share_empty_when_no_agents():
    assert Trajectory(edge_counts={}, frames=[]).observed_mode_share() == {}


def test_observed_mode_share_survives_json_roundtrip():
    traj = Trajectory(
        edge_counts={"e1": 3},
        frames=[_frame(0.0, [{"id": "a", "lon": 1.0, "lat": 2.0, "mode": "tricycle"}])],
    )
    restored = Trajectory.from_json(traj.to_json())
    assert restored.observed_mode_share() == {"tricycle": 1.0}
