# Deployment on Render (free plan)

`render.yaml` defines four free web services in one Render project.

| Environment | Service | Role | Branch | URL |
|---|---|---|---|---|
| dev | `fraud-dashboard-api-dev` | FastAPI backend | `dev` | https://fraud-dashboard-api-dev.onrender.com |
| dev | `fraud-dashboard-ui-dev` | Streamlit frontend | `dev` | https://fraud-dashboard-ui-dev.onrender.com |
| prod | `fraud-dashboard-api-prod` | FastAPI backend | `main` | https://fraud-dashboard-api-prod.onrender.com |
| prod | `fraud-dashboard-ui-prod` | Streamlit frontend | `main` | https://fraud-dashboard-ui-prod.onrender.com |

## Environment variables

All values are set in `render.yaml`. The project uses no secrets.

| Variable | Used by | Purpose |
|---|---|---|
| `APP_ENV` | both | `dev` or `prod`. The frontend refuses to run if the backend reports a different value. |
| `BACKEND_URL` | frontend | Public URL of the backend in the same environment. |
| `PYTHON_VERSION` | both | Python version Render installs. |

`BACKEND_URL` is a literal public URL on purpose. Free services cannot receive
private network traffic, and `fromService` only provides private hostnames.

## First deployment

`render.yaml` must be on `main` and the `dev` branch must exist on GitHub.

1. In the Render Dashboard choose **New > Blueprint**.
2. Connect `AmitEliaQ/fraud-dashboard` and select the `main` branch.
3. Confirm that the review screen lists four services on the Free plan, then apply.
4. Wait for the four deploys to finish, then run the health checks below.
5. Check that each backend got the hostname in the table. If Render added a suffix,
   update `BACKEND_URL` in `render.yaml` and merge the change to `main`.

Validate changes to the Blueprint with `render blueprints validate render.yaml`.

## Promoting a change

1. Push to `dev`. The dev services deploy automatically.
2. Run the dev health checks.
3. Open a pull request from `dev` to `main`. Merging deploys prod.

Render reads `render.yaml` from `main`, so Blueprint changes apply only after they
reach `main`. Code changes on `dev` deploy straight away.

## Health checks

A sleeping service takes about a minute to answer, so allow for it with `--max-time`.

```bash
for env in dev prod; do
  curl -s --max-time 120 "https://fraud-dashboard-api-$env.onrender.com/health"; echo
  curl -s --max-time 120 "https://fraud-dashboard-ui-$env.onrender.com/_stcore/health"; echo
done
```

Expected results:

- Backend: HTTP 200 with `{"status":"ok","environment":"<env>","rows":10000}`.
- Frontend: HTTP 200 with `ok`.

Then open each frontend URL. The banner should show `ENV :: DEV` or `ENV :: PROD`,
and the KPI row should show 10,000 transactions with 151 fraud cases and no filters.

## Free plan limits

- Services sleep after 15 minutes without traffic and take about a minute to wake.
  A first visit can take up to about two minutes, because the frontend wakes first
  and then the backend. The frontend waits and retries.
- The workspace gets 750 instance hours a month, shared by all four services. Hours
  are used only while a service is awake, so do not add a keep-alive pinger.
- Each service has 0.1 CPU and 512 MB of RAM. Render may restart a free service at
  any time.
- The backend has no authentication. It is read-only and serves the same data that
  is public in this repository.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `BACKEND_UNAVAILABLE` | Backend is down, or `BACKEND_URL` is wrong | Check the backend logs and its real hostname in the Dashboard |
| `ENVIRONMENT_MISMATCH` | Frontend points at the other environment's backend | Correct `BACKEND_URL` in `render.yaml` |
| Blueprint sync fails on `dev` | The `dev` branch is missing on GitHub | Push `dev` and sync again |
| Long wait on the first visit | The services were asleep | Expected on the free plan |

## Running locally

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest

(cd backend && uvicorn main:app --port 8000)
(cd frontend && streamlit run app.py)    # in a second terminal
```

If port 8000 is taken, start the backend on another port and set `BACKEND_URL` for the
frontend. See `.env.example` for the variables.
