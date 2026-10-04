# Cohort Shuffle — Bug Fix Verification Report

Date: 2026-10-04
Verifies the fixes for `reports/bugs_report.md` (B1–B16) against the **working tree**, not the docs.
Code state: uncommitted changes on top of `318f7d1` ("bug fixes for engine") — 6 algorithm files
modified, 2 test files extended (80 → 96 tests, all passing), `.gitignore` added, `backend/`
scaffolded.

Method: every bug re-tested by re-running the original reproduction against the current code, plus
new adversarial probes aimed at the fixes themselves (randomized seeds, boundary values, and direct
calls to the new internal helpers).

---

## 1. Scoreboard

| # | Bug | Status | Evidence |
|---|---|---|---|
| B1 | Negative `pair_score` for old repeats | **FIXED** | min met-pair score = 1000 over counts 1–5 × ages 0…10⁶; never-met = 0; `count=1` max (1999) < `count=2` min (2000) |
| B2 | Two contradictory "has met" checks | **FIXED** | `has_met(a,b,h) == (pair_score(a,b,h) > 0)` on 20,000 randomized (count, days) combos → 0 mismatches; `has_met` used in `count_new_pairs`, `_conflict_students`, `_new_pairs_in`, `_find_violations`, `_try_fix` |
| B3 | Locks silently unsatisfied | **STILL BROKEN** | 3-person `together` chain still unsatisfied in **52/200 runs (26%)**; the new fixpoint loop oscillates instead of converging |
| B4 | Fairness pass breaks locks | **FIXED** | order swapped (fairness → locks); the old deterministic repro now ends with the lock satisfied and `unfair_students=['s1']` honestly reported |
| B5 | All remainder extras land on team 0 | **FIXED** | 62 students / team size 6 → `(6,)*10 + (7,7)` on 50/50 seeds (was `(8)` on 40/40) |
| B6 | `validate_locks` misses unsatisfiable locks | **PARTIAL** | self-lock, pairwise contradiction, one-team `apart`, cluster > team_size detected. **Cluster-level contradiction and `apart` edge-infeasibility still missed** |
| B7 | `team_size <= 0` crash | **FIXED** | `ValueError: team_size must be >= 1, got 0` |
| B8 | `saturation()` > 1.0 / counts outsiders | **FIXED** | 20 unrelated pairs with n=5 → 1.0 (clamped); with `registered=[...]` out-of-cohort pairs excluded; engine passes `registered=students` |
| B9 | `time_limit` overrun | **STILL BROKEN** | no deadline inside `swapper.optimise`; measured 1.81× at N=200, 1.48× at N=300 |
| B10 | Duplicate student IDs | **FIXED** | `ValueError: students list contains duplicate IDs: ['a']` |
| B11 | Fairness creates new violations | **PARTIAL** | 166/3000 → **36/3000** residual; fixpoint cap reached, incoming-student-only check remains |
| B12 | Double-computed first restart | **FIXED** | `restarts=0` ↔ `place()` calls = 1 |
| B13 | Lock input validation / silent skips | **PARTIAL** | `Lock(..., "sideways")` → `ValueError`; `unsatisfied_locks` reported honestly (52/52). Locks naming unregistered students are still skipped **silently** |
| B14 | Unused imports | **PARTIAL** | `deepcopy` removed from `engine.py`; `pair_score`/`pair_key` still imported unused in `swapper.py:10` |
| B15 | `algorithm` vs `backend.algorithm` paths | **FIXED (code)** | `algorithm/__init__.py:5` now imports `algorithm.engine`. **Docs still contradict the code** (see §4) |
| B16 | `.venv` + bytecode committed | **FIXED** | tracked `.venv` files 1393 → 0; tracked `__pycache__` 665 → 0; `.gitignore` present |

**Net: 9 fixed, 3 partial, 4 still broken.** Test suite grew 80 → 96 and passes.

---

## 2. Still-broken bugs in detail

### B3 (CRITICAL, not fixed) — the fixpoint loop oscillates instead of converging

`algorithm/engine.py:188-251`

`_apply_locks_fixpoint` re-checks locks and retries up to 20 iterations, but `_apply_one_lock` still
resolves a `together` lock by displacing **the first non-`a` member of `a`'s team**
(`engine.py:233-240`) with no regard for whether that member is itself locked. Two locks that share a
student therefore ping-pong: fixing `s8≡s1` evicts `s1`'s other locked partner, and fixing that one
evicts `s8`, for all 20 iterations.

Through the public API (26 students, team size 4, 40 random history pairs, one 3-person `together`
chain, 200 seeds):

```
unsatisfied 3-person together chain: 52/200 (26%)     [was 27/60 = 45% before the fix]
runs ending with non-empty unsatisfied_locks: 82/300
```

Minimal deterministic repro (9 students, team size 3, small history, `seed=0`):

```
locks:  s8+s1 together, s1+s2 together
teams:  [['s8','s1','s5'], ['s4','s7','s6'], ['s2','s0','s3']]
unsatisfied: [('s1','s2')]      # s1 and s8 stuck together, s2 evicted, fixpoint gave up
```

Credit where due: `unsatisfied_locks` is populated in **52 of 52** failing runs, so the result is at
least *honest* now. But `problem_final.md` §11 requires the run to abort and notify the admin
("Formation must never produce two sets of teams"; "Locks cannot be satisfied → admin is told before
formation runs"), and `FormationResult` is still returned as a success with teams attached. Nothing in
the algorithm layer raises.

Fix: choose the displaced member by lock awareness — never evict a student who participates in a
satisfied `together` lock whose cluster is still inside that team; if no legal eviction exists, give
up immediately instead of thrashing. Also drop `max_iterations` to something small (2–3) and treat
"iteration limit reached" as a hard failure rather than a result. Better still, seed the locked
clusters into `greedy.place` as pre-formed blocks instead of post-hoc swapping.

### B6 (HIGH, partial) — two whole classes of unsatisfiable locks still undetected

`algorithm/engine.py:138-181`

Contradiction detection intersects **exact pairs** (`together_pairs & apart_pairs`,
`engine.py:160`), not clusters, so a contradiction routed through a third student is invisible:

```
locks: a+b together, b+c together, a+c apart
validate_locks(locks, team_size=3, n_students=9)  -> []      # MISSED
validate_locks(locks, team_size=4, n_students=9)  -> []      # MISSED
```

This is unsatisfiable by construction (a,b,c must share a team, yet a and c must be apart). It only
gets caught today by accident, when the "all students fit on one team" rule happens to fire for some
other reason. Feasibility of `apart` edges is still not modelled at all:

```
locks: a apart from b,c,d,e,f   (7 students, team_size 3)
validate_locks(locks, 3, 7)     -> []      # MISSED: a needs a team to itself, min size is 3
```

And `n_students` defaults to `0`, which silently disables the one-team check:

```
validate_locks([Lock("a","b","apart")], team_size=4)            -> []   # check skipped
validate_locks([Lock("a","b","apart")], team_size=4, n_students=4) -> [error]
```

`form_teams` never calls `validate_locks` at all, so end-to-end:

```
form_teams(12 students, locks=[Lock("s0","s0","together")])       -> silently accepted, 0 unsatisfied
form_teams(12 students, locks=[Lock("s0","s1","together"),
                               Lock("s0","s1","apart")])         -> no exception, no abort;
                                                                     one of the two applied
```

Fix: build clusters first, then check every `apart` edge against cluster membership; compute
`n_teams = len(teams)` from the actual placement and test `sum(len(c)-1 for c in clusters of a) <=
n_teams * (team_size - 1)`; make `n_students` a required argument; call `validate_locks` from
`form_teams` (or make the formation service the only caller and enforce it there with a test).

### B9 (MEDIUM, not fixed) — `time_limit` still only checked between restarts

The "fix" moved the clock read to the top of the loop body, which is where it already was. Nothing was
threaded into `swapper.optimise`, so one cycle still runs to completion:

```
N=200, k=5, 10,897 history pairs, time_limit=0.3s -> 0.54s  (1.81x), restarts=2
N=300, k=6,             time_limit=0.5s        -> 0.74s  (1.48x), restarts=2
N=500, k=5,             time_limit=0.5s        -> 0.21s  (0.41x, exits early at score 0)
```

The overrun equals one full `place()` + `swap_optimise()` cycle and grows with cohort size and history
density, so the APScheduler deadline job (plan §Scheduler) can block well past its budget. Secondary
issue unchanged: `team_score` is still recomputed for both teams on every candidate swap
(`swapper.py:37-43`), so `algorithm_approach1.md:157`'s "O(1) per candidate swap" remains false.

Fix: add a `deadline: float | None` parameter to `optimise()` (and to the swap-pass loop, checked
between team pairs), pass `start + time_limit` from `form_teams`, and cache per-team scores instead of
recomputing them.

### B11 (LOW, partial) — fairness still creates new violations

`algorithm/fairness.py:14-30`

The fixpoint loop is an improvement (166/3000 → 36/3000 randomized trials) but `_try_fix` still only
verifies the violating student and the incoming student (`fairness.py:75-82`); the student swapped
*out* into the other team is never re-checked, and `max_passes=10` silently gives up. Residual rate
~1.2%:

```
before: [['s5','s9'], ['s1','s4','s7','s6'], ['s8','s3','s2','s0']]
after : [['s5','s3'], ['s1','s4','s7','s6'], ['s8','s9','s2','s0']]   # s3 now has an all-repeat team
```

Fix: after an accepted swap, re-evaluate both affected teams and reject the swap if the outgoing
student gains a violation; or simply re-run `_find_violations` on the two touched teams before keeping.

---

## 3. New issues found in the fixes

### N1 (HIGH) — `.gitignore` does not ignore `.env`, and one now exists in the tree

`.gitignore` covers `.venv/`, `venv/`, `env/`, `__pycache__/`, `.pytest_cache/`, IDE dirs — but **not
`.env`**. `backend/.env.example:1-2` says "Copy this file to .env … Never commit .env to git", and
`backend/.env` will hold `SECRET_KEY` and the database password. The scaffold landed at 22:41 and
`backend/.env` is not excluded. Add `.env` and `*.env.local` to `.gitignore` (keeping `.env.example`
tracked).

### N2 (MEDIUM) — the formation service contract is now wider than the algorithm's guarantees

The backend scaffold (`backend/app/main.py`, `config.py`, `database.py`, `requirements.txt`) appeared
during this review. It is still Phase 1 item 1 only — routers, models, schemas and services are empty
stubs, `backend/alembic/` has no files, so plan progress is unchanged at ~11%. Three integration
requirements follow from the B-fixes and are not yet reflected anywhere in the backend:

- `validate_locks(locks, team_size, n_students)` — the third argument is new and **required** for the
  `apart` check to run; the service must supply the registered count.
- `FormationResult.unsatisfied_locks` must be treated as a **failure**: abort the transaction, leave
  the activity unformed, and notify the admin (plan §Formation Flow step 3, spec §11). Nothing in the
  algorithm layer enforces this.
- `saturation(history, n, registered=...)` — the service should pass the registered list, otherwise
  out-of-cohort pairs are counted (now clamped, but wrong).
- `backend/requirements.txt` is missing `apscheduler` (plan §Scheduler) and any Google OAuth client
  (`authlib` per the plan's tech stack; the file has `python-jose` for JWT only, which is a reasonable
  substitution but should be recorded as a deviation).

### N3 (LOW) — dead imports left behind by the B2 refactor

`algorithm/swapper.py:10` still imports `pair_score` and `pair_key`, neither of which is used after
switching to `has_met`. The B14 pass only cleaned `engine.py`.

### N4 (LOW) — documentation now contradicts the code

`algorithm_approach1.md` still documents the removed formula and will mislead the next reader or agent:

- line 27: `score(A, B) = overlap_count[A][B] * 1000 - days_since_last_together[A][B]`
- line 39: "Total score … Goal: minimize total score" (no mention of the new clamp)
- line 33-37: the entire "Why this works better than 1/days" argument rests on the old formula

`implementation_plan.md:254-261` still declares `def form_teams(...) -> list[list[str]]`, while the code
returns a `FormationResult` dataclass. The docstring header of `algorithm/scorer.py` records the new
formula, so the two sources disagree. Pick the code as truth and update both `.md` files.

### N5 (LOW) — test gaps that still hide every remaining failure

| Gap | Hides |
|---|---|
| `test_engine.py:254` uses exactly **one** lock; the only multi-lock engine tests (lines 185, 201) use `empty_history` (stage-1 path, where a single swap always works) | B3's 26% failure |
| No test asserts `unsatisfied_locks` is **populated** for a genuinely unsatisfiable set — `test_unsatisfied_locks_field_exists` only checks `isinstance(..., list)` | B3, B6 |
| `test_met_once_recently` / `test_met_once_long_ago` now assert only `> 0`; nothing pins the count-primary invariant (`count=1` max < `count=2` min) | B1 regression |
| No cluster-level contradiction case; only the same-pair case | B6 |
| No assertion on `elapsed_seconds` vs `time_limit` (only `>= 0` at `test_engine.py:143`) | B9 |
| No randomized/multi-seed lock or fairness test | B3, B11 |

Minimum additions: a `test_all_locks_satisfied(result, locks)` invariant helper called by every engine
test that passes locks; a 3-lock chain over ≥100 seeds with history; an assertion that
`validate_locks` catches a cluster contradiction and an `apart`-edge-infeasible set; and
`assert result.elapsed_seconds < time_limit * 1.5` on a dense-history case.

---

## 4. Fix order for what remains

1. **B3** — lock-aware eviction + treat `max_iterations` exhaustion as an error; wire
   `unsatisfied_locks` into an abort path.
2. **B6** — cluster-based contradiction detection, `apart` edge feasibility, `n_students` required,
   and actually call `validate_locks` from the formation path.
3. **B9** — thread a deadline into `swapper.optimise`, cache team scores.
4. **N1** — add `.env` to `.gitignore` before `backend/.env` is created.
5. **B11**, **N3**, **N4**, **N5** — cleanups and the test additions above.
6. **N2** — hold the formation service to the new contract as it is written (still 0% built).
