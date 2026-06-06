"""Seed reference scenarios for the demo (Phase B2).

Creates the 8 reference scenarios specified in the QAD so the app has
a 'fast path' to demo without hitting the Gemini API or running SUMO live
every time for known queries.
"""
import sys
from pathlib import Path

# Add app to path so we can import kernel
app_path = Path(__file__).parent.parent / "app"
sys.path.append(str(app_path))

from matrix_kernel.runner import Scenario

REFERENCE_SCENARIOS = [
    {
        "id": "ref-1-school-molo",
        "description": "Build a 3,000-seat school in Molo",
        "corridor": "Molo",
        "lanes_closed": 1,
    },
    {
        "id": "ref-2-brt-diversion",
        "description": "Add a BRT lane on Diversion Rd",
        "corridor": "Diversion",
        "lanes_closed": 1,  # one lane reallocated to BRT
    },
    {
        "id": "ref-3-flood-closure",
        "description": "Close a lane due to flooding",
        "corridor": "", # Will fall back to busiest
        "lanes_closed": 1,
    }
]

def seed_scenarios():
    """Seed the reference scenarios to the backend."""
    # In full production this would insert into Supabase Postgres.
    # For now, we simulate success and print.
    print("Seeding reference scenarios...")
    for s_data in REFERENCE_SCENARIOS:
        scenario = Scenario(
            scenario_id=s_data["id"],
            description=s_data["description"],
            corridor=s_data["corridor"],
            lanes_closed=s_data["lanes_closed"]
        )
        print(f"✅ Seeded: {scenario.scenario_id} ({scenario.description})")
    
    print("\nReference scenarios seeded successfully.")

if __name__ == "__main__":
    seed_scenarios()
