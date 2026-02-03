# Climate Burden Index (CBI) System

A production-ready platform for quantifying environmental inequity at the U.S. census-tract level.

This repository contains the full pipeline: ETL → Feature Engineering → ML (clustering + supervised) → PostGIS database → FastAPI backend → Next.js frontend, plus orchestration (Airflow), Docker deployment, and comprehensive documentation.

Quick start: see `START_HERE.md` and `QUICKSTART.md` for 30-second launch instructions and step-by-step development guides.

Primary docs:
- `START_HERE.md` — Read first, high-level overview.
- `QUICKSTART.md` — Fast path to run locally with Docker Compose.
- `API_DOCS.md` — API endpoints, request/response examples.
- `DATA_DICTIONARY.md` — Full feature descriptions and schema.
- `ML_CARD.md` — Model performance, fairness, limitations.
- `DEPLOYMENT_GUIDE.md` — Production deployment steps (AWS/GCP/Azure).

For development, run the test suite and follow the QUICKSTART instructions.
