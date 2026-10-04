# Cohort Shuffle — Problem Draft 2

---

## 1. Problem

In classes and institutions, when students are allowed to form their own teams, the same people keep working together. Friend groups and habit-driven pairings repeat activity after activity. Students miss chances to work with classmates they don't know, and cohort-wide mixing never happens.

Asking a teacher to manually rotate teams does not scale. Remembering who worked with whom across many activities is not realistic for a human.

---

## 2. Idea

An application that automatically forms teams for each activity so that, across the activities in a cohort, every student works with as many different classmates as possible. The system remembers every past teammate pairing and uses that history to minimize repeats.

Core principle: no one chooses their teammates; the system shuffles, using history, to maximize new interactions.

The goal is to get students to work with new people. The system does not try to measure how deeply they interact. If two students were on the same team, they count as having worked together, and that is accepted even though real life is messier.

---

## 3. Scale and Scope

- Current target: fewer than 200 students per cohort.
- Intended future: any institution with many classes. The design must not assume one global pool.
- The unit of mixing is the cohort (a class, batch, or academic-year group). History and team formation are scoped to a cohort. Students in different cohorts are never mixed.
- At under 200 students per cohort, the full pairwise history fits trivially in memory (about 20,000 pairs). The system can use a simple heuristic search rather than anything distributed.

---

## 4. Actors

| Actor   | Can do |
|---------|--------|
| Admin   | Create an activity. Optionally set a participant cap or add locks. Add late students. Re-run or adjust teams if something goes wrong. |
| Student | Log in. See all posted activities. Register for the ones they want. View their current team and past teams. |

The admin does not pick team members by default. The only required team-related input from the admin is the team size. Locks and a participant cap are optional.

Students who have a concern or a problem contact the admin. The admin handles late additions, dropouts, and any special requests.

---

## 4.1 Activity Creation Form

**Required fields:**

- Activity / task / event name
- Team size
- Duration
- Date and time

**Optional fields:**

- Participant cap (number input). If set, registration closes once that many students have registered, on a first-come first-served basis. Leave blank for no cap.
- Locks (structured input). The admin selects students from a list and chooses a constraint type: "must be together" or "must be apart". Multiple lock rules can be added. Leave empty for no locks.

**Registration deadline (mandatory):**

- Admin sets this explicitly. The form displays a prominent warning: "Set the deadline at least 20 minutes before the event start time."
- Exception: if the gap between post time and event time is 20 minutes or less, the system automatically fixes the deadline to event time − 2 minutes. The admin cannot override this; the field is locked and the reason is shown.
- The deadline is always displayed to students on the Activities page.

Venue is not a required system field; the admin may include it in the activity name or notes if needed.

---

## 4.2 Lock Constraints

The admin may fix certain students relative to each other before formation runs. Two constraint types are supported:

- **Must be together:** the named students are placed on the same team.
- **Must be apart:** the named students are placed on different teams.

These are entirely the admin's call. The system treats locked students as fixed constraints and shuffles the rest of the cohort around them.

If the locks cannot be satisfied (e.g., a "must be together" group is larger than the team size), the admin is told before formation runs. The system does not guess or partially apply the constraint. The admin must correct the locks.

---

## 5. Pages

- **Activities** — all posted activities. Each shows: activity name, date, duration, team size, registration deadline, and registration status. Students register here.
- **Student Teams** — the student's current team and full history. Each entry shows: activity name, team number, teammates, date, duration.

---

## 6. Lifecycle of an Activity

1. Admin posts activity (name, team size, duration, date and time; optional cap and locks).
2. Activity is immediately visible to all students in the cohort.
3. Students register individually for activities they want to join. Visibility is not participation.
4. If a cap is set, registration closes when the cap is reached. Formation runs immediately once the cap is filled.
5. If no cap is set, registration stays open until the deadline. Formation runs automatically at the deadline.
6. Teams are locked and visible on the Student Teams page.
7. Admin handles any late arrivals or dropouts manually.

**Key rules:**

- Only registered students are included in team formation. Logging in alone does not count.
- When a cap is set, the participant list is finalized as soon as the cap is reached and shuffling runs at that point.
- When no cap is set, the total number of participants is unknown until the deadline. The admin never enters a headcount.
- Once teams are formed they are locked.

---

## 6.1 Registration Deadline Rule

The deadline is a mandatory field on the activity creation form. The admin sets it directly.

- The form shows a prominent warning above the deadline field: **"Set the deadline at least 20 minutes before the event start time."**
- If the gap between post time and event time is **20 minutes or less**, the system locks the deadline automatically to event time − 2 minutes. The field is not editable in this case and the reason is displayed to the admin.
- In all other cases, the admin chooses the deadline freely. There is no system-enforced minimum beyond the advisory warning.

The deadline is always shown explicitly to students on the Activities page. It is never a hidden internal value.

---

## 7. Team Formation Logic

### 7.1 Success Criterion

Success means the fewest possible repeats overall. In early activities, zero repeats is achievable and is the target. After enough activities, zero repeats becomes impossible; the system then minimizes repeats as much as it can. That is a normal result, not a failure.

Some repeats within a team are acceptable. A team of seven can have members who have worked together before. The real failure condition is a student who gets no new teammate at all on their team.

### 7.2 First Activity in a Cohort

No history exists. Assign teams randomly.

### 7.3 Later Activities

Use history. Prefer pairings between students who have not worked together before.

### 7.4 When Repeats Are Unavoidable

Zero repeats is only possible for a limited number of activities (for 62 students and team size 6, roughly 7 activities). After that, repeats are forced. The preference order:

1. Prefer pairs who have worked together fewer times.
2. Among equal counts, prefer pairs who worked together longest ago. Example: if A worked with X one month ago and with Y one year ago, prefer pairing A with Y.

### 7.5 Fairness Goal

Every student should have at least one teammate they have not worked with (or have not worked with recently). A solution that gives one student a team of entirely repeat partners is worse than a slightly higher-repeat-total solution that spreads the repeats evenly. The system must not sacrifice one student's experience to improve the aggregate count.

### 7.6 Uneven Headcount

When participants do not divide evenly by team size, let `r = participants mod team_size`:

- `r = 0`: all teams are exactly team size.
- `r >= team_size / 2` (round up for exact half): the leftover students form one smaller team.
- `r < team_size / 2`: leftover students are absorbed into existing teams (those teams become team size + 1), choosing the teams with least prior overlap among their members.
- Special case: if absorbing would leave a team of one, absorb that student into an existing team instead of creating a solo team.

Example with team size 6: 62 students → r = 2, absorb. 65 students → r = 5, new team. r = 3 (exactly half) → new team.

### 7.7 Search Strategy

The number of possible team arrangements is astronomically large for any real cohort size, so exhaustive search is impossible. The goal is a good arrangement, not a provably optimal one. A greedy placement followed by local improvement (e.g., swap-based refinement) is sufficient.

---

## 8. History

- Every time two students are placed on the same team, that pairing is recorded with the activity date and the cohort.
- History is scoped per cohort. A pairing in one cohort has no effect on formation in another cohort.
- History applies to every student who was placed on a team, regardless of whether they attended. Attendance tracking is a later enhancement.
- History lasts for the student's enrollment in the cohort.
- When a student leaves, their data is archived, not deleted, because it remains part of other students' history.
- All history can be derived from team membership records. No separate history table is needed.

---

## 9. Multi-Cohort Membership

A student may belong to more than one cohort simultaneously (e.g., enrolled in two courses that each run their own activities). This is supported.

Cohort histories are fully independent. A pairing recorded in cohort A is invisible to formation in cohort B. Every pairing record is tagged with a cohort ID, and formation only reads pairings within the same cohort.

---

## 10. Fallbacks and Exception Handling

| Situation | Behavior |
|-----------|----------|
| Zero-repeat teams impossible | Use the minimum-repeat result silently. No admin confirmation needed. |
| Student wants to register after the deadline | Registration is blocked. Admin may add the student to an existing team or let them sit out. |
| Student drops out after teams are formed | The team stays as is. Admin may add a replacement. No automatic re-shuffle. |
| Participant cap reached | Registration closes. Students who missed the cap are not registered. Order is by registration timestamp. |
| A registered student unregisters while a cap is set and before the deadline | Their spot is freed; the next student to register may take it. |
| No locks, no cap set | Default behavior only. |
| Locks cannot be satisfied | Admin is told before formation runs. The system does not guess. Admin corrects the locks. |
| Fewer registered students than team size | One team containing everyone. |
| No one registered | No teams formed. Activity is marked as having no participants. |
| Remainder would produce a team of one | Absorb that student into an existing team. |
| Formation job fails or does not run at the deadline | Admin can trigger formation manually. Formation must never produce two sets of teams for one activity. |
| Admin dislikes the result | Admin may re-run formation (only before the activity has started) or edit teams manually. Each run is logged. |
| Student is "exhausted" (has worked with everyone registered) | Apply repeat-minimizing rules from section 7.4 (count, then recency). |

---

## 11. Assumptions

- A formed team counts as "worked together" even if a member does not show up.
- Students may belong to more than one cohort. History is always cohort-scoped.
- Activities are team-based group work. Individual tasks are out of scope.
- The admin is the single point of contact for exceptions. Students do not self-manage edge cases.
