# Sidequest

A personal gaming session recommendation web application answering: **What should I play right now, and what should I accomplish during this session?**

Sidequest will recommend game/goal pairs using a deterministic scoring engine and explain every score. It will also record play sessions for future analysis.

## Current status

Planning and directory scaffolding only. There is no runnable application, dependency manifest, database, or implemented API yet. The workspace was initially empty and was not a Git repository. Application implementation awaits plan review.

## Planned stack

- Python, FastAPI, SQLAlchemy, SQLite
- React, JavaScript, Vite
- pytest for meaningful backend and scoring checks

## Project layout

```text
backend/
  app/          # Future API, schemas, models, database, scoring modules
  tests/        # Future scoring and API/persistence tests
  data/         # Local SQLite database (ignored)
frontend/
  src/          # Future React screens and components
PROJECT.md      # Scope, architecture, model, scoring, acceptance criteria
IMPLEMENTATION_PLAN.md
```

## Eventual development setup

These are intended commands, not available functionality today. Python/package versions and manifests will be selected during implementation.

Backend (PowerShell, from the repository root):

```powershell
py -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
python -m pip install -r backend/requirements.txt
Set-Location backend
python -m uvicorn app.main:app --reload
```

Frontend (a separate PowerShell terminal, from the repository root):

```powershell
Set-Location frontend
npm install
npm run dev
```

The planned API runs at `http://127.0.0.1:8000`; Vite normally runs at `http://localhost:5173` and will proxy `/api` to FastAPI. Future backend checks run with `python -m pytest` from `backend/`; frontend build verification runs with `npm run build` from `frontend/`.

The SQLite database will live under `backend/data/`. It is personal local data and is excluded from source control. Schema initialization/migration and backup instructions will be added when persistence exists.

Read [PROJECT.md](PROJECT.md) and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) before implementation. Start with the scoring engine after the plan has been reviewed.
