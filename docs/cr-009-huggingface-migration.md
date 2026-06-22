# CR-009: Hugging Face Spaces Migration

**Date:** 2026-06-22
**Status:** Approved
**Author:** Antigravity (on behalf of User)

## Context
The MATRIX architecture originally used Hugging Face Spaces for hosting the FastAPI backend, SUMO Docker container, and Python workers. To optimize our deployment infrastructure, we are migrating the backend services to Hugging Face Spaces using Docker. The Next.js frontend will remain on Vercel. 

## Decision
- Decommission Hugging Face Spaces deployment (`app/fly.toml`).
- Deploy the FastAPI backend and SUMO simulation engine as a Docker-based Hugging Face Space.
- The frontend architecture (Vercel) remains unchanged.
- Use Hugging Face Secrets for environment variable management instead of `fly secrets`.

## Consequences
- **Deployment Process:** Developers will use git push to the Hugging Face Space remote or GitHub Actions to trigger deployments, replacing the `fly deploy` command.
- **Secrets Management:** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, and database URLs must be configured in the Hugging Face Space settings.
- **Removed Dependencies:** Fly CLI is no longer required for operational tasks.
