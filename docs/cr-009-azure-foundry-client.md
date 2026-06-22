# CR-009: Azure AI Foundry v1 Client Compatibility

**Date:** 2026-06-22
**Status:** Approved
**Author:** Antigravity (on behalf of User)

## Context
Following the Azure OpenAI migration (CR-008), the application experienced `404 Resource not found` errors when attempting to connect to the Azure AI Foundry endpoint (`https://<resource>.services.ai.azure.com/openai/v1`). 

The standard `openai.AzureOpenAI` Python client class builds a legacy URL path structure (`/openai/deployments/{name}/…?api-version=…`), which is incompatible with the standard v1 endpoint exposed by Azure AI Foundry.

## Decision
- Replace usage of `openai.AzureOpenAI` with the standard `openai.OpenAI` client class.
- Point the client's `base_url` to the Azure AI Foundry v1 endpoint.
- Continue using the standard Azure OpenAI environment variables (`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`).
- Pass the deployment name via the `model` argument in the API call.

## Consequences
- **Code:** Type hints across the matrix kernel (`orchestrator.py`, `synthesis.py`, `llm.py`, and tests) have been updated to expect `openai.OpenAI` instead of `openai.AzureOpenAI`.
- **Infrastructure:** The `make_client` factory logic now normalizes the Azure endpoint string and injects it as a `base_url` to the standard OpenAI client.
- **Reliability:** The 404 errors during scenario parsing have been eliminated.
