# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to **Atlas Observatory (`atlas-observatory-ryan-vo`)** are documented in this file.

## [1.0.0] - 2026-10-15

### Added (Round 1 — `simulative-swarm-planner`)
- Created incremental roadmap (`feature-plan.json`, `PLAN.md`, and `STATUS.md`) tracking `simulative-swarm-planner` (`done`) and upcoming milestones (`witness-manifest-verifier`, `goap-action-planner`, `quantized-memory-benchmark`, `oidc-keycloak-rbac`, `advisory-llm-adapters`).
- Implemented FastAPI backend (`backend/app/main.py`) with transactional SQLite storage (`backend/app/core/database.py`), DAG topological critical-path analyzer and selective `SR²AM` simulative planning router (`backend/app/services/planner_engine.py`), and labeled 8-workload benchmark evaluator (`backend/app/services/benchmark_service.py`).
- Added REST endpoints under `/api/v1` for health checks, creating/listing/filtering/inspecting/exporting/deleting swarm plans, running labeled routing benchmarks, and querying audit logs (`backend/app/api/routes.py`).
- Built React + TypeScript + Vite workbench (`frontend/src/App.tsx`, `SwarmPlanForm.tsx`, `SwarmPlanDetail.tsx`, `BenchmarkPanel.tsx`) with a typed API client (`frontend/src/api/client.ts`).
- Added 13 backend pytest tests (`backend/tests/`) and 3 frontend Vitest integration tests (`frontend/src/App.test.tsx`).
