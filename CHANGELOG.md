# Changelog

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

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

### Added (Round 2 — `witness-manifest-verifier`)
- Implemented Release Artifact & Witness Manifest Integrity Verifier: platform manifest inspection (`macos`, `linux`, `windows`), SHA-256 artifact digest verification, and Ed25519 witness stamp validation per ruflo scheme.
- Three-state verification classification: `verified_clean` (all entries match), `drift_detected` (mismatches or mixed verified/missing), `unverifiable_missing_build` (all entries missing — explicit failure instead of soft-passing exit 0).
- Added `backend/app/services/witness_verifier.py`, `backend/app/models/witness.py`, and REST endpoints under `/api/v1/witness/*` in `backend/app/api/routes.py`.
- Built React workbench panel (`frontend/src/components/WitnessVerifierPanel.tsx`) with per-platform status, artifact detail tables, and witness stamp inspection.
- Added 12 backend unit tests (`backend/tests/test_witness_verifier.py`) and 3 API workflow tests (`backend/tests/test_api_workflows.py`) covering all three states and stamp verification.
- Extended typed frontend API client (`frontend/src/api/client.ts`) with witness verification methods.
