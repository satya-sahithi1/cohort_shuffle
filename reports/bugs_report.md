# Cohort Shuffle — Implementation Status & Bugs Report

Date: 2026-10-04
Findings first written against commit `d65a5ac`; **re-verified in the working tree** after the
bug-fix pass (uncommitted changes on top of `318f7d1` "bug fixes for engine", 6 algorithm files
modified, 2 test files extended, `.gitignore` added, `backend/` scaffolded).
Sources of truth: `implementation_plan.md`, `algorithm_approach1.md`, `problem_final.md`
Test suite: **96 passed / 96** (`.venv/bin/python -m pytest -q` → `96 passed`) — was 80 before the fixes.
Verification method: every bug re-tested by re-running its original reproduction against the current
code, plus new adversarial probes aimed at the fixes themselves (randomized seeds, boundary values,
direct calls to the new internal helpers).

---

## 1. How much of the plan is actually implemented

### 1.1 Backend web layer: ~5% (scaffold only)

`backend/` was empty at the time of the first pass. It now contains a Phase 1 scaffold —
`app/main.py` (FastAPI app, CORS, `/health`), `app/config.py` (pydantic-settings), `app/database.py`
(async engine, `Base`, `get_db`), `requirements.txt`, `.env.example`, and **empty**
`app/routers/`, `app/schemas/`, `app/models/`, `app/services/` packages plus an empty `alembic/`
directory. Nothing functional beyond `/health`.

| Planned artifact | Status |
|---|---|
| `backend/app/` routers (20 endpoints in plan §API Endpoints) | missing — 0 of 20 endpoints; `routers/` is an empty package |
| DB schema + migrations (9 tables: users, cohorts, cohort_members, activities, activity_locks, registrations, teams, team_members, formation_logs) | missing — `models/` empty, `alembic/` has no files |
| Google OAuth + session cookies | missing (`python-jose` JWT is in requirements, no OAuth client — see N2) |
| APScheduler deadline/cap triggers | missing (not even in `backend/requirements.txt`) |
| Formation service (`formation_service.run`) incl. idempotency guard | missing (`services/` empty) |
| Pair-history loader from `team_members` | missing |
| `formation_logs` writer + saturation ≥ 0.80 flag | missing |
| `frontend/` (React 18 + Vite, 5 pages) | missing |
| `docker-compose.yml`, `nginx.conf`, `backend/Dockerfile`, `frontend/Dockerfile` | missing |
| `backend/requirements.txt` | present but incomplete (missing `apscheduler`, OAuth client) |

### 1.2 Algorithm module: implemented, was 16 defects, 4 remain

Lives at `algorithm/` (scorer, greedy, swapper, fairness, engine) = 5 modules, ~570 lines after the
fix pass. This is plan items 10 and 11 (Phase 3) and remains the only substantive code in the repo.

Implemented and working:
- sparse pair history + canonical `pair_key` (`algorithm/scorer.py:22`)
- unified pair score, now clamped so count is strictly primary (`algorithm/scorer.py:31`)
- single authoritative `has_met()` used by every "have these two met?" check (`algorithm/scorer.py:26`)
- two-key ranking `is_better(score ASC, new_pairs DESC)` (`algorithm/scorer.py:87`)
- randomised greedy placement with overlap-load ordering + jitter (`algorithm/greedy.py:41`)
- time-limited restart loop with early exit at score 0 (`algorithm/engine.py:102`)
- swap local search with conflict-student pruning (`algorithm/swapper.py:13`)
- fairness pass to fixpoint + `unfair_students` reporting (`algorithm/fairness.py:14`)
- remainder rule incl. one-extra-per-team absorb and `r == 1` special case (`algorithm/greedy.py:60`)
- lock fixpoint application + `unsatisfied_locks` reporting (`algorithm/engine.py:188`)
- static lock validation via union-find clusters (`algorithm/engine.py:138`)
- 96 unit tests across 5 files + `conftest.py` fixtures

### 1.3 Phase-by-phase scorecard (plan items 1–23)

| Phase | Items done | Notes |
|---|---|---|
| Phase 1 — Foundation | 0.5 / 5 | item 1 (project scaffold) in progress; auth, schema/migrations, cohort CRUD, login UI all missing |
| Phase 2 — Activity lifecycle | 0 / 4 | nothing |
| Phase 3 — Team formation | 2 / 6 (+1 partial) | algorithm + unit tests done; item 14 (lock validation) exists as a helper only, never called by `form_teams` or any service |
| Phase 4 — Team views + admin controls | 0 / 5 | nothing |
| Phase 5 — Polish | 0 / 3 | nothing |

**Overall: ~2.5 of 23 plan items (≈11%). Backend endpoints: 0 of 20. DB tables: 0 of 9.**

### 1.4 Deviations from the plan that are baked in

1. `algorithm/` is at repo root; the plan (§Project Layout) requires `backend/algorithm/`.
   `algorithm/__init__.py:5` now correctly imports `algorithm.*` (B15 fixed in code), but
   `implementation_plan.md` still describes the `backend/algorithm/` layout and `tests/` importing
   from it. Pick one before the formation service lands.
2. `docs/` folder from the plan does not exist; the four design docs sit at the repo root, and both
   `problem.md` and `problem_draft2.md` remain alongside the merged `problem_final.md`.
3. `algorithm_approach1.md` §Step 3 (escalation ladder: low/medium thresholds, 10/100 restarts) is not
   implemented — the engine uses a flat time limit. Defensible, because the same document's §Scaling #4
   endorses the time-limit replacement, but the two sections now contradict each other.
4. The numpy / sub-pool fallbacks for >200 students (§Scaling #5) are not implemented and there is no
   guard or warning for oversized cohorts.
5. `backend/requirements.txt` uses `python-jose` for JWT instead of the plan's `authlib` for the
   Google OAuth flow — a reasonable substitution, but it is an undocumented deviation, and there is
   still no OAuth client library at all.

---

## 2. Bug status scoreboard

Severity: **CRITICAL** = wrong results returned silently to users / admin intent violated ·
**HIGH** = spec rule broken or crash · **MEDIUM** = wrong metric or resource overrun ·
**LOW** = correctness-adjacent hygiene.

| # | Bug | Severity | Status |
|---|---|---|---|
| B1 | `pair_score` goes negative — old repeats beat brand-new pairs | CRITICAL | **FIXED** |
| B2 | Two contradictory definitions of "has this pair met" | CRITICAL | **FIXED** |
| B3 | Lock application order-dependent — locks silently unsatisfied | CRITICAL | **STILL BROKEN** |
| B4 | Fairness pass runs after locks and breaks them | HIGH | **FIXED** |
| B5 | Remainder absorb puts every leftover student in one team | HIGH | **FIXED** |
| B6 | `validate_locks` misses most unsatisfiable locks | HIGH | **PARTIAL** |
| B7 | `form_teams` crashes on `team_size <= 0` | HIGH | **FIXED** |
| B8 | `saturation()` exceeds 1.0 / counts out-of-cohort pairs | MEDIUM | **FIXED** |
| B9 | `time_limit` not enforced inside a restart cycle | MEDIUM | **STILL BROKEN** |
| B10 | Duplicate student IDs put one student on a team twice | MEDIUM | **FIXED** |
| B11 | Fairness pass creates new violations | LOW | **PARTIAL** |
| B12 | First restart computed twice, `restarts` undercounts | LOW | **FIXED** |
| B13 | Lock input validation / silent skips | LOW | **PARTIAL** |
| B14 | Dead imports | LOW | **PARTIAL** |
| B15 | `algorithm` vs `backend.algorithm` import paths | LOW | **FIXED (code only)** |
| B16 | `.venv` + bytecode committed, no `.gitignore` | LOW | **FIXED** |
| N1 | `.gitignore` does not ignore `.env` (secret key + DB password) | HIGH | **NEW — OPEN** |
| N2 | Formation-service contract is wider than the algorithm's guarantees | MEDIUM | **NEW — OPEN** |
| N3 | Dead imports left by the B2 refactor (`swapper.py`) | LOW | **NEW — OPEN** |
| N4 | Documentation now contradicts the code | LOW | **NEW — OPEN** |
| N5 | Test gaps still hide every remaining failure | MEDIUM | **NEW — OPEN** |

**Net: 9 fixed, 3 partial, 4 still broken, 5 new open.**

---

## 3. Bugs that remain broken

### B3 — CRITICAL — the lock fixpoint loop oscillates instead of converging

`algorithm/engine.py:188-251`

`_apply_locks_fixpoint` re-checks locks and retries up to 20 iterations, but `_apply_one_lock` still
resolves a `together` lock by displacing **the first non-`a` member of `a`'s team**
(`engine.py:233-240`) with no regard for whether that member is itself locked. Two locks that share a
student therefore ping-pong: satisfying `s8≡s1` evicts `s1`'s other locked partner, and satisfying
that one evicts `s8`, for all 20 iterations.

Through the public API (26 students, team size 4, 40 random history pairs, one 3-person `together`
chain, 200 seeds):

```
unsatisfied 3-person together chain: 52/200 (26%)      [45% before the fix — reduced, not solved]
runs ending with non-empty unsatisfied_locks: 82/300
```

Minimal deterministic repro (9 students, team size 3, small history, `seed=0`):

```
locks:  s8+s1 together, s1+s2 together
teams:  [['s8','s1','s5'], ['s4','s7','s6'], ['s2','s0','s3']]
unsatisfied: [('s1','s2')]     # s1 and s8 stuck together, s2 evicted, fixpoint gave up
```

Original bug, for reference: locks were applied once in list order with no re-check, violating a
3-person chain in 27/60 runs and `_apply_locks` directly in 731/3000 randomized trials.

Credit where due: `unsatisfied_locks` is populated in **52 of 52** failing runs, so the result is at
least honest now. But `problem_final.md` §11 requires the run to abort and notify the admin
("Formation must never produce two sets of teams"; "Locks cannot be satisfied → admin is told before
formation runs"), and `FormationResult` is still returned as a success with teams attached. Nothing in
the algorithm layer raises, and nothing calls `validate_locks` first (see B6).

Fix: choose the displaced member by lock awareness — never evict a student who participates in a
satisfied `together` lock whose cluster is still inside that team; if no legal eviction exists, give up
immediately instead of thrashing. Drop `max_iterations` to 2–3 and treat exhaustion as a hard failure.
Better: seed locked clusters into `greedy.place` as pre-formed blocks instead of post-hoc swapping.

### B6 — HIGH (partial) — two whole classes of unsatisfiable locks are still undetected

`algorithm/engine.py:138-181`

Fixed: self-locks, same-pair `together`+`apart` contradictions, `apart` when everyone fits on one team
(when `n_students` is passed), and `together` clusters larger than `team_size`.

Still broken — contradiction detection intersects **exact pairs** (`together_pairs & apart_pairs`,
`engine.py:160`), not clusters, so a contradiction routed through a third student is invisible:

```
locks: a+b together, b+c together, a+c apart
validate_locks(locks, team_size=3, n_students=9)  -> []      # MISSED
validate_locks(locks, team_size=4, n_students=9)  -> []      # MISSED
```

Unsatisfiable by construction (a, b, c must share a team, yet a and c must be apart). It is only caught
today by accident, when the "all students fit on one team" rule fires for an unrelated reason.
Feasibility of `apart` edges is still not modelled at all:

```
locks: a apart from b,c,d,e,f   (7 students, team_size 3)
validate_locks(locks, 3, 7)     -> []      # MISSED: a needs a team to itself, min size is 3
```

And `n_students` defaults to `0`, which silently disables the one-team check:

```
validate_locks([Lock("a","b","apart")], team_size=4)              -> []    # check skipped
validate_locks([Lock("a","b","apart")], team_size=4, n_students=4) -> [error]
```

`form_teams` never calls `validate_locks`, so end-to-end:

```
form_teams(12 students, locks=[Lock("s0","s0","together")])  -> silently accepted, 0 unsatisfied
form_teams(12 students, locks=[Lock("s0","s1","together"),
                               Lock("s0","s1","apart")])    -> no exception, no abort;
                                                                one of the two silently applied
```

Original bug, for reference: only "together cluster > team_size" was detected; self-locks,
contradictions and impossible `apart` locks all returned `[]`.

Fix: build clusters first, then check every `apart` edge against cluster membership; compute
`n_teams` from the actual placement and test
`sum(len(c) - 1 for c in clusters_of_a) <= n_teams * (team_size - 1)`; make `n_students` a required
argument; call `validate_locks` from `form_teams` or enforce it in the formation service with a test.

### B9 — MEDIUM — `time_limit` is still only checked between restarts

The fix moved the clock read to the top of the loop body, which is where it already was. Nothing was
threaded into `swapper.optimise`, so one cycle still runs to completion and the overrun equals one full
`place()` + `swap_optimise()`:

```
N=200, k=5, 10,897 history pairs, time_limit=0.3s -> 0.54s  (1.81x), restarts=2
N=300, k=6,                  time_limit=0.5s  -> 0.74s  (1.48x), restarts=2
N=500, k=5,                  time_limit=0.5s  -> 0.21s  (0.41x, exits early at score 0)
```

The overrun grows with cohort size and history density, so the APScheduler deadline job (plan
§Scheduler) and any inline cap-hit formation can block well past its budget. Secondary issue unchanged:
`team_score` is still recomputed for both teams on every candidate swap (`swapper.py:37-43`), so
`algorithm_approach1.md:157`'s "O(1) per candidate swap" remains false.

Fix: add a `deadline: float | None` parameter to `optimise()`, checked between team pairs; pass
`start + time_limit` from `form_teams`; cache per-team scores instead of recomputing them.

### B11 — LOW (partial) — fairness pass still creates new violations

`algorithm/fairness.py:14-30`

The fixpoint loop reduced the failure rate from 166/3000 to **36/3000** randomized trials (~1.2%), but
`_try_fix` still verifies only the violating student and the incoming student
(`fairness.py:75-82`); the student swapped *out* into the other team is never re-checked, and
`max_passes=10` silently gives up:

```
before: [['s5','s9'], ['s1','s4','s7','s6'], ['s8','s3','s2','s0']]
after : [['s5','s3'], ['s1','s4','s7','s6'], ['s8','s9','s2','s0']]   # s3 now has an all-repeat team
```

Fix: after an accepted swap, re-evaluate both affected teams and reject the swap if the outgoing
student gains a violation; or re-run `_find_violations` on the two touched teams before keeping.

---

## 4. Partial fixes, remaining gaps

### B13 — LOW (partial) — locks naming unregistered students are still skipped silently

Fixed: `Lock(..., "sideways")` now raises `ValueError` (`engine.py:37-43`) and `FormationResult`
carries `unsatisfied_locks` (`engine.py:55`). Remaining: `_check_locks` `continue`s when a locked
student is not in any team (`engine.py:216-217`), so locks referring to non-registered students vanish
with no trace:

```
form_teams(["a","b","c","d"], 2, {}, locks=[Lock("a","zz","together")])
  -> teams=[['b','c'],['d','a']], unsatisfied_locks=0     # lock silently dropped
```

Either report them separately or reject them up front.

### B14 — LOW (partial) — dead imports remain in `swapper.py`

`deepcopy` was removed from `engine.py`, but `algorithm/swapper.py:10` still imports `pair_score` and
`pair_key`, neither used after switching to `has_met` (see N3).

### B15 — LOW — code fixed, docs still contradict it

`algorithm/__init__.py:5` now imports `algorithm.engine` and the package resolves as `algorithm`, so the
code path bug is gone. `implementation_plan.md:48-61, 254-261` still specifies
`backend/algorithm/` with `tests/` importing `backend.algorithm.*` and
`def form_teams(...) -> list[list[str]]`, while the code returns a `FormationResult` dataclass. See N4.

---

## 5. New issues found during verification

### N1 — HIGH — `.gitignore` does not ignore `.env`

`.gitignore` covers `.venv/`, `venv/`, `env/`, `__pycache__/`, `.pytest_cache/`, IDE dirs — but **not
`.env`**. `backend/.env.example:1-2` says "Copy this file to .env … Never commit .env to git", and
`backend/.env` will hold `SECRET_KEY` and the database password. The scaffold landed during this review
and `.env` is not excluded. Add `.env` / `*.env.local` while keeping `.env.example` tracked.

### N2 — MEDIUM — the formation-service contract is wider than the algorithm's guarantees

`backend/` is a scaffold only, so nothing has consumed the algorithm yet. Three obligations follow from
the fixes and are not reflected anywhere in the backend:

- `validate_locks(locks, team_size, n_students)` — the third argument is new and **required** for the
  `apart` check to run; the service must supply the registered count.
- `FormationResult.unsatisfied_locks` must be treated as a **failure**: abort the transaction, leave the
  activity unformed, notify the admin (plan §Formation Flow step 3, spec §11). Nothing in the algorithm
  layer enforces this.
- `saturation(history, n, registered=...)` — the service should pass the registered list, otherwise
  out-of-cohort pairs are counted (now clamped, but wrong).
- `backend/requirements.txt` is missing `apscheduler` (plan §Scheduler) and any Google OAuth client
  (`authlib` per the plan's stack; the file has `python-jose` for JWT only).

### N3 — LOW — dead imports left behind by the B2 refactor

`algorithm/swapper.py:10` still imports `pair_score` and `pair_key`; neither is used after the switch to
`has_met`. The B14 cleanup only touched `engine.py`.

### N4 — LOW — documentation now contradicts the code

`algorithm_approach1.md` still documents the removed formula and will mislead the next reader or agent:

- line 27: `score(A, B) = overlap_count[A][B] * 1000 - days_since_last_together[A][B]`
- lines 33-37: the entire "Why this works better than `1 / days`" argument rests on the old formula
- line 39: "Goal: minimize total score" — no mention of the new clamp

`implementation_plan.md:254-261` still declares `def form_teams(...) -> list[list[str]]` while the code
returns `FormationResult`. The new formula is documented only in the `algorithm/scorer.py` docstring, so
the two sources disagree. Pick the code as truth and update both `.md` files.

### N5 — MEDIUM — test gaps still hide every remaining failure

96 tests pass and none of them catch B3, B6, B9 or B11:

| Gap | Hides |
|---|---|
| `test_engine.py:254` uses exactly **one** lock; the only multi-lock engine tests (lines 185, 201) use `empty_history` (stage-1 path, where a single swap always succeeds) | B3's 26% failure |
| No test asserts `unsatisfied_locks` is **populated** for a genuinely unsatisfiable set — `test_unsatisfied_locks_field_exists` only checks `isinstance(..., list)` | B3, B6 |
| `test_met_once_recently` / `test_met_once_long_ago` now assert only `> 0`; nothing pins the count-primary invariant (`count=1` max < `count=2` min) | B1 regression |
| No cluster-level contradiction case; only the same-pair case | B6 |
| No assertion on `elapsed_seconds` vs `time_limit` (only `>= 0` at `test_engine.py:143`) | B9 |
| No randomized / multi-seed lock or fairness test | B3, B11 |

Minimum additions: a `test_all_locks_satisfied(result, locks)` invariant helper called by every engine
test that passes locks; a 3-lock chain over ≥100 seeds with history; assertions that `validate_locks`
catches a cluster contradiction and an `apart`-edge-infeasible set; and
`assert result.elapsed_seconds < time_limit * 1.5` on a dense-history case.

---

## 6. Fixes confirmed in the working tree

Recorded with the evidence used to close each one.

| # | Fix | Verification evidence |
|---|---|---|
| B1 | `pair_score` clamps recency into `[0, RECENCY_SCALE-1]` and adds it to `count * RECENCY_SCALE` (`scorer.py:31-41`) | min met-pair score = 1000 over counts 1–5 × ages 0…10⁶; never-met = 0; `count=1` max (1999) < `count=2` min (2000) — count is strictly primary |
| B2 | new `has_met()` (`scorer.py:26`), used by `count_new_pairs`, `_conflict_students`, `_new_pairs_in`, `_find_violations`, `_try_fix` | `has_met(a,b,h) == (pair_score(a,b,h) > 0)` on 20,000 randomized (count, days) combos → 0 mismatches |
| B4 | fairness now runs **before** lock application (`engine.py:85-86, 121-123`) | the old deterministic repro (`s0` locked with `p`, both repeats) now ends with the lock satisfied and `unfair_students=['s1']` honestly reported |
| B5 | `grew` set restricts absorb extras to distinct teams (`greedy.py:60-68`) | 62 students / team size 6 → `(6,)*10 + (7,7)` on 50/50 seeds (was one team of 8 on 40/40); 65/6 → ten 6s + one 5 |
| B7 | `team_size < 1` raises `ValueError` (`engine.py:67-68`) | `ValueError: team_size must be >= 1, got 0` |
| B8 | `saturation()` takes `registered` and clamps to `[0.0, 1.0]` (`scorer.py:66-84`); engine passes `registered=students` (`engine.py:126`) | 20 unrelated pairs with n=5 → 1.0 (clamped); with `registered=['a','b']` an out-of-cohort pair is excluded |
| B10 | duplicate IDs raise `ValueError` (`engine.py:71-73`) | `ValueError: students list contains duplicate IDs: ['a']` |
| B12 | best seeded before the loop, `score == 0` checked before entering (`engine.py:96-102`) | `restarts=0` ↔ `place()` calls = 1 |
| B16 | `.gitignore` added; `.venv` and bytecode untracked | tracked `.venv` files 1393 → 0; tracked `__pycache__` 665 → 0 |

---

## 7. Fix order for what remains

1. **B3** — lock-aware eviction + treat `max_iterations` exhaustion as an error; wire
   `unsatisfied_locks` into an abort path.
2. **B6** — cluster-based contradiction detection, `apart` edge feasibility, `n_students` required,
   and actually call `validate_locks` from the formation path.
3. **N1** — add `.env` to `.gitignore` before `backend/.env` is created.
4. **B9** — thread a deadline into `swapper.optimise`, cache team scores.
5. **N2** — hold the formation service to the new contract as it is written (still 0% built).
6. **N5** — add the invariant/randomized tests above so the next regression cannot hide.
7. **B11, B13, B14/N3, N4** — cleanups and doc corrections.
