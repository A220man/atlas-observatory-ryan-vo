# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

simulative-swarm-planner

## Roadmap

### simulative-swarm-planner — Swarm Topology Analyzer & Selective Simulative Planning Router

Status: done

Acceptance:
- Compute DAG critical-path execution horizon and tool-call density for multi-agent task workflows
- Route workflows between selective simulative forward planning (SR2AM shadow pass) and direct reactive dispatch with deterministic token-budget savings estimates
- Evaluate hierarchical, mesh, ring, and star swarm topologies for communication edge overhead, agent role allocation, and parallel efficiency
- Persist swarm plans and audit log entries in SQLite with filtering, pagination, detail inspection, JSON export, and reproducible benchmark evaluation across labeled workloads
- Render a React + TypeScript dashboard connected to the FastAPI backend for creating, filtering, inspecting, exporting, and benchmarking swarm plans

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/models/swarm.py`, `backend/app/services/planner_engine.py`, `backend/app/services/benchmark_service.py`, `backend/app/services/swarm_repository.py`, `backend/app/api/routes.py`, `frontend/src/api/client.ts`, `frontend/src/App.tsx`, `frontend/src/components/SwarmPlanForm.tsx`, `frontend/src/components/SwarmPlanDetail.tsx`, `frontend/src/components/BenchmarkPanel.tsx`

Tests: `backend/tests/test_planner_engine.py`, `backend/tests/test_api_workflows.py`, `frontend/src/App.test.tsx`

### witness-manifest-verifier — Release Artifact & Witness Manifest Integrity Verifier

Status: planned

Acceptance:
- Inspect platform build manifests (macos, linux, windows) and verify SHA-256 artifact digests and Ed25519 witness stamps
- Explicitly distinguish verified_clean, drift_detected, and unverifiable_missing_build states when dist/ artifacts are absent instead of soft-passing with exit code 0

### goap-action-planner — Goal-Oriented Action Planning (GOAP) A* Search Engine

Status: planned

Acceptance:
- Synthesize minimum-cost executable agent action sequences from world-state preconditions and effects using deterministic A* search
- Persist and visualize synthesized GOAP action trees and state transitions

### quantized-memory-benchmark — Quantized Vector Memory & Temporal Staleness Evaluator

Status: planned

Acceptance:
- Compare float32, int8, and 1-bit RaBitQ vector quantization recall and memory footprint across agent memory namespaces
- Diagnose temporal staleness and interference aging across multi-session memory records

### oidc-keycloak-rbac — OIDC PKCE Authentication, Keycloak SAML Broker & Role-Based Access Control

Status: planned

Acceptance:
- Enforce OIDC Authorization Code + PKCE token verification with viewer, operator, and admin role guards on all API endpoints
- Provide Keycloak realm configuration for upstream SAML identity brokering and guarded local demo mode

### advisory-llm-adapters — Opt-In Advisory LLM Critique Adapters

Status: planned

Acceptance:
- Support server-side LLM_API_KEY adapters for OpenAI-compatible, Anthropic Messages, and Gemini generateContent APIs
- Generate grounded advisory critiques of swarm plans without fabricating responses when credentials are absent

