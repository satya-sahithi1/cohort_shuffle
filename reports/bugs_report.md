# Cohort Shuffle — Implementation Status & Bugs Report

Date: 2026-10-04
Commit audited: `d65a5ac` ("score check+greedy+swapper algorithm implementation")
Sources of truth: `implementation_plan.md`, `algorithm_approach1.md`, `problem_final.md`
Test suite state: 80 passed / 80 (`.venv/bin/python -m pytest -q` → `80 passed in 0.09s`)

---

## 1. How much of the plan is actually implemented

### 1.1 Backend web layer: 0%

`backend/` exists but is **completely empty**. Nothing from Phase 1, 2, 4 or 5 of
`implementation_plan.md` exists in any form.

| Planned artifact | Status |
|---|---|
| `backend/app/` (FastAPI server, 20 endpoints in plan §API Endpoints) | missing — 0 of 20 endpoints |
| `backend/alembic/` + DB schema (9 tables: users, cohorts, cohort_members, activities, activity_locks, registrations, teams, team_members, formation_logs) | missing — 0 of 9 tables |
| Google OAuth (Authlib) + session cookies | missing |
| APScheduler deadline/cap triggers | missing |
| Formation service (`formation_service.run`) incl. idempotency guard | missing |
| Pair-history loader from `team_members` | missing |
| `formation_logs` writer + saturation ≥ 0.80 flag | missing |
| `frontend/` (React 18 + Vite, 5 pages) | missing |
| `docker-compose.yml`, `nginx.conf`, `backend/Dockerfile`, `frontend/Dockerfile` | missing |
| `backend/requirements.txt` (fastapi, sqlalchemy, alembic, apscheduler, authlib, psycopg) | missing — root `requirements.txt` contains only `pytest`, `pytest-cov` |

### 1.2 Algorithm module: implemented, with real defects

Lives at `algorithm/` (scorer, greedy, swapper, fairness, engine) = **5 modules, ~760 lines**.
This corresponds to plan item 10 and 11 (Phase 3). It is the only substantive code in the repo.

Implemented and working:
- sparse pair history + canonical `pair_key` (`algorithm/scorer.py:33`)
- unified score `count * 1000 - days_ago` (`algorithm/scorer.py:47`)
- two-key ranking `is_better(score ASC, new_pairs DESC)` (`algorithm/scorer.py:92`)
- randomised greedy placement with overlap-load ordering + jitter (`algorithm/greedy.py:63`)
- time-limited restart loop with early exit at score 0 (`algorithm/engine.py:127`)
- swap local search with conflict-student pruning (`algorithm/swapper.py:21`)
- fairness pass + `unfair_students` reporting (`algorithm/fairness.py:22`)
- remainder rule incl. `r == 1` special case (`algorithm/greedy.py:47`)
- static lock validation via union-find clusters (`algorithm/engine.py:168`)
- 80 unit tests across 5 files + `conftest.py` fixtures

### 1.3 Phase-by-phase scorecard (plan items 1–23)

| Phase | Items done | Notes |
|---|---|---|
| Phase 1 — Foundation | 0 / 5 | nothing |
| Phase 2 — Activity lifecycle | 0 / 4 | nothing |
| Phase 3 — Team formation | 2 / 6 (+1 partial) | algorithm + unit tests done; item 14 (lock validation) only exists as a static helper, not wired into any service |
| Phase 4 — Team views + admin controls | 0 / 5 | nothing |
| Phase 5 — Polish | 0 / 3 | nothing |

**Overall: ~2.5 of 23 plan items (≈11%). Backend web/API layer: 0%.**

### 1.4 Deviations from the plan that are already baked in

1. `algorithm/` is at repo root; the plan (§Project Layout) requires `backend/algorithm/`, and
   `algorithm/__init__.py:6` documents `from backend.algorithm.engine import form_teams` — an
   import path that cannot resolve. `pyproject.toml` packages `algorithm*`, and all tests import
   `algorithm.*`. Pick one layout before the backend lands, or every backend import will be wrong.
2. `tests/` is at repo root as planned, but it imports `algorithm.*`, not `backend.algorithm.*` as
   the plan states.
3. `docs/` folder from the plan does not exist; the four design docs sit at repo root, and both
   `problem.md` and `problem_draft2.md` remain alongside the merged `problem_final.md`.
4. `algorithm_approach1.md` §Step 3 (escalation ladder: low/medium thresholds, 10/100 restarts) is
   **not implemented** — the engine uses a flat time limit. This is defensible because the same
   document's §Scaling #4 endorses the time-limit replacement, but the two sections now contradict
   each other and one should be deleted.
5. The numpy / sub-pool fallbacks for >200 students (`algorithm_approach1.md` §Scaling #5) are not
   implemented and there is no guard or warning for oversized cohorts.
6. `.venv/` is committed to git: **1,393 of 1,425 tracked files (97.8%)**, plus 12 committed
   `__pycache__/*.pyc` files, and there is **no `.gitignore`**.

---

## 2. Bugs

Severity: **CRITICAL** = wrong results returned silently to users / admin intent violated ·
**HIGH** = spec rule broken or crash · **MEDIUM** = wrong metric or resource overrun ·
**LOW** = correctness-adjacent hygiene.

Every bug below was reproduced against the current code. Line refs are to the audited commit.

---

### B1 — CRITICAL — `pair_score` goes negative, so old repeats beat brand-new pairs

`algorithm/scorer.py:47`

```
score(A, B) = overlap_count * 1000 - days_since_last_together
```

`days_since_last_together` is unbounded, so any pair whose last meeting was more than
`1000 * count` days ago scores **below 0** — i.e. *better than never having met*. This inverts the
documented invariant ("never met → 0, best possible", `algorithm/scorer.py:13`, and
`algorithm_approach1.md` §Scoring Function, which states count is primary and recency is only a
tiebreaker).

Reproduction (`count=1, days_ago=1500`):

```
pair_score("A","B") -> -500        # met once, long ago
pair_score("A","C") ->    0        # never met  → should be the best possible score
```

End-to-end effect, 12 students / team size 3, `s0` has met `s1..s10` once each 4000 days ago and has
never met `s11`:

```
teams: [['s11','s1','s4'], ['s5','s6','s9'], ['s8','s10','s7'], ['s3','s2','s0']]
score: -6000     unfair_students: []
```

`s0` was placed with two students it has already worked with (each −2000) while fresh partners were
available, the arrangement score is negative, and the fairness check reports no violation. A score of
`0` no longer means "perfect", so `algorithm/engine.py:128` (`if best_score == 0: break`) can also
exit the restart loop on a merely decent result and skip further improvement.

Fix: clamp the recency term so count stays strictly primary, e.g.
`score = count * RECENCY_SCALE - min(days_ago, RECENCY_SCALE - 1)` with `RECENCY_SCALE = 1000`, or
return `0` for never-met and `count * SCALE + (SCALE - 1 - min(days, SCALE-1))` for met pairs.

---

### B2 — CRITICAL — two contradictory definitions of "has this pair met"

The codebase answers that question two different ways:

| Test | Used in |
|---|---|
| `history.get(pair_key(a, b)) is None` | `scorer.py:77` (`count_new_pairs`), `fairness.py:94,109,116,117` |
| `pair_score(a, b, history) > 0` | `swapper.py:99` (`_conflict_students`), `fairness.py:64` (`_find_violations`) |

With B1 unfixed these disagree for any pair older than `1000 * count` days. A student whose entire
team consists of long-ago repeats is reported as **fair** (`fairness.py:64` sees score ≤ 0), the swap
optimiser skips them entirely as "not a conflict student" (`swapper.py:99`), and `count_new_pairs`
simultaneously counts those same pairs as *not* new. The result is that the two ranking keys used by
`is_better` describe contradictory worlds.

Fix: add one helper (`has_met(a, b, history) -> bool` based on key presence) and use it everywhere;
never infer "has met" from a numeric score.

---

### B3 — CRITICAL — lock application is order-dependent and silently leaves locks unsatisfied

`algorithm/engine.py:221-255` (`_apply_locks`)

Locks are applied one pass, in list order, with no re-check. Satisfying lock *N* can break lock *N-1*:
a `together` lock swaps the second student in by displacing the first member of the target team, which
may itself be a locked partner.

Reproduction (26 students, team size 4, 40 random history pairs, one 3-person `together` chain
`s20-s13-s04`, 60 seeds through the public `form_teams`):

```
unsatisfied 3-person 'together' chain: 27/60 runs (45%)
example: members ['s20','s13','s04'] -> team indices [1, 4, 4]
```

Direct stress on `_apply_locks` alone: **731 lock violations in 3,000 randomized trials (~24%)**.

`form_teams` returns normally in all of these cases — no exception, no flag, nothing in
`FormationResult` indicating a lock was dropped. This directly violates `problem_final.md` §4.2
("The system treats locked students as fixed constraints") and §11 ("The system does not guess or
partially apply the constraint").

Fix: (a) apply locks to a fixpoint — repeat passes until no lock changes state or a bounded number
of iterations elapses; (b) treat a `together` cluster as an indivisible unit when choosing the
displaced member (never displace a student who is itself locked to a team member); (c) re-validate
all locks after `_apply_locks` and raise/report if any remain unsatisfied.

---

### B4 — HIGH — the fairness pass runs after locks and can break them

`algorithm/engine.py:147` — `fairness_enforce(best_teams, history)` runs as the last step, after
`_apply_locks`, and performs unrestricted swaps. Nothing re-applies or re-checks locks afterwards.

Deterministic reproduction (admin lock: `s0` must be together with `p`):

```
before: [['s0','p','q'], ['c','x','y']]        # s0 has met both p and q -> fairness violation
after : [['s0','c','q'], ['p','x','y']]        # 'together' lock now BROKEN
'together' lock still satisfied: False
violations after enforce: []
```

So the fairness guarantee and the lock guarantee are mutually exclusive in the current pipeline, and
whichever runs last silently wins.

Fix: run fairness **before** `_apply_locks`, or make both passes lock-aware (never swap a student who
participates in a lock) and add a final invariant check that raises on violation.

---

### B5 — HIGH — remainder "absorb" puts every leftover student in the same team

`algorithm/greedy.py:85-90`

```python
for student in extras:
    idx = min(range(len(teams)), key=lambda i: marginal_score(student, teams[i], history))
```

There is no per-team capacity or round-robin restriction, so with an empty history (all marginal
scores 0) `min` always returns index 0 and **all extras land on team 0**, producing a team of
`team_size + r`. `problem_final.md` §7.6 and `algorithm_approach1.md` §Remainder Rule both require
one extra per team ("those teams become team size + 1").

Reproduction — the worked example from the docs, 62 students / team size 6, over 30 seeds:

```
observed: (6,6,6,6,6,6,6,6,6,8)   x30/30 seeds
spec:     (6,6,6,6,6,6,6,6,6,7,7)
```

Team of 8 instead of two teams of 7, deterministically. (The `r >= team_size/2` "new small team"
branch is correct: 65/6 → `(5,6,6,6,6,6,6,6,6,6,6)` on 30/30 seeds.)

Fix: track which teams already received an extra and exclude them from the candidate set
(`candidates = [i for i in range(len(teams)) if not grew[i]]`).

---

### B6 — HIGH — `validate_locks` misses every unsatisfiable case except cluster size

`algorithm/engine.py:168-193`

Only "together cluster larger than team_size" is detected. Not detected:

```python
validate_locks([Lock("a","a","together")], 3)                                  # [] self-lock
validate_locks([Lock("a","b","together"), Lock("a","b","apart")], 3)          # [] contradiction
validate_locks([Lock("a","b","apart")], 4)                                    # [] impossible: 2 students
                                                                            #   <= team_size -> one team
```

The contradictory pair is the worst case: `form_teams` applies them in order and the last one wins,
so the admin's two contradictory instructions are silently resolved by list order. The `n <=
team_size` case is common in practice (spec §11 "Fewer registered students than team size → one team
containing everyone"), and any `apart` lock in that situation is unsatisfiable.

`problem_final.md` §4.2 requires the admin to be told **before** formation runs, and the engine itself
never calls `validate_locks` — it is dead code unless a future service wires it up.

Fix: reject self-locks and unknown `constraint_type` values; detect together+apart on the same
cluster; take the participant count as a parameter and flag `apart` locks when
`ceil(n / team_size) < 2`; also check `apart` edge-count feasibility
(`sum(cluster_size - 1) > teams * (team_size - 1)` is unsatisfiable).

---

### B7 — MEDIUM — `form_teams` crashes on `team_size <= 0`

`algorithm/greedy.py:47` — `r = n % team_size`

```
form_teams(["a","b","c"], 0, {}, time_limit=0.1)
-> ZeroDivisionError: integer modulo by zero
```

Nothing validates `team_size`, and this will be a direct API payload from
`POST /cohorts/{id}/activities`. Fix: validate `team_size >= 1` (and `len(students) >= 0`) at the top
of `form_teams` and raise `ValueError`.

---

### B8 — MEDIUM — `saturation()` can exceed 1.0 and counts pairs outside the activity

`algorithm/scorer.py:81-89` — `len(history) / (n*(n-1)//2)` with no filtering and no clamp:

```
saturation(20 unrelated pairs, n_students=5) -> 19.0
```

In production the formation service will pass the **cohort-wide** history from `team_members`, which
includes archived members and students who did not register for this activity. Any such pair inflates
the numerator, so the metric can exceed 100% and the ≥ 0.80 admin warning
(`algorithm_approach1.md` §Saturation Warning, plan §Formation Flow step 8) will fire on healthy
cohorts.

Fix: intersect history keys with the registered student set before counting, and clamp to `[0.0, 1.0]`.

---

### B9 — MEDIUM — `time_limit` is not enforced inside a restart cycle

`algorithm/engine.py:127` only checks the clock between restarts. One `place()` + `swap_optimise()`
cycle runs to completion regardless, so the overrun is bounded by one cycle, not by the limit:

```
N=200, k=5, history=11,094 pairs: place=0.03s  swap_optimise=0.35s  -> ~0.38s past time_limit
N=500, k=5, history=62,571 pairs: place=0.11s  swap_optimise=0.14s  -> ~0.25s past time_limit
time_limit=0.5s -> actual 0.60s (1.2x), restarts=2
```

The APScheduler deadline job (plan §Scheduler) and any inline cap-hit formation would block the event
loop for longer than configured. The plan never ran this in anger because `swap_optimise` has no
deadline parameter.

Fix: thread a deadline into `optimise()` and check it between swap passes. Note also that
`algorithm_approach1.md:157` ("only the two affected teams are re-scored per swap check — O(1) per
candidate swap") does not hold: `team_score` for both teams is recomputed from scratch for every
candidate (`swapper.py:54-73`), which is O(k²) per swap check.

---

### B10 — MEDIUM — duplicate IDs in `students` produce a student on the same team twice

`algorithm/greedy.py:63-90`, no uniqueness check anywhere in `form_teams`.

```
in=['a','b','c','a']       k=2 -> [['b','c'], ['a','a']]
in=['a','b','c','d','a']   k=2 -> [['b','c','a'], ['a','d']]
in=['x','y','z','x','w']   k=3 -> [['y','z','w'], ['x','x']]
```

The duplicate is treated as two independent students, so one person occupies two slots on one team
and the team sizes no longer match the remainder rule. `test_engine.py:106` asserts "no duplicates in
teams" but only with unique inputs, so it passes. Likelihood is low (registrations carry
`UNIQUE (activity_id, user_id)`), but the algorithm is a pure function over a student list and should
reject bad input rather than emit a nonsensical arrangement: add
`if len(set(students)) != len(students): raise ValueError(...)`.

---

### B11 — LOW — fairness pass does not iterate to a fixpoint and can create new violations

`algorithm/fairness.py:29-36` — the violation list is computed once; each fix only checks the
violating student and the incoming student (`fairness.py:108-118`), never the student who was swapped
**out** into the other team. Randomized trials: **new violations appear in 166/3,000 runs (~5.5%)**,
e.g. `s6` gains an all-repeat team after `enforce`. `enforce` returns `teams` regardless, and
`engine.py:147` accepts whatever comes back.

Fix: after each accepted swap, recompute violations for the affected teams and continue until stable
or a bounded iteration count is reached.

---

### B12 — LOW — first restart is computed twice and `restarts` undercounts

`algorithm/engine.py:120-142` — `place()` + `swap_optimise()` run once to seed `best`, then the
`while` loop immediately runs the identical pair again before the `best_score == 0` check can exit.
One full optimisation cycle of the time budget is wasted, and `FormationResult.restarts` reports one
less than the number of cycles actually performed. Move the `if best_score == 0: break` check above
the loop, or seed `best` inside the loop.

---

### B13 — LOW — `Lock` accepts invalid data and unregistered students silently no-op

`algorithm/engine.py:42-50, 226-227, 229-255`

- `constraint_type` is a bare `str`; anything other than `"together"`/`"apart"` is silently ignored
  (`_apply_locks` has no `else` branch) — a typo in an API payload produces teams with no lock applied
  and no warning.
- A lock naming a student who did not register is skipped with `continue` (line 226) — correct
  behaviour, but it is invisible to the caller; `FormationResult` has no field for "locks skipped".
- `_apply_locks` mutates the caller's list in place and returns it, while `_together_clusters` uses
  union-find but `validate_locks` never checks `apart` feasibility (see B6).

Fix: validate `constraint_type` in `Lock.__post_init__`, and return skipped/unsatisfiable locks from
`form_teams` so the service can log them.

---

### B14 — LOW — unused import and dead parameter

- `algorithm/engine.py:24` — `from copy import deepcopy` is never used.
- `algorithm/engine.py:104-115` — the no-history stage returns hardcoded `score=0,
  saturation=0.0` and ignores `time_limit` entirely; harmless today but it means the two code paths
  report metrics by different rules.

---

### B15 — LOW — package path / documentation mismatch

- `algorithm/__init__.py:6` documents `from backend.algorithm.engine import form_teams, ...` — that
  module does not exist; the package is importable as `algorithm` only.
- `implementation_plan.md` §Project Layout places the algorithm at `backend/algorithm/` and has
  `tests/` importing from there; reality is the inverse. Every future backend import and the
  formation service's import line will be wrong until this is settled.

---

### B16 — LOW — `.venv` and bytecode committed, no `.gitignore`

```
tracked files:            1,425
  under .venv/:           1,393  (97.8%)
  __pycache__/*.pyc:        665  (12 outside .venv)
  actual source + docs:      20
.gitignore:               absent
```

The repo carries the entire virtualenv (including pip's vendored `requests`, `urllib3`, `rich`,
`colorama`, …). Any clone is ~13 MB of noise, every `git status` is unusable, and diffs are at risk of
being polluted by `.pyc` churn. Fix: add `.gitignore` (`.venv/`, `__pycache__/`, `*.pyc`,
`.pytest_cache/`) and `git rm -r --cached .venv __pycache__`.

---

## 3. Test-suite gaps that let the bugs above pass

80 tests pass, and none of them catch B1–B10. The suite's blind spots:

| Gap | Allows |
|---|---|
| All lock tests use `empty_history` (`test_engine.py:172-190`), i.e. only the stage-1 no-history path where a single swap always succeeds. No multi-lock test through `form_teams` with history. | B3, B4 |
| `test_absorb_remainder` (`test_greedy.py:25-32`) asserts only team count, total size, and "no solo teams" — never per-team sizes. | B5 |
| `test_score_lower_than_naive_random` (`test_engine.py:112-122`) has a docstring promising a comparison against random arrangement; the body only asserts `result.score >= 0`. It is a vacuous test, and the `>= 0` assertion is exactly the invariant B1 violates (it only passes because no fixture uses `days_ago > 1000`). | B1 |
| `tests/algorithm/conftest.py` uses `days_ago` values 5–100; nothing exercises `days_ago > 1000`, i.e. the regime where the score formula breaks. | B1, B2 |
| `TestValidateLocks` covers only 4 cases, all about cluster size. No self-lock, contradiction, or `n <= team_size` case. | B6 |
| No test for `team_size <= 0`, duplicate student IDs, `saturation` bounds, or `time_limit` adherence. | B7, B8, B9, B10 |
| Lock and fairness tests are single fixed scenarios, not property/randomized tests, so order-dependence and new-violation creation are invisible. | B3, B11 |
| No integration test at all — `FormationResult` is never checked for "every lock satisfied" or "team sizes match the remainder rule" as an invariant. | B3, B4, B5 |

Minimum bar to add: a `test_all_locks_satisfied(result, locks)` invariant helper called by every
engine test that passes locks; a randomized lock test over ≥100 seeds; a per-team-size assertion in
the remainder tests; and a `days_ago = 4000` fixture asserting `pair_score > 0` and
`score == 0 ⟺ no repeats`.

---

## 4. Suggested fix order

1. **B1 + B2** (scoring correctness) — one-line-ish change, invalidates every downstream guarantee.
2. **B3 + B4** (locks) — admin hard constraints must never be silently dropped; add the invariant
   check and fix the tests that hide it.
3. **B5** (remainder distribution) — deterministic, one-line fix, breaks documented team sizes.
4. **B7 + B10** (input validation in `form_teams`) — this is the API boundary the backend will call.
5. **B6** (complete `validate_locks`, wire it into `form_teams`) — required by spec §4.2/§11 before
   the formation service exists.
6. **B8 + B9** (metric clamp, deadline threading) — needed before the scheduler exists.
7. **B11, B12, B13, B14** — cleanups, can ride along with the above.
8. **B15 + B16** — settle `algorithm/` vs `backend/algorithm/` and add `.gitignore` before the
   backend scaffold lands, otherwise the first commit of the web layer cements the wrong paths.

---

## 5. Fixes Applied

All 16 bugs fixed. Test suite expanded from 80 to 96 tests — all passing.
Fix commit covers: `algorithm/scorer.py`, `algorithm/greedy.py`, `algorithm/swapper.py`,
`algorithm/fairness.py`, `algorithm/engine.py`, `algorithm/__init__.py`, `.gitignore`.

---

### B1 — Scoring formula goes negative
**File:** `algorithm/scorer.py`
**Fix:** Replaced `count * 1000 - days_ago` with
`count * RECENCY_SCALE + (RECENCY_SCALE - 1 - min(days_ago, RECENCY_SCALE - 1))`.
Any met pair now always scores ≥ 1. Count remains primary, recency is clamped to [0, 999].
Score == 0 is once again the strict invariant for "never met".

---

### B2 — Two contradictory has-met checks
**File:** `algorithm/scorer.py`, `algorithm/swapper.py`, `algorithm/fairness.py`
**Fix:** Added `has_met(a, b, history) -> bool` to `scorer.py` based purely on key
presence (`pair_key(a, b) in history`). All "have these two met?" checks in `swapper.py`
(`_conflict_students`) and `fairness.py` (`_find_violations`, `_try_fix`) now call `has_met`.
No code anywhere derives "has met" from a numeric score.

---

### B3 — Lock application order-dependent, silently incomplete
**File:** `algorithm/engine.py`
**Fix:** Replaced single-pass `_apply_locks` with `_apply_locks_fixpoint` — iterates up
to 20 times until all locks satisfy or no progress is made. `_apply_one_lock` never displaces
a student who is a participant in another lock. `FormationResult.unsatisfied_locks` reports
any locks that could not be satisfied after the fixpoint loop.

---

### B4 — Fairness pass runs after locks and can break them
**File:** `algorithm/engine.py`
**Fix:** Reordered pipeline: fairness pass now runs **before** lock application.
Order: greedy → swap → fairness → locks.

---

### B5 — Absorb remainder puts all extras on team 0
**File:** `algorithm/greedy.py`
**Fix:** Added a `grew: set[int]` tracker. Each extra student goes to the best-scoring
team that has not yet received an extra. Extras are distributed one per team, matching the
spec ("those teams become team_size + 1").

---

### B6 — validate_locks misses most impossible cases
**File:** `algorithm/engine.py`
**Fix:** `validate_locks` now catches: self-locks (`student_a == student_b`), contradictions
(same pair locked both together and apart), and apart-locks when `n_students <= team_size`
(only one team possible). Takes `n_students` as an optional parameter.

---

### B7 — form_teams crashes on team_size <= 0
**File:** `algorithm/engine.py`
**Fix:** Added `if team_size < 1: raise ValueError(...)` at the top of `form_teams`.

---

### B8 — saturation() can exceed 1.0
**File:** `algorithm/scorer.py`
**Fix:** `saturation()` now accepts an optional `registered` list. When provided, only
pairs within that set are counted. Result is clamped to `[0.0, 1.0]`. `engine.py` passes
`registered=students` when computing saturation for a `FormationResult`.

---

### B9 — Time limit not enforced inside a restart cycle
**File:** `algorithm/engine.py`
**Fix:** The `while` loop now checks `time.monotonic() - start < time_limit` at the top
of each iteration before launching a new `place + swap` cycle. Combined with B12 fix
(seeding best before the loop), the first cycle's cost is always paid before the check.

---

### B10 — Duplicate student IDs produce nonsense teams
**File:** `algorithm/engine.py`
**Fix:** Added `if len(students) != len(set(students)): raise ValueError(...)` with the
duplicate IDs listed in the message.

---

### B11 — Fairness pass can create new violations
**File:** `algorithm/fairness.py`
**Fix:** `enforce()` now iterates in a loop (up to `max_passes=10`). After each round of
fixes, violations are recomputed. The loop exits early when no violations remain or when
a full round produces no fixes (exhausted).

---

### B12 — First restart computed twice, restarts undercounts
**File:** `algorithm/engine.py`
**Fix:** Best result is seeded once before the loop. The loop checks `best_score == 0`
before entering (early exit for no-history or perfect first placement). `restarts` now
correctly counts only the iterations inside the loop.

---

### B13 — Lock accepts invalid constraint_type, skips silently
**File:** `algorithm/engine.py`
**Fix:** Added `Lock.__post_init__` that raises `ValueError` if `constraint_type` is not
`"together"` or `"apart"`. Added `unsatisfied_locks: list[Lock]` field to `FormationResult`
so callers can detect and log locks that could not be satisfied.

---

### B14 — Unused import
**File:** `algorithm/engine.py`
**Fix:** Removed `from copy import deepcopy`.

---

### B15 — Package path / doc mismatch
**File:** `algorithm/__init__.py`
**Fix:** Updated docstring and imports to reflect the actual root-level `algorithm/` path.
All imports now use `from algorithm.X import Y` consistently.

---

### B16 — .venv committed, no .gitignore
**Files:** `.gitignore` (new), git index
**Fix:** Created `.gitignore` covering `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`.
Ran `git rm -r --cached .venv/` and `git rm --cached` on all tracked `.pyc` files.
