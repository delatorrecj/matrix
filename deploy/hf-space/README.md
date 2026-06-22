---
title: MATRIX System
emoji: 🏙️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# MATRIX System Backend

This Space runs the FastAPI backend for the MATRIX System (Multi-Agent Twin for Routing & Infrastructure eXchange).

It requires a persistent volume mounted at `/data` containing the SUMO `.net.xml` and `.rou.xml` files.
