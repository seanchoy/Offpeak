# Offpeak — Manhattan Trip Itinerary Planner 🗽🧭

<p align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=python,fastapi,postgres,react,ts,vite,swift,docker,githubactions,figma&theme=light" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/status-live-brightgreen.svg" alt="Status: Live" />
  <img src="https://img.shields.io/badge/COMP47360-Research%20Project-blue.svg" alt="COMP47360 Research Project" />
  <a href="https://offpeak.seancai.dev/"><img src="https://img.shields.io/badge/website-offpeak.seancai.dev-orange.svg" alt="Website" /></a>
</p>

## 🌟 Project Overview

**Offpeak** is a trip itinerary planner web and mobile application built for tourists visiting Manhattan, New York. The central problem it addresses is the uncertainty visitors face when planning a day out: which attractions will be overcrowded, when is the best time to visit each one, and how to build a realistic multi-stop itinerary around that.

Offpeak solves this by combining a curated Points-of-Interest (POI) database for Manhattan with a machine-learning busyness prediction model, letting users generate and save personalised itineraries that account for predicted crowd levels, accessibility needs, and trip dates.

An **AI Planner** sits on top: visitors can describe what they are after in their own words ("somewhere quiet to watch birds") and get recommendations retrieved from Offpeak's own catalogue (RAG), then turn the conversation into a crowd-aware itinerary. The assistant is a Gemini tool-calling agent; recommendations come only from places Offpeak has data for.

> Development continues in this fork ([seanchoy/Offpeak](https://github.com/seanchoy/Offpeak)) after the COMP47360 project: RAG-based recommendations, the tool-calling planner, Google sign-in, and self-hosted CI/CD.

<p align="center">
  <img src="docs/images/web-explore.png" alt="Offpeak web app — Explore" width="95%" />
  <br />
  <em>Web interface - Explore </em>
</p>
<p align="center">
  <img src="docs/images/mobile-explore-ai-planner-poi.png" alt="Offpeak iOS app — Explore, AI Planner, and POI detail" width="60%" />
  <br />
  <em>Native iOS interface — Explore, AI Planner, and POI detail</em>
</p>

🌏 Website: https://offpeak.seancai.dev/

---

## 📋 Table of Contents

<details open>
  <summary>Table of Contents</summary>

  - [👩‍💻🧑‍💻 Group Members](#-group-members)
  - [📑 Team Documents](#-team-documents)
  - [✨ Features](#-features)
  - [🧰 Technology Stack](#-technology-stack)
  - [🧠 Machine Learning / Busyness Prediction](#-machine-learning--busyness-prediction)
  - [🚀 Getting Started](#-getting-started)
    - [💾 Prerequisites](#-prerequisites)
    - [🔧 Backend Setup](#-backend-setup)
    - [🎨 Frontend Setup](#-frontend-setup)
    - [📱 iOS Setup](#-ios-setup)
  - [🧪 Testing](#-testing)
  - [📂 Repository Layout](#-repository-layout)
  - [🌐 Deployment](#-deployment)
  - [📎 Supporting Material](#-supporting-material)
  - [🤝 Contributing](#-contributing)
  - [📝 License](#-license)
</details>

---

## 👩‍💻🧑‍💻 Group Members

- Yu Ning Chen (@Nancyuning)
- Hansel Oduah (@hansel-3)
- Eoin Conroy (@conroy96)
- Shida Cai (@Seanchoy)
- Fan Chi Meng (@alisonmeng)

> Developed as part of the **COMP47360** Research Project.

---

## 📑 Team Documents

- [Deployment Guide](DEPLOYMENT.md)
- [Git Workflow](git-workflow.md)
- [Machine Learning / Data](ml/README.md)
- [POI Column Dictionary](backend/db/poi_column_dictionary.md)
- [Project Management (backlog, budget, timeline)](docs/project-management/) — see [Supporting Material](#-supporting-material)

---

## ✨ Features

The app is organised into five tabs, available on both web and mobile:

- **🧭 Explore** — Browse and search Manhattan points of interest. Each POI card shows a photo, name, neighbourhood, rating, crowd level, and a best-time-to-visit hint, plus an accessibility icon (♿) where applicable. Tapping a card opens its detail page, with a 6-slot Crowd Forecast chart (colour-coded Quiet / Moderate / Busy), a "Best Time to Visit" window, and an accessibility section shown by default, listing confirmed wheelchair or step-free access and otherwise linking to the venue's own site.
- **🤖 AI Planner** — A conversational planner with two jobs:
  - **Find places:** ask in natural language ("rainy-day art, somewhere quiet") and the assistant searches Offpeak's catalogue by meaning, answering only with places it found. Each recommended place appears as a card that opens its detail page.
  - **Plan a trip:** the assistant collects a trip name, dates and pace, then shows selectors for the place types you prefer and want to avoid. On confirmation it builds a crowd-aware itinerary (with a photo cover and crowd forecast for each stop) that can be saved — saving the same itinerary twice keeps one copy — or opened in My Itinerary.
  - Your wheelchair setting always applies to searches, and the conversation survives a page refresh until you start again or log out.
- **🗓️ My Itinerary** (manual, main flow) — Pick POIs and trip dates directly; the system auto-schedules them into a time-slotted itinerary based on predicted crowd level and location, prioritising Quiet/Moderate slots where possible. Stops can be removed, with the schedule reflowing automatically.
- **🔖 Saved** — POIs can be saved straight from Explore (no itinerary needed) and appear here immediately; saved itineraries can also be reopened in full or deleted.
- **👤 Profile** — Account info (username, joined date) and an accessibility setting (e.g. step-free routes). When enabled, itineraries are restricted to POIs with *confirmed* wheelchair access; places with only partial access, or with no accessibility data, are left out and a warning is shown if you add one anyway.

---

## 🧰 Technology Stack

- **Backend:** [Python](https://www.python.org/) — [FastAPI](https://fastapi.tiangolo.com/) (REST API), [SQLAlchemy](https://www.sqlalchemy.org/) (ORM), [Alembic](https://alembic.sqlalchemy.org/) (database migrations)
- **Database:** [PostgreSQL](https://www.postgresql.org/) with [PostGIS](https://postgis.net/) and [pgvector](https://github.com/pgvector/pgvector)
- **AI / LLM:** [Gemini API](https://ai.google.dev/) — tool calling, structured output and embeddings; RAG over the POI catalogue with pgvector
- **Frontend (Web):** [React](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) + [Vite](https://vitejs.dev/)
- **Mobile:** Native iOS ([Swift](https://developer.apple.com/swift/) + [SwiftUI](https://developer.apple.com/swiftui/))
- **Machine Learning:** [Python](https://www.python.org/), [Pandas](https://pandas.pydata.org/), [DuckDB](https://duckdb.org/)
- **Design / Mockups:** [Figma](https://www.figma.com/), [Stitch](https://stitch.withgoogle.com/)
- **Deployment:** [Docker Compose](https://docs.docker.com/compose/) on a [DigitalOcean](https://www.digitalocean.com/) Droplet behind [Caddy](https://caddyserver.com/); images on GHCR, shipped by [GitHub Actions](https://github.com/features/actions)

---

## 🧠 Machine Learning / Busyness Prediction

Offpeak's crowd forecasts come from a busyness model built on a curated Manhattan POI registry plus public demand signals (transit, taxi, Citi Bike, pedestrian counts, weather, holidays). The target is **Google Popular Times** — a 0–100 score normalised to each place's own typical peak — modelled as a typical-week (day-of-week × hour) profile that the backend serves as the crowd forecast.

The datasets and DB seed that power this live in [`ml/`](ml/README.md).

---

## 🚀 Getting Started

### 💾 Prerequisites

- [Docker](https://www.docker.com/) (recommended: runs Postgres with PostGIS and pgvector, migrations and the API for you)
- *or, without Docker:* Python 3.12 and `pip`, plus PostgreSQL with the **PostGIS** and **pgvector** extensions
- Node.js and `npm`
- A [Gemini API key](https://ai.google.dev/) (the AI Planner and the search index need it)
- Xcode (for iOS development) — iOS 26

### 🔧 Backend Setup
> For the backend specific guide, see [Backend README](backend/README.md).

Backend code resides in the `backend/app` folder:

- FastAPI application entry point: `backend/app/main.py`
- API endpoint definitions: `backend/app/routers/`
- Database connection code: `backend/app/database.py`

#### Option A — Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env       # then fill in JWT_SECRET_KEY and GEMINI_API_KEY
echo "POSTGRES_PASSWORD=choose-a-password" > .env

docker compose up -d --build                         # Postgres (PostGIS + pgvector) → migrations → API
docker compose --profile seed run --rm seed          # load the POI data (fresh database only)
docker compose run --rm api python -m app.scripts.embed_pois   # build the search index for the AI Planner
```

The API runs at [http://localhost:8000](http://localhost:8000) (docs at `/docs`). Re-run `embed_pois` after POI descriptions change; it only re-embeds places whose text changed.

#### Option B — Run it yourself

**1. Install dependencies**

```bash
cd backend
pip install -r requirements.txt
```

**2. Create your `.env` file**

A `.env.example` template file is provided inside `/backend`. Copy it to `.env` and fill in your own values. Never commit `.env` to GitHub.

**3. Set up a local PostgreSQL database**

The database needs the **PostGIS** and **pgvector** extensions installed on the server (the migrations run `CREATE EXTENSION`, which fails if pgvector is missing). Create a database, either via a GUI, or in the terminal:

```bash
psql postgres
```
```sql
CREATE DATABASE database_name;
\c database_name   -- connects to the database
\q                 -- quits the connection
```

**4. Connect PostgreSQL to FastAPI**

In your `.env`, add your database URL:

```
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/database_name
```

Replace `username`, `password`, port (usually `5432`), and `database_name` with your actual values. All settings are read from `.env` by `backend/app/core/config.py`, so no code changes are needed.

**5. Run database migrations (Alembic)**

Alembic is installed via `requirements.txt` and manages the tables defined in `backend/app/models/`.

```bash
git pull origin main
cd backend
alembic upgrade head
```

Run this command whenever the team announces a database change, then verify the new tables/columns exist.

**6. Seed the database**

Run the following seed scripts **in order**:

```bash
cd backend/db
psql -d your_database_name -f 03_dml_seed_poi_table.sql
psql -d your_database_name -f 04_dml_seed_busyness_forecast.sql
psql -d your_database_name -f 05_insert_poi_availability_mode.sql
psql -d your_database_name -f 06_dml_update_poi_best_time.sql
psql -d your_database_name -f 07_dml_update_poi_content.sql
```

**7. Build the search index**

The AI Planner's recommendations search POI embeddings. Generate them once (needs `GEMINI_API_KEY`):

```bash
cd backend
python -m app.scripts.embed_pois
```

**8. Run FastAPI**

For web development (paired with the React frontend):

```bash
cd backend
uvicorn app.main:app --reload
```

FastAPI will run at [http://localhost:8000](http://localhost:8000), with interactive endpoint docs at [http://localhost:8000/docs](http://localhost:8000/docs). The Vite dev server proxies `/api` to this address, so the web app needs no CORS setup.

For mobile development (so a physical device on the same network can reach it):

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- iOS Simulator → call the backend at `http://localhost:8000`.
- Physical iPhone → call the backend at `http://YOUR_MAC_IP:8000`, with the Mac and iPhone on the same Wi-Fi network.

### 🎨 Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The web app should now be running at `http://localhost:5173`.

### 📱 iOS Setup

> For more iOS specific guide — see the [iOS README](ios/README.md).

Build and run the **Offpeak** iOS app in the Xcode **iOS Simulator** on a Mac.
No physical device or Apple Developer account is required.

> **Assumption:** your backend is successfully set up and running locally.
> For Backend setup, please refer to the top-level of this section if you need it.

---

#### 1. Prerequisites

| Requirement | Version / Notes |
|---|---|
| macOS | Recent enough to run Xcode 26 |
| **Xcode** | **26 or newer** — the app targets **iOS 26.0** |
| iOS Simulator runtime | **iOS 26.0**  |

> Check with `xcodebuild -version`. If the iOS 26 simulator is missing, install it
> from **Xcode - Settings - Components - Platform Support**.

---

#### 2. Get the code & open the project

```bash
git clone https://github.com/seanchoy/Offpeak.git
cd Offpeak/ios
open ManhattanTravelApp.xcodeproj
```

*(Already have the repo? Just `git pull origin main`.)*

- Scheme: **ManhattanTravelApp**
- Bundle identifier: `com.sean.offpeak`

---

#### 3. Confirm the backend URL

A Debug build already points at default local backend, change accordingly if needed.
see `ManhattanTravelApp/Core/Networking/APIConfig.swift`:

```swift
#if DEBUG
static let baseURL = URL(string: "http://127.0.0.1:8000")! // change accordingly
#endif
```

---

#### 4. Select a simulator and run

1. In Xcode's toolbar (top center), open the run-destination dropdown.
2. Choose any **iPhone** simulator on **iOS 26** (e.g. *iPhone 17 Pro*).
3. Press **⌘R** (or the ▶️ Run button).

Xcode builds, boots the simulator, installs, and launches automatically. The
first build takes a little longer while it compiles from scratch.

**Command-line alternative** (build without launching):

```bash
xcodebuild build \
  -scheme ManhattanTravelApp \
  -project ManhattanTravelApp.xcodeproj \
  -destination 'generic/platform=iOS Simulator' \
  -configuration Debug
```

---

#### 5. Verify it works

- **Explore** loads a list of Manhattan POIs with photos.
- Tapping a card opens the detail page with a crowd-forecast chart.
- Sign up / log in, then check Saved and Itinerary.

---

#### 6. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Explore is empty or shows a network error | Backend not reachable. Confirm server is running. |
| "iOS 26.0 is not installed" / no matching destination | Install the iOS 26 runtime: **Xcode - Settings - Components**. |
| Build fails on an old Xcode | The project targets iOS 26 — update to **Xcode 26+**. |
| Photos don't load | Usually transient network; images cache to disk after first load, so a second launch shows them instantly. |
| Can't log in | No user in your local DB yet, sign up first. |

---

## 🧪 Testing

**Backend** — a [pytest](https://docs.pytest.org/) suite. Gemini is never called: a scripted fake model stands in for it.

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt   # requirements-dev.txt adds pytest and ruff
python -m pytest
```

| Tests | What they cover |
|---|---|
| `tests/test_scheduler.py`, `test_find_best_slot.py`, `test_overflow.py`, `test_utils.py` | the itinerary scheduling engine: day/slot assignment, the quietest-open-slot rule, the overflow cost model (70% busyness / 30% geography), POI-per-day distribution |
| `tests/test_accessibility.py` | the wheelchair-confirmed-only accessibility filter |
| `tests/rag/` | the embedding table, POI documents and incremental indexing, retrieval with filters, hybrid ranking and the retrieval metrics (recall@k, MRR) |
| `tests/planner/`, `test_planner_guards.py`, `test_trip_state.py` | the AI Planner: the search tool's declaration and argument checks, the tool loop, the chat turn, and the fallbacks when the model skips a step |
| `test_itinerary_save.py`, `test_google_*.py`, `test_users_me.py`, `test_photo_attribution.py`, `test_poi_profile.py` | saving itineraries, Google sign-in, the user profile, photo credits and POI profiles |

Tests that need a real database (with pgvector) are skipped unless `TEST_DATABASE_URL` points to a **disposable** Postgres — they drop and recreate their tables.

To measure retrieval quality against the golden set: `docker compose run --rm api python -m app.scripts.eval_retrieval`.

**Web frontend** — [Vitest](https://vitest.dev/) and Testing Library:

```bash
cd frontend
npm test
```

CI ([`ci.yml`](.github/workflows/ci.yml)) runs on every push and pull request: backend `ruff`, an import smoke test and `pytest`; frontend lint and build.

> The iOS client does not yet have automated tests.

---

## 📂 Repository Layout

| Folder | Purpose |
|---|---|
| `backend/` | FastAPI + SQLAlchemy API and Postgres schema (Alembic migrations in `backend/alembic/`, seed SQL in `backend/db/`). |
| `frontend/` | Vite / React / TypeScript web client. |
| `ios/` | Native iOS client. |
| `ml/` | **Data / ML side** — intermediate & processed datasets and the POI DB seed that power the busyness feature. See [`ml/README.md`](ml/README.md). |

---

## 🌐 Deployment

Offpeak is live at **[https://offpeak.seancai.dev/](https://offpeak.seancai.dev/)**, self-hosted on a single [DigitalOcean](https://www.digitalocean.com/) Droplet with Docker Compose:

- **Edge:** [Caddy](https://caddyserver.com/) terminates TLS and routes `/api/*` to the API and everything else to the web container, so the web app and API share one origin.
- **Web:** the Vite build served by Caddy in its own container (`ghcr.io/seanchoy/offpeak-web`).
- **API:** FastAPI (`ghcr.io/seanchoy/offpeak-api`); a one-shot `migrate` container runs `alembic upgrade head` before it starts.
- **Database:** PostgreSQL 18 with PostGIS and pgvector, in a container with a persistent volume.
- **CI/CD:** when CI passes on `main`, [`deploy.yml`](.github/workflows/deploy.yml) builds both images, pushes them to GHCR tagged with the commit SHA, and over SSH tells the server to pull them and restart (`docker compose pull && up -d`).

> [DEPLOYMENT.md](DEPLOYMENT.md) describes the original course deployment (Cloud Run, Neon and Vercel on `offpeak.live`).

### 🔑 Environment variables

The backend reads the variables below (template: [`backend/.env.example`](backend/.env.example)). Locally they live in `backend/.env`; in production they live in a `.env` file on the server, outside the repository and the images.

| Variable | Purpose | Required |
|---|---|---|
| `DATABASE_URL` | Postgres connection string | yes |
| `JWT_SECRET_KEY` | signs auth tokens | yes |
| `GEMINI_API_KEY` | Gemini — chat, tool calling and embeddings | yes |
| `GEMINI_PROXY_URL`, `GEMINI_PROXY_RETRIES` | route Gemini through a proxy (one URL or a comma-separated list) and retry across them | optional |
| `GOOGLE_PLACES_API_KEY` | POI photos; the photo endpoint returns 404 if unset | optional |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google sign-in; its routes return 503 if unset | optional |
| `PUBLIC_API_URL` | absolute base for photo links handed to clients | optional |
| `ALLOWED_ORIGINS` | browser CORS allowlist | optional¹ |
| `ENABLE_QUERY_COUNTER` | adds an `X-Query-Count` header per request, for performance work; keep off in production | optional |
| `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | auth-token settings; have code defaults | optional |

¹ Production doesn't depend on CORS — the web app and API share one origin behind Caddy, and iOS is native.

The Docker Compose setup also reads `POSTGRES_PASSWORD` from a `.env` file in the repository root.

---

## 📎 Supporting Material

### 📊 Project Management

The project-management artifacts live in **[`docs/project-management/`](docs/project-management/)**:

- **Product backlog & sprint backlog** — the per-task breakdown across Sprints 1–5
- **Timeline** — sprint schedule and a per-person Gantt
- **Budget** — planned vs actual hours and cost, with a 30% buffer
- **Burndown charts & timesheets** — one burndown per sprint

See the [folder README](docs/project-management/README.md) for a summary, or open the full workbook [`Sprint_Backlog_and_Budget.xlsx`](docs/project-management/Sprint_Backlog_and_Budget.xlsx) (Summary · Backlog · Burndown · Gantt · Budget tabs).

### 🎨 Design & Mockups

Design mockups for the mobile and web clients. These are **product drafts only**, indicating that the UI shifted considerably over the course of development, so they may not match the final product. They are included to give an intuitive sense of what the product is; the shipped web and iOS clients are the source of truth.

**📱 Mobile (iOS)**

| Version | Tool | Link |
|---|---|---|
| v1 | Figma Make | [Mobile mockup — v1](https://www.figma.com/make/Wy0N0YTlQOuGQF3VM3zpON/Mobile?code-node-id=0-9&p=f&t=VQL2LLW06JQlqGgr-0&fullscreen=1) |
| v2 | Figma | [Mobile mockup — v2](https://www.figma.com/design/JyAbBv5QKWtzuI1hCzXgCP/html.to.design-%E2%80%94-by-%E2%80%B9div%E2%80%BARIOTS-%E2%80%94-Import-websites-to-Figma-designs--web-html-css---Community-?node-id=0-1&t=OF2hU1V1JeuWJarb-1) |

**💻 Web**

| Tool | Link |
|---|---|
| Google Stitch | [Web mockup](https://stitch.withgoogle.com/projects/6161260565705765353) |

> Note: these links point at Figma / Stitch projects and may require the relevant sharing permissions to open — please contact the team for access if needed.

---

## 🤝 Contributing

We follow a branch-and-PR workflow — see the [Git Workflow](git-workflow.md) for the full details.

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Commit your changes:
   ```bash
   git commit -m "Add your awesome feature"
   ```
3. Push to the branch:
   ```bash
   git push origin feature/your-feature-name
   ```
4. Open a pull request. 🚀

---

## 📝 License

This project is licensed under the [MIT License](LICENSE) — see the `LICENSE` file for details. Developed as part of the **COMP47360** Research Project at University College Dublin.
