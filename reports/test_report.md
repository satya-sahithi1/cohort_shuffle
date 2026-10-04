# Test Report — Cohort Shuffle Algorithm

**Date:** 2026-10-04
**Test runner:** pytest 8.3.3
**Total tests:** 80
**Result:** 80 passed, 0 failed (0.11s)

---

## Overview

The test suite covers the entire algorithm layer — every public function across all five modules. Tests are organised to mirror the algorithm's own structure: one test file per module. All tests live in `tests/algorithm/` and run with no database, no server, and no external dependencies.

Two bugs were caught during test authoring and fixed before the final run:

1. **Wrong remainder-rule expectation** (`test_greedy.py`): The test assumed 14 students with team size 4 would absorb the remainder. In fact `r=2` equals exactly `team_size/2 = 2.0`, which by the spec forms a new smaller team — not absorb. The test input was corrected to use 13 students (r=1, always absorb).

2. **Solo-team false positive** (`test_fairness.py`): A student alone on a team was being flagged as a fairness violation. Python's `all()` on an empty sequence returns `True`, so the check `all(pair_score > 0 for teammate in [])` incorrectly returned True. Fixed in `fairness.py` with an explicit guard: skip students with no teammates.

---

## Test Files and Coverage

### `test_scorer.py` — 21 tests

**What scorer.py does:** Implements the core scoring formula. Assigns a numeric cost to any student pair based on how many times they have worked together and how recently. Also computes team-level and arrangement-level scores, saturation, and the two-key ranking used to compare arrangements.

**Why these tests matter:** Every other module calls the scorer. If the scoring formula is wrong, greedy placement, swap optimisation, and fairness enforcement all produce wrong results. These tests establish the mathematical foundation.

| Test class | Tests | What is verified |
|------------|-------|-----------------|
| `TestPairScore` | 7 | Never-met = 0. Score increases with count. Score increases with recency. Symmetric — (A,B) same as (B,A). Key order irrelevant. |
| `TestTeamScore` | 3 | All-stranger team = 0. Team with one pair = that pair's score only. Solo team = 0. |
| `TestMarginalScore` | 3 | Adding to empty team costs 0. Adding a stranger costs 0. Adding a repeat increases cost. |
| `TestArrangementScore` | 2 | All strangers = 0. Sums correctly across multiple teams. |
| `TestCountNewPairs` | 3 | All new = full count. All known = 0. Partial = correct count. |
| `TestSaturation` | 4 | No history = 0.0. Full history = 1.0. Partial = correct fraction. Edge case: < 2 students = 0.0. |
| `TestIsBetter` | 4 | Lower score wins. Higher score loses. Equal score — more new pairs wins. Equal score, equal new pairs — not better. |

---

### `test_greedy.py` — 10 tests

**What greedy.py does:** Places students into teams one by one. The most-conflicted students (highest overlap with others) go first. Each student is placed into the team with the lowest marginal cost. A random jitter in the sort ensures different restarts produce different orderings.

**Why these tests matter:** Greedy placement is the foundation every restart builds on. If it produces wrong team sizes, duplicates, or loses students, no amount of optimisation can fix it downstream.

| Test class | Tests | What is verified |
|------------|-------|-----------------|
| `TestTeamSizes` | 6 | Exact division → all teams exactly team_size. r=1 → absorb, never solo. r < half → absorb. r > half → new smaller team. Fewer students than team_size → one team. Empty students → empty result. |
| `TestAllStudentsPlaced` | 3 | All 62 students placed with no history. All 26 placed with history. No student appears twice. |
| `TestConflictedStudentsPlacedWell` | 1 | A student with known history prefers strangers in ≥80% of 50 randomised runs. |

---

### `test_swapper.py` — 7 tests

**What swapper.py does:** After greedy placement, tries every possible student swap between pairs of teams. Only swaps involving at least one "conflict student" (someone who already has a repeat teammate) are attempted. Keeps a swap if it improves the (score, new_pairs) ranking. Runs passes until no improvement is found.

**Why these tests matter:** The swap phase is where the algorithm moves from "decent" to "good." These tests verify it never makes things worse and that the conflict-student filter correctly skips the bulk of irrelevant swap attempts.

| Test class | Tests | What is verified |
|------------|-------|-----------------|
| `TestConflictStudents` | 3 | No history → empty conflict set. Detects repeat on same team. Repeat on different team is not a conflict. |
| `TestOptimise` | 4 | No history → teams unchanged. Forced bad arrangement improves after optimisation. All students present after swap. Single team does not crash. |

---

### `test_fairness.py` — 12 tests

**What fairness.py does:** After swap optimisation, checks whether any student has zero new teammates (their entire team is repeat partners). For each such student, tries a targeted swap with someone from another team they have never worked with. Keeps only swaps that fix the violation without creating a new one.

**Why these tests matter:** Fairness is the primary quality criterion from the spec — "the real failure is a student who gets no new person at all on their team." Score minimisation alone cannot guarantee this. The fairness pass is the explicit safeguard.

| Test class | Tests | What is verified |
|------------|-------|-----------------|
| `TestHasViolations` | 6 | No history → no violations. Detects all-repeat team. One new teammate → no violation. Only the affected student flagged. Multiple violations detected. Solo team → no violation (edge case fixed). |
| `TestEnforce` | 6 | No violations → teams unchanged. Fixes simple violation. All students present after fix. Does not create a new violation while fixing one. Exhausted student does not crash. Two violations — both fixed. |

---

### `test_engine.py` — 24 tests

**What engine.py does:** The single public entry point. Orchestrates all four modules: greedy → swap → fairness. Manages time-limited restarts (runs multiple greedy+swap attempts, keeps the best by two-key ranking). Handles lock constraints (must-be-together, must-be-apart). Returns a `FormationResult` with teams, score, new_pairs, saturation, restart count, elapsed time, and any remaining fairness violations.

**Why these tests matter:** The engine is what the formation service will call. These are the integration tests — they verify the full pipeline works end to end, not just individual steps.

| Test class | Tests | What is verified |
|------------|-------|-----------------|
| `TestEdgeCases` | 4 | Empty students → empty result. Fewer students than team_size → one team. Exact team size → one team. Single student → one team of one. |
| `TestFirstActivity` | 5 | No history → score 0. All students placed. No restarts triggered. Saturation = 0.0. Deterministic with fixed seed. |
| `TestWithHistory` | 5 | All students placed with history. No duplicates. Score is finite and non-negative. Saturation increases monotonically over activities. All result fields correctly populated. |
| `TestFairness` | 2 | No fairness violations in first 4 activities (26 students, team size 4). `unfair_students` field matches direct `has_violations()` check. |
| `TestLocks` | 4 | Together lock → students on same team. Apart lock → students on different teams. All students placed with locks active. No locks vs empty list → identical result. |
| `TestValidateLocks` | 4 | Valid locks → no errors. Together group larger than team_size → error reported. Together group equal to team_size → valid. Empty locks → no errors. |

---

## Bugs Found and Fixed

### Bug 1 — Wrong test input for remainder rule
**File:** `tests/algorithm/test_greedy.py`
**Test:** `test_absorb_remainder`
**Problem:** The test used 14 students with team_size 4. `r = 14 % 4 = 2`, and `half = 4 / 2 = 2.0`. The condition `r < half` is `2 < 2.0` = False, so the algorithm correctly creates a new small team (4 teams), not absorb (3 teams). The test expected 3 teams — wrong.
**Fix:** Changed to 13 students. `r = 13 % 4 = 1`, which always absorbs (special case), producing 3 teams as intended. The algorithm was correct; the test was wrong.

### Bug 2 — Solo student flagged as fairness violation
**File:** `algorithm/fairness.py`
**Test:** `test_solo_team_no_violation`
**Problem:** `has_violations()` called `all(pair_score(...) > 0 for teammate in teammates)` where `teammates` was an empty list (solo student). Python's `all([])` returns `True`, so a solo student was incorrectly flagged as having "all repeat partners."
**Fix:** Added an explicit check: `if not teammates: continue`. A student with no teammates cannot have a fairness violation.
**Impact:** This would have caused `enforce()` to attempt pointless fix swaps for solo students in every formation with a remainder-of-1 situation.

---

## How Tests Relate to the Algorithm

The test suite follows the algorithm's dependency chain from bottom to top:

```
test_scorer.py      ← foundation (everything calls scorer)
    ↓
test_greedy.py      ← uses scorer to place students
    ↓
test_swapper.py     ← uses scorer to evaluate and improve placement
    ↓
test_fairness.py    ← uses scorer to detect and fix violations
    ↓
test_engine.py      ← integration: all modules working together
```

Each layer's tests are independent — they use hand-crafted fixtures from `conftest.py`, not the output of other modules. This means a failure in `greedy.py` shows up in `test_greedy.py` and does not cascade silently into `test_engine.py`.

---

## Running the Tests

```bash
cd cohort_shuffle
PYTHONPATH=. .venv/bin/python -m pytest tests/ -v
```

To run a single file:
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/algorithm/test_engine.py -v
```

To run with coverage:
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/ --cov=algorithm --cov-report=term-missing
```
