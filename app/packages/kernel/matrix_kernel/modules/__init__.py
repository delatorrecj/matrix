"""The five impact modules -- each scores the one trajectory dataset (PRD-F3).

Built in confidence order: behavioral, ecological, social, economic, societal.
Each exposes score(trajectory, datasets) -> list[DimensionResult] (one result per
equation in its methods-matrix §3 block). Numbers come from the trajectories +
the registry equations -- never the LLM (glass-box, PRD-F14).
"""
