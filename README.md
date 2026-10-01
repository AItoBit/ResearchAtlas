# ResearchAtlas

**Mathematical research system with verifiable evidence.**

ResearchAtlas maps a mathematical question: what can be proved, what is false, what evidence exists, and what remains to be understood. Proofs, counterexamples, and refined questions are products of the same process.

This repository is an MVP. It is not an attempt to reproduce any private system. The first campaign is a **small, complete, auditable** calibration run in finite combinatorics.

## What it does

A **campaign** is the unit of work. It is bounded by a mathematical domain, a central question, an initial corpus, experimental tools, a budget, and stop criteria.

The system delivers:

| Deliverable | Content |
|---|---|
| Result map | Claims, hypotheses, dependencies, verification status |
| Reproducible experiments | Code, inputs, seeds, versions, results |
| Counterexamples | Concrete objects with independent checks |
| Candidate proofs | Structured arguments with explicit dependencies |
| Formal proofs | Lean files accepted by a pinned toolchain (when `lake` is available) |
| Obstacle log | Failed attempts, cause, and the scope of the failure |
| Frontier report | Established results, gaps, and next experiments |

**Out of scope for this MVP**

- Investigating arbitrary mathematics without a domain pack
- Claiming originality because a model does not recall prior work
- Promoting numerical or bounded evidence to a universal proof
- Publishing results automatically
- Training models or running large agent swarms

The first system uses **one sequential worker**. Agents propose; verifiers produce evidence; system rules control state changes.

## Architecture

```text
Human → campaign config → frontier planner → work loop
                              ↑                ↓
                         report ← graph ← knowledge loop ← verifiers
```

- **Work loop:** read, experiment, build examples, conjecture, search for proofs.
- **Knowledge loop:** record what the material actually supports, detect conflicts, version claims, update the frontier.
- **Planner:** an explainable priority queue connecting the two loops.

### Knowledge model

Nodes: `Claim`, `Definition`, `Source`, `ProofAttempt`, `Experiment`, `Example`, `Verification`, `Obstacle`, `Question`.

Relations: `uses`, `supports`, `refutes`, `generalizes`, `specializes`, `equivalent_to`, `derived_from`, `blocks`, `verified_by`. Every edge has provenance. A `refutes` edge must name both the counterexample and the exact statement version.

Research status and evidence level are independent:

| Dimension | Values |
|---|---|
| Research status | proposed, active, open, established, refuted, archived |
| Evidence level | none, heuristic, experiment, bounded_enumeration, reviewed_proof, formal_proof |

A conjecture may have millions of checked cases and still be **open**. A bounded exhaustive check records the finite universe it covers and why the enumeration is complete. A formalization records whether the Lean statement faithfully represents the informal claim.

Important edits are **versioned**. If a conjecture is false and a hypothesis is added, the system creates a new version (or a derived claim). The refuted record is kept.

## Calibration campaign: handshaking lemma

Domain pack: finite undirected simple graphs.

Path exercised by the sequential worker:

1. **Question** — what constraints hold on vertex degrees?
2. **Experiment** — enumerate all labeled graphs on 1 vertex.
3. **Conjecture** — every finite simple graph has an even-degree vertex (false).
4. **Counterexample** — `K2`, degrees `[1, 1]`, checked independently.
5. **Corrected claim** — the number of odd-degree vertices is even.
6. **Bounded enumeration** — all labeled graphs on `n ≤ 5`; two checkers must agree; this is **not** a proof.
7. **Informal proof** — `∑ deg(v) = 2|E|`, hence even odd-count; reviewed with no gaps.
8. **Lean certificate** — arithmetic core (`2e` is even; odd + odd is even), with an explicit faithfulness note.
9. **Map / report** — established vs refuted vs open.

The graph-theoretic handshake claim is recorded as a **reviewed proof**. The Lean development is a **faithful** formalization only of the arithmetic lemma. Partial coverage cannot promote `C-handshake` to `formal_proof`.

## Project layout

```text
research-atlas/
  campaigns/           campaign.yaml + runtime sqlite / artifacts / reports
  src/research_atlas/
    orchestrator/      sequential state machine, resume
    planner/           explainable priority scores
    workers/           one worker, many roles by turn
    knowledge/         SQLite graph, events, versioning rules
    verification/      experiments, counterexamples, Lean policy
    retrieval/         context loader for a move
    reporting/         Markdown campaign report
    model_adapters/    heuristic adapter (no paid calls in the MVP)
    domain_packs/      finite_graphs calibration pack
  lean/ResearchAtlasLean/   pinned Lean 4 project, no Mathlib
  tests/
```

Persistence is SQLite (nodes, edges, events). Artifacts are hash-addressed directories. The event log is the resume trail.

## Install and run

Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
research-atlas init --campaign handshake
research-atlas run --campaign handshake
research-atlas status --campaign handshake
research-atlas report --campaign handshake
pytest
```

`research-atlas run` is resumable. Interrupted campaigns continue from completed actions without duplicating claim versions.

Lean compilation is optional. If `lake` is not on `PATH`, the certificate is stored as `lean_unavailable` and the graph-theoretic claim stays at reviewed-proof level. Install a Lean 4 toolchain (Elan) matching `lean/ResearchAtlasLean/lean-toolchain` (currently Lean 4.34.1) and rerun to attach a compiled certificate. The MVP Lean project uses core Lean only; it does not depend on Mathlib.

## Design rules encoded in software

- Workers submit **graph proposals**. They do not directly overwrite scientific status.
- A valid counterexample must satisfy the hypotheses and fail the conclusion of a **named statement version**.
- Bounded exhaustive checks must record universe and completeness, and must set `promotes_to_universal_proof: false`.
- Lean sources must not contain `sorry`, `admit`, or extra `axiom`s. Foundational Lean core/`omega` is accepted.
- A failure has **scope**. `K2` blocks “every graph has an even-degree vertex”; it does not discard degree-parity questions or all inductive strategies.
- Incompatible results open a reconciliation question (same definition? same quantifiers? missing hypothesis? experimental error? mismatched formalization?).

## Development phases

| Phase | Verifiable result | MVP status |
|---|---|---|
| 1. Scientific memory | Register a campaign and generate a report | done |
| 2. Reproducible execution | Run tasks, store evidence, resume | done |
| 3. Two loops | Choose actions and update the graph | done (sequential, heuristic worker) |
| 4. Lean verification | Bind certificates to concrete claims | done (arithmetic core + faithfulness audit) |
| 5. Evaluation | Compare strategies under equal budget | not started |
| 6. Parallelism | Faster campaigns with one commit authority | not started |
| 7. Open research | Expert-supervised open question | not started |

Evaluation, when added, must compare direct generation, iterative repair, and the graph-backed system under the **same budget and tools**. Count verified results, wrongly promoted claims, reproducibility, cost per result, lemma reuse, and human intervention time. Node count measures activity, not mathematical progress.

## Adding a domain pack

A domain pack supplies definitions, object representation, generators, allowed operations, specialized checkers, an initial corpus, and search heuristics. The traceability protocol stays fixed; only the mathematical strategy changes.
