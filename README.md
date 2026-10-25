# Offpeak — Manhattan Trip Itinerary Planner 🗽🧭

<p align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=python,fastapi,postgres,react,ts,vite,npm,swift,git,figma&theme=light" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/status-live-brightgreen.svg" alt="Status: Live" />
  <img src="https://img.shields.io/badge/COMP47360-Research%20Project-blue.svg" alt="COMP47360 Research Project" />
  <a href="https://offpeak.seancai.dev/"><img src="https://img.shields.io/badge/website-offpeak.live-orange.svg" alt="Website" /></a>
</p>

## 🌟 Project Overview

**Offpeak** is a trip itinerary planner web and mobile application built for tourists visiting Manhattan, New York. The central problem it addresses is the uncertainty visitors face when planning a day out: which attractions will be overcrowded, when is the best time to visit each one, and how to build a realistic multi-stop itinerary around that.

Offpeak solves this by combining a curated Points-of-Interest (POI) database for Manhattan with a machine-learning busyness prediction model, letting users generate and save personalised itineraries that account for predicted crowd levels, accessibility needs, and trip dates.

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
- **🤖 AI Planner** — A conversational planner: the assistant asks whether you're starting a new trip or refining an existing one in My Itinerary, then gathers trip dates, interests, and accessibility needs through dialogue. Once confirmed, the generated itinerary is saved into My Itinerary.
- **🗓️ My Itinerary** (manual, main flow) — Pick POIs and trip dates directly; the system auto-schedules them into a time-slotted itinerary based on predicted crowd level and location, prioritising Quiet/Moderate slots where possible. Stops can be removed, with the schedule reflowing automatically.
- **🔖 Saved** — POIs can be saved straight from Explore (no itinerary needed) and appear here immediately; saved itineraries can also be reopened in full or deleted.
- **👤 Profile** — Account info (username, joined date) and an accessibility setting (e.g. step-free routes). When enabled, itineraries are restricted to POIs with *confirmed* wheelchair access; places with only partial access, or with no accessibility data, are left out and a warning is shown if you add one anyway.

---

## 🧰 Technology Stack

- **Backend:** [Python](https://www.python.org/) — [FastAPI](https://fastapi.tiangolo.com/) (REST API), [SQLAlchemy](https://www.sqlalchemy.org/) (ORM), [Alembic](https://alembic.sqlalchemy.org/) (database migrations)
- **Database:** [PostgreSQL](https://www.postgresql.org/)
- **Frontend (Web):** [React](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) + [Vite](https://vitejs.dev/)
- **Mobile:** Native iOS ([Swift](https://developer.apple.com/swift/) + [SwiftUI](https://developer.apple.com/swiftui/))
- **Machine Learning:** [Python](https://www.python.org/), [Pandas](https://pandas.pydata.org/), [DuckDB](https://duckdb.org/)
- **Design / Mockups:** [Figma](https://www.figma.com/), [Stitch](https://stitch.withgoogle.com/)
- **Deployment:** Backend on [Google Cloud Run](https://cloud.google.com/run), database on [Neon](https://neon.tech/), frontend on [Vercel](https://vercel.com/)

---

## 🧠 Machine Learning / Busyness Prediction

Offpeak's crowd forecasts come from a busyness model built on a curated Manhattan POI registry plus public demand signals (transit, taxi, Citi Bike, pedestrian counts, weather, holidays). The target is **Google Popular Times** — a 0–100 score normalised to each place's own typical peak — modelled as a typical-week (day-of-week × hour) profile that the backend serves as the crowd forecast.

The datasets and DB seed that power this live in [`ml/`](ml/README.md).

---

## 🚀 Getting Started

### 💾 Prerequisites

- Python 3.x and `pip`
- Node.js and `npm`
- PostgreSQL (installed locally, or a GUI client such as [DBeaver](https://dbeaver.io/) or [pgAdmin](https://www.pgadmin.org/))
- Xcode (for iOS development) — iOS 26

### 🔧 Backend Setup
> For the backend specific guide, see [Backend README](backend/README.md).

Backend code resides in the `backend/app` folder:

- FastAPI application entry point: `backend/app/main.py`
- API endpoint definitions: `backend/app/routers/`
- Database connection code: `backend/app/database.py`

**1. Install dependencies**

```bash
cd backend
pip install -r requirements.txt
```

**2. Create your `.env` file**

A `.env.example` template file is provided inside `/backend`. Copy it to `.env` and fill in your own values. Never commit `.env` to GitHub.

**3. Set up a local PostgreSQL database**

Create a database, either via a GUI, or in the terminal:

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

Replace `username`, `password`, port (usually `5432`), and `database_name` with your actual values. `backend/app/database.py` reads this variable via `os.getenv("DATABASE_URL")` — no code changes needed if your `.env` variable name matches.

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

**7. Run FastAPI**

For web development (paired with the React frontend):

```bash
cd backend
uvicorn app.main:app --reload
```

FastAPI will run at [http://localhost:8000](http://localhost:8000), with interactive endpoint docs at [http://localhost:8000/docs](http://localhost:8000/docs). Make sure the CORS middleware in `main.py` allows requests from `http://localhost:5173` (the default Vite dev server address) so the frontend can reach the backend.

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
git clone https://github.com/comp47360-team8/manhattan-travel-app.git
cd manhattan-travel-app/ios
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

The backend has a [pytest](https://docs.pytest.org/) suite for the **itinerary scheduling engine** — the app's core algorithm. The tests are pure-logic (no database or network), so they're fast and deterministic.

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt   # requirements-dev.txt adds pytest
python -m pytest
```

They run automatically in CI on every push and pull request (see [`ci.yml`](.github/workflows/ci.yml)).

| Test file | What it covers |
|---|---|
| `tests/test_scheduler.py` | day/slot assignment, closed-POI handling, overflow, and warnings (integration-style) |
| `tests/test_find_best_slot.py` | the "busyness-first" rule that places each POI in its quietest open slot |
| `tests/test_overflow.py` | the overflow cost model (70% busyness / 30% geography) |
| `tests/test_accessibility.py` | the wheelchair-confirmed-only accessibility filter |
| `tests/test_utils.py` | POI-per-day distribution and day-of-week range helpers |

> The web frontend and iOS client do not yet have automated tests.

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

Offpeak is live at **[https://offpeak.live/](https://offpeak.live/)**. See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the full hosting architecture, DNS, and CI/CD.

- **Frontend:** React + Vite static build on [Vercel](https://vercel.com/) — `offpeak.live`.
- **Backend:** FastAPI on [Google Cloud Run](https://cloud.google.com/run) (`us-west1`) — reached at `api.offpeak.live`.
- **Database:** PostgreSQL + PostGIS on [Neon](https://neon.tech/) (US West).
- **CI/CD:** merging `main` → `production` triggers GitHub Actions ([`deploy.yml`](.github/workflows/deploy.yml)) to run migrations, deploy the backend to Cloud Run, and deploy the frontend to Vercel.

### 🔑 Environment variables

The backend reads the variables below (template: [`backend/.env.example`](backend/.env.example)). Locally they live in `backend/.env`; in production they are set on Cloud Run — sensitive ones via **GCP Secret Manager**, the rest as plain env vars.

| Variable | Purpose | Required |
|---|---|---|
| `DATABASE_URL` | Postgres connection string (pooled in prod) | yes |
| `JWT_SECRET_KEY` | signs auth tokens | yes |
| `GEMINI_API_KEY` | Gemini — primary LLM | yes |
| `GROQ_API_KEY` | Groq / Llama — fallback LLM | yes |
| `AI_PROVIDER` | LLM strategy; `fallback` = Gemini with Groq fallback | yes |
| `GOOGLE_PLACES_API_KEY` | POI photos; endpoint returns none if unset | optional |
| `ALLOWED_ORIGINS` | browser CORS allowlist | optional¹ |
| `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | auth-token settings; have code defaults | optional |

¹ Production doesn't depend on CORS — the web app is same-origin via the Vercel rewrite and iOS is native.

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
