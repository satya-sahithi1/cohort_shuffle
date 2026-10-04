1. Problem

In classes and institutions, when students are allowed to form their own teams, the same people keep working together. Friend groups and habit-driven pairings repeat activity after activity. Students miss chances to work with classmates they don't know, and cohort-wide mixing never happens.

Asking a teacher to manually rotate teams does not scale. Remembering who worked with whom across many activities is not realistic for a human.

2. Idea

An application that automatically forms teams for each activity so that, across the activities in a cohort, every student works with as many different classmates as possible. The system remembers every past teammate pairing and uses that history to minimize repeats.

Core principle: no one chooses their teammates; the system shuffles, using history, to maximize new interactions.

3. Scale and scope
Current target: fewer than 200 students in total.
Intended future: any institution with many classes. The design must therefore not assume one global pool.
Unit of mixing is the cohort (a class, batch or academic-year group). History and team formation are scoped to a cohort. Students in different cohorts are never mixed unless the admin explicitly says so.
At under 200 students per pool, the full pairwise history fits trivially in memory (about 20,000 pairs). The system can therefore use a simple heuristic search rather than anything distributed.
4. Actors
Actor	Can do
Admin	Create an activity. Optionally add instructions (locks, participant cap). Add late students. Re-run or adjust teams if something goes wrong.
Student	Log in. See all activities immediately. Register for the ones they want. View current team and past teams.

The admin does not pick team members by default. The only required team-related input from the admin is the team size. Any adjustments (see 4.2) are optional and exist only when the admin writes them in the instructions box.

4.1 Activity creation form

Required fields:

Activity / task / event name
Team size
Duration
Date and time
Venue 

Optional field:

Instructions (free-text box). Used only when the admin needs an adjustment. Leave it empty and the system applies the default behavior with no special rules.
4.2 What the instructions box can carry

Two kinds of adjustment are supported. If neither is needed, the box stays empty.

a) Locks on specific students. The admin decides who is locked and how. Example: keep two named students on the same team, keep two apart, or fix a student to a team. These are entirely the admin's call; the system does not decide who deserves a lock. Locked students are treated as fixed constraints and the rest of the cohort is shuffled around them as usual.

b) Participant count (cap). The admin may state a number of participants, for example 56. Then only the first 56 students to register count; registration for the activity closes for everyone else once the cap is filled. The cap is first-come, first-served by registration time.

If the admin writes no count, there is no cap and everyone who registers by the deadline participates.

5. Pages
Activities — all available activities. Each shows: activity name, date, duration, team size. Students register here.
Student Teams — the student's current team and full history. Each entry shows: activity name, team number, team members, date, duration.
6. Lifecycle of an activity
Admin posts activity (name, team size, duration, date and time, optional instructions)
   -> Activity may be posted well in advance
   -> As soon as a student logs in, every posted activity is visible to them
   -> Students must register for each activity they want to join (visibility is not participation)
   -> If the admin set a participant cap, registration closes when the cap is filled
   -> Otherwise registration stays open until the deadline
   -> Deadline passes: registration closes
   -> System forms teams automatically from registered students only
   -> Teams are locked and visible on the Student Teams page
   -> Admin handles any late arrivals or dropouts manually

Key rules:

Only students who registered are part of team formation. Logging in alone does not count as participating.
The total number of participants is unknown until the deadline. The admin never enters it.
There is a strict registration deadline. It can be days before the event or as late as about 2 minutes before it, depending on how the admin sets it.
Once teams are formed they are locked.
7. Team formation logic (conceptual)
7.1 First activity in a cohort

No history exists. Assign teams randomly.

7.2 Later activities

Use history. Put people together who have not worked together before.

7.3 When repeats are unavoidable

Zero repeats is only possible for a limited number of activities (it depends on cohort size and team size; for 62 students and team size 6 it is roughly 7 activities). After that, repeats are forced. The preference order for repeats:

Prefer pairs who have worked together fewer times.
Among equal counts, prefer pairs who worked together longest ago. Example: if A worked with X one month ago and with Y one year ago, prefer pairing A with Y.
7.4 Fairness goal

Beyond a low total number of repeats, every student should get at least one teammate they have not worked with (or have not worked with recently). A solution that gives one student a team full of repeat partners is worse than a slightly higher-total solution that spreads the repeats.

7.5 Uneven headcount

When participants do not divide evenly by team size, let r = participants mod team_size:

r = 0: all teams are exactly team size.
r is at least half the team size: the leftover students form one new smaller team.
r is less than half the team size: leftover students are absorbed into existing teams (those teams become team size + 1), choosing the teams with least prior overlap.

Example, team size 6: 62 students gives r = 2, so absorb. 65 students gives r = 5, so new team. Exactly half (r = 3) forms a new team.

7.6 Too many combinations to search

For a cohort of any real size the number of possible team arrangements is astronomically large, so exhaustive search is impossible. The goal is therefore a good arrangement, not a provably optimal one. A smart placement plus local improvement is sufficient.

8. History
Every time two students are placed in the same team, that pairing is recorded with the activity date.
History lasts for the student's enrollment in the cohort.
When students leave, their data is archived, not deleted, because it remains part of other students' history.
All history can be derived from the team membership records. No separate history table is needed.
9. Fallbacks and exception handling
Situation	Behavior
Zero-repeat teams impossible	Use the minimum-repeat result silently. No admin confirmation needed.
Student wants to register after the deadline	Registration is blocked. Admin may add the student to an existing team, or let them participate alone.
Student drops out after teams are formed	The team stays as is. Admin may add a replacement. No automatic re-shuffle.
Participant cap is set and the cap is reached	Registration is closed for the activity. Students after the cap are not registered. Order is by registration time.
A registered student unregisters while a cap is set and before the deadline	Their spot is freed and the next student to register can take it.
Admin instructions are empty	Default behavior only. No locks, no cap.
Admin locks students in a way that cannot be satisfied (for example, a locked group is larger than the team size)	The admin is told before formation; the system does not guess. Admin corrects the instructions.
Fewer registered students than the team size	One team containing everyone.
No one registered	No teams formed. Activity is marked as having no participants.
Remainder would leave a team of one	Absorb that student into an existing team instead of creating a team of one.
Formation job fails or does not run at the deadline	Admin can trigger formation manually. Formation must never produce two sets of teams for one activity.
Bad result the admin dislikes	Admin may re-run formation (only while the activity has not started) or edit teams manually. Each run is logged.
Student is "exhausted" (has worked with everyone registered)	Switch to the repeat-minimizing rules in 7.3 (count, then recency).
10. Assumptions in this draft
A formed team counts as "worked together" even if a member does not show up. Attendance tracking is a later enhancement.
Students belong to exactly one cohort at a time.
Activities are team-based group work. Individual tasks are out of scope.
