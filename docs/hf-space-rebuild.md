# Rebuild the Hugging Face API Space

Do **not** redeploy Vercel. [matrix-atlan.vercel.app](https://matrix-atlan.vercel.app) is already on `main` (`c6466b4`). This rebuild is for the backend only: [delatorrecj/matrix-api-backend](https://huggingface.co/spaces/delatorrecj/matrix-api-backend).

The Space image is from **22 June 2026**. Its orchestrator remaps “build a 3,000-seat school in Molo” to `lane_closure`. GitHub `main` already has `new_facility` / BEH-4 (PR #54). The Dockerfile only `git clone`s GitHub at **image build**, so a Restart is not enough.

Leave Space secrets and `iloilo.net.xml` / `iloilo.rou.xml` alone.

## 1. Pull current `main`

```bash
git pull origin main
```

## 2. Factory reboot the Space

**UI:** Space → **Settings → Factory reboot** (Rebuild, not Restart).

**CLI** (if you have `HF_TOKEN` / are logged in):

```bash
pip install -q huggingface_hub
python -c "from huggingface_hub import HfApi; HfApi().restart_space('delatorrecj/matrix-api-backend', factory_reboot=True)"
```

Wait until status is **Running** and the SUMO baseline has seeded (~45 s). First simulate after reboot is a cold SUMO run.

## 3. Confirm

```bash
curl -sS https://delatorrecj-matrix-api-backend.hf.space/health
curl -sS -o /dev/null -w "%{http_code}\n" https://delatorrecj-matrix-api-backend.hf.space/credibility
```

Expect: `health` → `"status":"ok"` and `baseline` ok. `credibility` → **200** (it is 404 on the June image).

On the live app, run cockpit **School in Molo**. Plan should read **New facility · Molo · school · 3,000 seats**, not Lane closure.

## If Factory reboot still behaves like June

Docker cached the `git clone` layer. Bump the Space Dockerfile and push the **Space** repo (not GitHub `matrix`):

```bash
cd deploy/hf-space
# add a one-line ARG before the git clone, e.g. ARG CACHEBUST=c6466b4
git remote add space https://huggingface.co/spaces/delatorrecj/matrix-api-backend
git push space main
```

Then wait for the Space build to finish and re-run §3.
