# Cohort Matching Algorithm

---

## Approach

The goal is to assign students into teams such that they work with as many different people as possible across activities. The approach minimizes repeated teammate pairings using interaction history.

Three stages handle the full lifecycle:

**Stage 1 — No history (first activity)**
Pure random assignment. Shuffle registered students and split by team size.

**Stage 2 — History exists (subsequent activities)**
Use a Randomized Greedy Placement algorithm with adaptive swap optimization. Place students into teams that minimize prior overlap. Escalate optimization effort based on how many conflicts exist.

**Stage 3 — Student exhausted (worked with everyone registered)**
Switch to time-based priority. Re-pair with whoever they worked with the longest time ago. Handled automatically by the unified scoring function — no explicit mode switch needed.

---

## Scoring Function

A single unified function scores any pair (A, B). No explicit mode switching — the formula handles all three stages naturally.

```
score(A, B) = overlap_count[A][B] * 1000 - days_since_last_together[A][B]
```

- If A and B have never worked together: `overlap_count = 0`, so `score = 0`. Best possible.
- If they have worked together: score is penalized by count (primary) and recency (tiebreaker). Higher count = worse. More recent = worse.
- If a student is exhausted (worked with everyone): all their pairs have `overlap_count > 0`, so the formula automatically falls back to recency as the differentiator.

**Why this works better than `1 / days`:**
- No division by zero when two activities happen on the same day.
- Count and recency are on a consistent numeric scale — they are always comparable.
- No mixed-unit problem between the two scoring modes.

Total score of an arrangement = sum of `score(A, B)` for every pair (A, B) that shares a team.
Goal: minimize total score.

---

## Tie-Breaking Rule

When multiple arrangements have the same (or within-epsilon) total score, prefer the one that introduces the most new pairs:

```
new_pairs = count of (A, B) in this arrangement where overlap_count[A][B] == 0
```

Selection key (two-key sort):

```
primary:   total score      → ascending  (lower is better)
secondary: new_pairs        → descending (more new pairs is better)
```

This ensures that among equally-scored arrangements, the one maximizing fresh interactions is chosen — the easiest win for the system's core goal.

---

## Algorithm

### Step 1 — Build Interaction History

From `team_members`, compute for every pair (A, B):
- `overlap_count[A][B]` — number of times they have been in the same team
- `days_since_last_together[A][B]` — days elapsed since their most recent shared activity

No separate history table needed — derived entirely from `team_members`.

---

### Step 2 — Phase 1: Randomized Greedy Placement

```
1. For each student, compute their overlap load:
       overlap_load[S] = sum of overlap_count[S][X] for all X in registered students

2. Sort students descending by overlap_load + small random jitter
       (most conflicted students placed first; jitter ensures restarts differ)

3. For each student in sorted order:
       compute score of placing them into each existing team
       place them into the team with the lowest marginal score

4. Apply remainder rule (see below) to handle leftover students

5. Calculate total score and new_pairs for this arrangement
```

---

### Step 3 — Phase 2: Conditional Escalation

Check the total score and decide how much optimization effort to invest.

Thresholds scale with cohort size to avoid hardcoding values that break at different scales:

```
total_pairs = N * (N - 1) / 2

low_threshold    = total_pairs * 0.002   (0.2% of all possible pairs)
medium_threshold = total_pairs * 0.01    (1% of all possible pairs)
```

Examples:
| N   | total_pairs | low  | medium |
|-----|-------------|------|--------|
| 26  | 325         | ~1   | ~3     |
| 62  | 1891        | ~4   | ~19    |
| 200 | 19900       | ~40  | ~199   |

Escalation logic:

```
score == 0          → perfect result, stop immediately

score <= low        → run swap optimization once

score <= medium     → run 10 random restarts of Phase 1
                      run swap optimization after each restart
                      keep best by (score ASC, new_pairs DESC)

score > medium      → run 100 random restarts of Phase 1
                      run swap optimization after each restart
                      keep best by (score ASC, new_pairs DESC)
```

---

### Step 4 — Phase 3: Swap Optimization

Run when triggered by escalation:

```
repeat until no improvement:
    for every pair of teams (Team i, Team j):
        for every student X in Team i:
            for every student Y in Team j:
                score_before = score(Team i) + score(Team j)
                swap X and Y
                score_after = score(Team i) + score(Team j)

                if score_after < score_before:
                    keep swap (improvement found)
                elif score_after == score_before:
                    keep swap only if new_pairs improves (tie-break)
                else:
                    revert swap

    if no swap in this full pass improved the result:
        stop (local optimum reached)
```

Only the two affected teams are re-scored per swap check — O(1) per candidate swap.

---

### Step 5 — Fairness Pass

After swap optimization, enforce the fairness constraint:

```
for each student S:
    teammates = other members of S's team
    if all teammates have overlap_count[S][T] > 0:
        S has no new teammate — flag as fairness violation

for each flagged student S:
    search all other teams for a student T where overlap_count[S][T] == 0
    if found:
        try swapping T with a member of S's team
        if the swap resolves S's violation without creating a new one:
            keep the swap
    if not found (S is truly exhausted):
        no fix possible — already handled by time-based scoring
```

A result with a slightly higher total score but no fairness violations is always preferred over a lower-score result that leaves any student with a full team of repeat partners.

---

## Remainder Rule

```
remainder = N % team_size

remainder == 0                    → all teams exactly team_size
remainder > team_size / 2         → form one new smaller team with remainder students
remainder <= team_size / 2        → distribute remainder students into existing teams
                                    (one per team, choosing teams with least overlap with them)
                                    those teams grow to team_size + 1
special case: remainder == 1      → always absorb (a team of one is never formed)
```

Boundary: exactly half (remainder == team_size / 2) forms a new smaller team.

| N  | team_size | remainder | action          |
|----|-----------|-----------|-----------------|
| 62 | 6         | 2         | absorb          |
| 63 | 6         | 3         | new small team  |
| 64 | 6         | 4         | new small team  |
| 65 | 6         | 5         | new small team  |
| 61 | 6         | 1         | absorb (special)|

---

## Full Flow Summary

```
registered students for this activity
          ↓
first activity?
   yes → random shuffle + split → done
   no  ↓
build interaction history (overlap_count, days_since_last_together)
          ↓
compute overlap loads → sort descending + jitter
          ↓
Phase 1: greedy placement → score + new_pairs
          ↓
score == 0?          → done
score <= low?        → one swap pass
score <= medium?     → 10 restarts + swap, keep best (score ASC, new_pairs DESC)
score > medium?      → 100 restarts + swap, keep best (score ASC, new_pairs DESC)
          ↓
Phase 3: fairness pass — fix any student with zero new teammates
          ↓
final team assignment persisted
```

## Scaling and Efficiency

The algorithm stays fast by design. These rules apply at every scale:

### 1. Keep pools small by design

The algorithm runs per cohort, not per institution. Many classes of 50–200 students each is just many small independent problems. A single pool of 10,000 students may never exist. Each cohort runs its own formation quickly and without interfering with others.

### 2. Store only pairs that have actually worked together

Do not maintain a full N×N matrix. Most pairs in early activities have never met — storing zeros for them wastes memory and slows the greedy step. Instead, use a sparse structure (dictionary of dictionaries or a database index on student pairs):

```
pair_history[(A, B)] = (overlap_count, last_activity_date)
```

Only entries where `overlap_count > 0` exist. A missing key means the pair has never worked together — score is 0 by definition. Past pairs are a tiny fraction of all possible pairs, so this structure stays small throughout the cohort's lifetime.

### 3. Only try swaps for students who currently have a repeat

Most students in early activities have zero repeats on their team. Checking every possible swap pair is wasteful. Instead:

```
conflict_students = {S for S in all_students if any(overlap_count[S][T] > 0 for T in S's team)}
```

Only attempt swaps involving at least one student from `conflict_students`. In early activities this set is empty and the swap phase is skipped entirely.

### 4. Replace fixed restart count with a time limit

Instead of always running exactly 10 or 100 restarts, run until either:
- The result is already optimal (score == 0), or
- A time budget is exhausted (e.g., 2 seconds for ≤200 students)

```
start = now()
best = initial_greedy()
while now() - start < TIME_LIMIT:
    candidate = greedy_with_jitter() + swap_optimize()
    if better(candidate, best):
        best = candidate
    if best.score == 0:
        break
```

This naturally adapts: easy problems finish in milliseconds, harder ones use the full budget. The time limit can be tuned per deployment (tighter for interactive use, looser for background jobs).

### 5. Fallback for very large pools

If a cohort ever grows unusually large (e.g., a mega-class or a misconfigured merge):

- **First choice:** use numpy for the scoring matrix operations. Dense numpy arrays with vectorized pair scoring are 10–100× faster than pure Python loops.
- **Second choice:** split the pool into random sub-pools (e.g., groups of 100), run the algorithm on each independently, then merge. This sacrifices global optimality slightly but keeps runtime linear.
- **Third choice:** rewrite the hot loop in a compiled extension (Cython, Rust via PyO3) if the above are insufficient.

In practice, with cohorts under 200 students and sparse pair history, none of these fallbacks should be needed.

---

## Saturation Warning

Track pair saturation after every formation run:

```
saturation = len(pair_history) / (N * (N - 1) / 2)
```

| Saturation | Meaning | Action |
|------------|---------|--------|
| < 80% | Healthy — new pairings still plentiful | None |
| ≥ 80% | Approaching exhaustion | Show admin warning |
| ~100% | Fully exhausted — all pairs have worked together | Fairness guarantee no longer possible |

When saturation crosses 80%, surface this message to the admin after formation:

> "Most students in this cohort have now worked with everyone else. New pairings are running low. Results from here will have more repeats. Consider expanding the cohort if this matters."

This is not an error. The system continues running and produces the best possible result under repeat-minimizing rules. The warning exists so the admin understands the context, not to block anything.

The fairness constraint (every student gets at least one new teammate) is silently relaxed once saturation reaches 100% — at that point it is mathematically impossible and the system switches fully to recency-based scoring.

---

## Implementation Speed by Cohort Size

The algorithm logic does not change with cohort size. Only the inner loop implementation is swapped for speed:

| Cohort size | Approach |
|-------------|----------|
| ≤ 200 | Pure Python, current algorithm — fast enough |
| 200–500 | Switch pair scoring to numpy vectorized operations |
| 500+ | Should not exist by design (split into sub-cohorts); if unavoidable, split into random groups of ~150 and run independently |

The scoring function, greedy placement, swap logic, fairness pass, and tie-breaking rules are identical across all tiers. Only the data structure under the scoring step changes.

---

## Theoretical Ceiling

Zero-repeat assignment is only possible up to a mathematical limit:

```
unique_pairs(N)            = N * (N - 1) / 2
pairs_per_activity(N, k)   = (N // k) * C(k, 2) + C(N % k, 2)
max_zero_repeat_activities = floor(unique_pairs(N) / pairs_per_activity(N, k))
```

| Team Size | Max zero-repeat activities (62 students) |
|-----------|------------------------------------------|
| 2         | ~39                                      |
| 3         | ~19                                      |
| 4         | ~13                                      |
| 5         | ~9                                       |
| 6         | ~7                                       |
| 7         | ~6                                       |

After the ceiling, the algorithm transitions automatically via the unified scoring function — time-based recency takes over and the algorithm always produces a result without blocking or erroring.
