# CR-008: Azure OpenAI Migration

**Date:** 2026-06-22
**Status:** Approved
**Author:** Antigravity (on behalf of User)

## Context
The MATRIX architecture originally mandated Azure OpenAI GPT-5.4 for orchestration and synthesis, and Azure OpenAI GPT-5.4 for high-volume persona generation (see PRD-F2, PRD-F7, and SDD §8). Due to billing constraints on the Google side, a migration to an Azure OpenAI GPT-5.4 endpoint was proposed and approved by the User. 

## Decision
- Replace `openai` with the Azure OpenAI Python SDK (`openai`).
  - *Note: See [CR-009](cr-009-azure-foundry-client.md) — the client class was later adjusted to `openai.OpenAI` for Azure AI Foundry v1 endpoint compatibility.*
- Use the provided Azure OpenAI GPT-5.4 deployment (`gpt-5.4`) for **both** orchestration/synthesis and high-volume persona generation.
- The glass-box citation guard mechanism remains identical. The LLM acts solely as a parser and synthesizer; all raw numbers and metrics remain strictly deterministic from the kernel.

## Consequences
- **Environment Variables:** Deprecated `GEMINI_API_KEY`. Introduced `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, and `AZURE_OPENAI_DEPLOYMENT`.
- **Cost:** Both low-volume complex reasoning (orchestration) and high-volume generation (personas) are now bound to the same `gpt-5.4` deployment.
- **Latency:** We will monitor Azure OpenAI's latency against the 90-second SLO, though it is expected to be comparable to or faster than the previous provider.
- **Dependencies:** The application has standardized on the `openai` package for all LLM calls.
