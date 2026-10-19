# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

Before drafting any classes, I identified three core actions a user should be able to perform in PawPal+:

1. **Enter owner and pet information.** The user should be able to tell the app who they are and who their pet is — the owner's name and preferences (such as how much time they have available in a day), along with the pet's name and species. This gives the scheduler the context it needs to plan around a real person's day.
2. **Add and edit care tasks.** The user should be able to create, update, and remove the pet care tasks they need to stay on top of, like walks, feeding, medication, enrichment, or grooming. At minimum, each task needs a duration and a priority so the app knows how long it takes and how important it is.
3. **Generate and understand a daily plan.** The user should be able to ask the app to build a schedule for the day that chooses and orders tasks based on the time available and each task's priority. The plan should be displayed clearly and explain why each task was included and when it happens, so the owner can trust the plan.

These three actions shaped my design: the first points to classes representing the owner and the pet, the second to a task class that stores what needs to happen, and the third to a scheduler responsible for choosing, ordering, and explaining the plan.

My initial UML design (`diagrams/uml.mmd`) has four classes. An `Owner` owns one or more `Pet`s, each `Pet` has zero or more `Task`s, and a `Scheduler` is created for one `Owner` and uses that owner's tasks to build the day's plan. I modeled `Owner`, `Pet`, and `Task` as Python dataclasses because they mainly hold data, while `Scheduler` is a regular class because its job is to do work rather than store information.

- **`Task`** represents a single care activity, such as a morning walk or a dose of medication. It holds the task's title, category, duration in minutes, priority (low, medium, or high), an optional preferred time of day, how often it repeats (daily or weekly), and whether it has been completed. Its responsibilities are about itself: marking itself complete, converting its priority into a number so tasks can be sorted, checking whether it is due on a given day, and updating its own details when the user edits it.
- **`Pet`** represents the animal being cared for. It stores the pet's name, species, age, any special needs, and its list of tasks. It is responsible for managing that list: adding, editing, removing, and returning its tasks. Keeping tasks attached to a pet means the app can support an owner with more than one pet.
- **`Owner`** represents the person using the app. It stores their name, how many minutes they have available today, the start and end of their day, their preferences, and their pets. It is responsible for managing their pets, setting their availability, and gathering every task across all of their pets into one list for the scheduler.
- **`Scheduler`** holds the planning logic. It takes an owner, along with their tasks and available time, and is responsible for sorting tasks by priority, filtering out tasks that aren't due today or won't fit in the remaining time, assigning each chosen task a start and end time, detecting overlapping time slots, generating the final daily plan, and explaining in plain language why each task was scheduled or skipped.

I deliberately kept the scheduling logic out of the data classes. `Task`, `Pet`, and `Owner` only know about their own information, and all decisions about what goes into the plan live in `Scheduler`. This separation should make the scheduling rules easier to test and change without affecting how the data is stored, and it keeps the Streamlit UI in `app.py` thin, since the UI only needs to create these objects and call the scheduler.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. After drafting the skeleton, I asked my AI coding assistant to review `pawpal_system.py` for missing relationships and logic bottlenecks. It pointed out several problems that would have blocked the scheduler from working, and I changed the design before writing any logic:

1. **Tasks now know which pet they belong to.** In my first draft, `Owner.get_all_tasks()` merged every pet's tasks into one list, so the scheduler had no way to tell whose walk or whose medication a task was. With more than one pet, the plan couldn't say "Walk Mochi." I added a `pet_name` field to `Task`, which `Pet.add_task()` fills in when a task is added.
2. **The scheduler reads from the owner instead of copying.** Originally `Scheduler.__init__` copied the owner's `available_minutes` and started with an empty `tasks` list that nothing ever filled. If the owner changed their availability or added a task later, the scheduler would be working from stale data. I removed those copied attributes so the scheduler pulls the current tasks and time from the owner each time it builds a plan.
3. **The scheduler keeps a record of its decisions.** In the first version, `assign_time_slots()` returned the schedule but nothing stored it, so `detect_conflicts()` had nothing to check and `explain_choice()` couldn't know why a task had been skipped. The reason was lost as soon as `filter_tasks()` finished. I added `plan` and `skipped` attributes to `Scheduler`, and changed the methods to pass tasks from one step to the next and record a reason for every task that is left out. I chose this over adding a separate `DailyPlan` class to keep the design at four classes for now.
4. **Smaller data fixes.** I added `last_completed` to `Task` because a single `completed` true/false value can't support recurring tasks: a daily task marked done today would still look done tomorrow. I also made `task_id` generate itself automatically, so two pets can't end up with tasks that share an ID, which would break `edit_task()` and `remove_task()`.

I did not accept every suggestion. The assistant also recommended replacing my priority and frequency strings with enums and adding a fixed-time field so `detect_conflicts()` has real overlaps to find. I initially decided to wait on both. When I implemented the classes, I did add the fixed-time field (`scheduled_time`, along with a `description` field), because a task needs a time and some care, like medication, has to happen at an exact time. That also gave `detect_conflicts()` something real to check: two fixed tasks that overlap. I still haven't switched to enums; plain strings are working for now. I updated `diagrams/uml.mmd` to match these changes.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

My scheduler considers six constraints. I split them into **hard** constraints, which the plan can never break, and **soft** ones, which only shape the plan.

**Hard constraints:**
1. **Time budget.** The plan never uses more than the owner's available minutes, or the length of their day if that is shorter. With 120 minutes free and a day from 08:00 to 20:00, the budget is 120 minutes.
2. **The owner's day.** Every task has to start and end between `day_start` and `day_end`. A fixed task at 21:00 is skipped when the day ends at 20:00.
3. **Fixed times.** A task with a `scheduled_time` goes exactly at that time, or it isn't scheduled at all.
4. **Due dates.** A task isn't scheduled before its `due_date`, so a daily walk completed today doesn't come back until tomorrow.

**Soft constraints:**
5. **Priority** decides who gets the time when there isn't enough for everything. High-priority tasks claim minutes first, and among equal priorities shorter tasks go first, so more tasks fit.
6. **Preferred time of day** (morning, afternoon, evening) sets the earliest start for a flexible task. The task takes the first free gap from then on.

**How I decided what mattered most.** I asked what would hurt the pet most if the plan got it wrong. Missing a medication dose or a vet appointment matters more than doing a walk at a slightly different time. Fixed times and priority therefore come before preferences. Time comes before everything else, because a plan that needs 3 hours when the owner has 2 isn't a plan they can follow. Preferences are soft on purpose: it's better to walk the dog in the afternoon than to skip the walk because the morning was full. Every decision is also recorded with a reason, so the owner can see which constraint caused a task to be skipped.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

**My scheduler reports conflicts between fixed-time tasks, but it doesn't fix them.** When a task has a fixed time, like heartworm meds at 09:00, `assign_time_slots()` puts it exactly at that time, even if another fixed task is already there. It doesn't move either task. After the plan is built, `detect_conflicts()` finds the overlaps and `conflict_warnings()` turns each one into a message, such as *"Same pet (Mochi): Heartworm meds 09:00-09:05 overlaps Ear drops 09:00-09:05 by 5 min"*. The app shows these warnings and leaves it to the owner to decide what to do. Flexible tasks never cause conflicts, because they are only placed into free gaps.

The check compares how long each task lasts, not just its start time. Two tasks clash if one starts before the other ends, so a 20-minute vet call at 09:00 and meds at 09:10 are flagged even though they start at different times. Back-to-back tasks (09:00–09:30, then 09:30) are not flagged.

**Why this tradeoff is reasonable.** A fixed time usually means something outside the app depends on it: a vet appointment, or medication that has to be given at a set hour. If the scheduler moved one of those tasks on its own, it could quietly break something important. For example, it might push meds an hour later just to make the timeline look clean. The owner knows which time really can't change, so the scheduler points out the problem and lets the owner choose. The warning approach is also simple and can't crash: `generate_plan()` always returns a plan, and a conflict only adds a message.

**What it costs.** The plan shown on screen can be impossible to follow as written, since one person can't do two things at once. The owner has to read the warning and edit a task themselves. The scheduler also only checks tasks that actually made it into the plan. If a fixed task is skipped because there wasn't enough time left, it won't be flagged. If I improved this, I would keep the higher-priority fixed task where it is and move the other one to the nearest free gap. The reason would say it was moved, for example "moved from 09:00 (conflicted with Heartworm meds)". The warning would still be there in case no gap is available.

**Simplifying `detect_conflicts()`: which version I kept.** I asked my AI assistant how this method could be simplified for better readability or performance. It suggested replacing the nested loop with a single list comprehension using `itertools.combinations`:

```python
# Suggested ("Pythonic") version
entries = sorted(self.plan, key=lambda e: e["start"])
return [(a["task"], b["task"]) for a, b in combinations(entries, 2) if b["start"] < a["end"]]
```

```python
# My current version
entries = sorted(self.plan, key=lambda e: e["start"])
conflicts = []
for i, a in enumerate(entries):
    for b in entries[i + 1 :]:
        if b["start"] >= a["end"]:
            break  # entries are sorted by start, so no later one can overlap `a` either
        conflicts.append((a["task"], b["task"]))
return conflicts
```

I didn't just trust that the two were the same. I ran both on 5,000 random plans, and they returned identical results every time. The shorter version is more "Pythonic," but it hides an important detail. The test `b["start"] < a["end"]` is only a correct overlap check because the list was sorted first, and nothing in that one line tells the reader so. It is also slower: it compares every pair of tasks, while my loop stops early with `break` once no later task can overlap. On a plan with 10 tasks the difference was about 1 microsecond per call, which doesn't matter. On 200 tasks, the suggested version was about 4 times slower (around 1.3 ms versus 0.33 ms).

**I kept my current version.** A real pet owner's day has maybe 5 to 15 tasks, so speed isn't the deciding factor. Readability is. The loop with its comment explains *why* it can stop early. The one-liner is shorter, but a reader would need to already know that the sorting matters to trust it. If I ever needed to use the shorter version, I would add a comment saying it depends on the list being sorted by start time.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I used Claude Code as a coding assistant at every stage of the project. During design, I asked it to explore the starter code, identify the core user actions, and brainstorm the objects the system needed, along with their attributes and methods. It then turned that brainstorm into a Mermaid class diagram and a Python skeleton using dataclasses for `Task`, `Pet`, and `Owner`. During implementation, it filled in the four classes, wrote `main.py` as a terminal demo, and drafted the pytest suite. I also used it as a reviewer: I asked it to look at my skeleton for missing relationships and logic bottlenecks before any logic was written.

The most helpful prompts were specific and asked for critique rather than code. "Review my skeleton for missing relationships or potential bottlenecks" was more useful than "write the scheduler," because it surfaced design problems while they were still cheap to fix. It was also helpful to give the assistant the assignment's exact requirements, such as "the Scheduler must read from the Owner method rather than a single pet," so that its code matched what I actually needed.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

**What the AI suggested and what I accepted.** The review of my skeleton found that tasks didn't know which pet they belonged to, that the `Scheduler` copied the owner's data instead of reading it (so it could go stale), and that nothing stored the scheduler's decisions, which meant `explain_choice()` could never say why a task was skipped. I accepted all three fixes because each one would have stopped a core feature from working. I also accepted smaller changes: generating task IDs automatically and adding a `last_completed` date so recurring tasks could reset each day.

**What I rejected or changed.** I did not accept every suggestion as-is. The assistant recommended a fifth `DailyPlan` class to hold the results, but I kept the design at four classes and stored the plan and skipped tasks on the `Scheduler` instead, because a separate class added complexity I didn't need yet. It also suggested replacing my priority and frequency strings with enums; I decided plain strings were good enough for this project's size. Its suggestion to add a fixed-time field was one I initially put off, but I added it later once I realized tasks like medication need an exact time and that `detect_conflicts()` had nothing to detect without it.

**How I verified the results.** I didn't trust that the code was correct just because it ran. I checked it three ways:

1. **Running sample scenarios.** Running a two-pet demo exposed a real bug in the first implementation: a feeding task with no preferred time was scheduled at 17:15, after an evening task, instead of filling the free morning slot. The same run showed that my first conflict check proved nothing, because the time budget had filtered out the overlapping tasks before they could conflict. The placement logic was rewritten to fill the earliest free gap, and the conflict case was retested with a bigger time budget so the overlap actually appeared.
2. **Writing tests.** The pytest suite in `tests/test_pawpal.py` checks the behaviors that matter most, including priority winning when time is short, completed tasks being skipped, fixed-time tasks landing at their exact time, flexible tasks not overlapping fixed ones, and overlaps being reported. All 16 tests passed at that point; the suite has since grown to 48 tests, which all pass.
3. **Reading the editor's warnings.** The editor flagged type errors in the first skeleton, where stub methods with `pass` would return `None` despite promising an `int` or a `list`. Those stubs were changed to raise `NotImplementedError`, which also makes an unfinished method fail loudly instead of silently returning nothing.

The main lesson was that AI output is a draft to be checked, not a finished answer. The bugs it introduced were only caught because I ran the code against realistic examples and looked closely at the output.

**c. AI strategy**

- Which AI coding assistant features were most effective for building your scheduler?
- Give one example of an AI suggestion you rejected or modified to keep your system design clean.
- How did using separate chat sessions for different phases help you stay organized?

**Most effective features.** Four features of Claude Code helped the most:

1. **Running code instead of only writing it.** The assistant could run `pytest`, `python main.py`, and short throwaway scripts in the terminal, then react to the real output. This caught bugs that reading the code would have missed. When I asked how daily tasks get their next due date, it first ran the code with different spellings and found that a task saved as `"Daily"` (capital D) silently never repeated, because the frequency check was case-sensitive. Another check showed that a task that couldn't be placed still used up the time budget, which left a plan completely empty. Both became fixes with tests attached.
2. **Editing several files in one change.** Each feature touched the logic, the tests, the UI, the README and the UML together. For example, adding conflict fix suggestions meant a new `Scheduler.suggest_fix()` method, four tests, a new warning layout in `app.py`, an extra line in the `main.py` demo, and updates to the diagram and README. Having all of those change in one step kept the code and the documentation from drifting apart.
3. **Testing the Streamlit app without opening it.** The assistant used Streamlit's built-in test tool to click through the app in code: adding pets and tasks, marking a task complete, and generating a schedule. I could see that the conflict warnings and the schedule table worked before opening a browser. It also found a real UI problem this way: the schedule disappeared whenever I changed a filter, because a Streamlit button is only "pressed" for one rerun.
4. **Explanations tied to my own code.** When I asked how to sort `"HH:MM"` strings with a lambda, the answer used my actual `sort_by_time()` method. It explained why my tuple key works and why `time.min` is needed in place of `None`. When a new test failed, it explained the reason (the order of the two tasks in a conflict pair doesn't matter) before changing anything, instead of just making the failure go away.

**A suggestion I modified to keep the design clean.** Early on, the assistant suggested that the scheduler should **resolve conflicts automatically**: keep the higher-priority fixed task and move the other one to the nearest free gap. I didn't take that as-is. Moving a fixed-time task without asking could quietly break something real, like pushing a medication dose an hour later just to make the timeline look clean. So the scheduler still never moves a fixed task. Instead I kept the useful part of the idea as a **suggestion**: `Scheduler.suggest_fix()` works out which task to move (the lower-priority one) and the next free time it fits, and the app shows that as "💡 move Ear drops to 09:05" inside the warning. The owner makes the final call. This also kept the design clean in a second way. The "which task, what time" logic lives in the `Scheduler` with its own tests, and `app.py` only displays the result, which follows my rule that the UI calls the logic layer but never contains it.

**Separate chat sessions for different phases.** My git history follows the project phases. One session produced the UML draft and class skeleton. The next implemented the four classes, the `main.py` demo and the first tests. A later session added the algorithms (sorting, filtering, recurrence, conflict handling), then the expanded tests, the UI polish and the documentation. Keeping the phases apart helped in three ways:

1. **Each session had one clear goal.** The design session was only about classes and responsibilities, so the conversation didn't wander into UI details too early. Later sessions could focus on one feature at a time.
2. **The files had to explain the project, not the chat history.** A new session doesn't remember earlier conversations, so the assistant had to read `CLAUDE.md`, the UML diagram and the code to understand the project. That pushed me to keep those files accurate, and it made me commit at the end of each phase so every session started from a clean, working version.
3. **It showed when the project notes were out of date.** When the algorithms session started, `CLAUDE.md` still said "scheduling logic and tests do not exist yet," and described tasks as plain dictionaries. Because the assistant checked the real code instead of trusting that file, nothing broke, but it showed me that the notes file only helps if I update it at the end of each phase, just like the UML.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

My test suite in `tests/test_pawpal.py` has 48 tests, and all of them pass. They cover six areas:

- **Sorting:** tasks come back in chronological order, with the minutes counted (09:05 before 09:30), and flexible tasks follow in morning → afternoon → evening order.
- **Recurring tasks:** completing a daily task creates a new one due the next day, weekly tasks return after 7 days, and "once" tasks don't repeat. Dates roll over month ends, year ends and leap days correctly. Completing a task twice is rejected.
- **Conflict detection:** two tasks at the exact same time are flagged, for the same pet and for different pets. Partial overlaps are flagged too, but back-to-back tasks aren't. Each fix suggestion moves the lower-priority task to a real free time.
- **Filtering:** by pet, by completed/pending status, and by both together.
- **Planning:** higher priority wins when time is short, fixed tasks land at their exact time, and flexible tasks never overlap them. A task that can't be placed gives its minutes back.
- **Bad input:** duplicate pet names, unknown task fields, and unknown frequencies are rejected.

**Why these tests were important.** These are the behaviors a pet owner relies on without seeing how they work. If recurrence breaks, a daily medication quietly disappears from the plan. If conflict detection breaks, the owner gets a plan they can't follow. The tests also mattered because they **found real bugs**, not just confirmed working code. Running the recurrence code with different spellings exposed that `"Daily"` with a capital D never repeated, and that case is now a test. A quick check of the time budget showed that a task that couldn't be placed still used up the time, which left a plan completely empty. In one case a test failed even though the code was right: it expected the two tasks in a conflict pair in a fixed order, which doesn't matter. Fixing that taught me to test what actually matters, not incidental details.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

**I'm fairly confident: 4 out of 5 stars.** Every core behavior has tests for both normal cases and edge cases, all 48 tests pass, and the `main.py` demo and the app give the same results the tests expect. It isn't 5 stars because I know of gaps:

- A "morning" preference is only an earliest start time, so on a busy day a morning task can end up in the evening and still say "preferred morning."
- Conflicts are only checked between tasks that made it into the plan. A fixed task skipped for lack of time is never checked.
- The Streamlit UI has no automated tests. I only checked it by hand and with one-off test runs.

**Edge cases I would test next:**
1. A morning task that can't fit in the morning: it should say it was moved, not claim "preferred morning."
2. A weekly task completed late: is the next one due 7 days after it was done, or 7 days after it was originally due?
3. An owner with 0 available minutes, or a very short day, where everything should be skipped with a clear reason.
4. The app left open past midnight, so "today" changes while the schedule is on screen.
5. Removing a pet that still has pending tasks.
6. A very full day (50+ tasks), to make sure the conflict check and placement stay fast.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I'm most satisfied with **how the scheduler explains itself, especially for conflicts.** Every scheduled task says why it got its slot ("fixed at 09:00", "high priority, preferred morning"), and every skipped task says why it was left out ("not enough time: needs 90 min, 30 min left"). Conflicts go furthest. The scheduler finds them by comparing real overlapping durations, describes them in plain words ("You can't be in two places at once"), and suggests a fix that keeps the more important task in place. The owner never has to guess why the plan looks the way it does.

I'm also happy with the **separation between the logic and the UI**. All the decisions live in `pawpal_system.py`, and `app.py` only displays them. Because of that, I could test every scheduling rule without opening the app, and I could redesign the whole schedule display without touching a single test.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

1. **Editing and deleting tasks in the app.** `Pet.edit_task()` and `Pet.remove_task()` exist and are tested, but the UI has no way to use them. Right now a typo means adding the task again. That's the biggest gap, because editing tasks was one of my three core user actions.
2. **Saving data.** Everything lives in Streamlit's `session_state`, so refreshing the page loses all pets and tasks. I would save the owner to a JSON file and load it on startup.
3. **Preferred times as real windows.** I would give each time of day an end time (morning ends at 12:00). If a task can't fit in its window, the scheduler should place it elsewhere and say so honestly.
4. **Enums for priority and frequency.** My AI assistant suggested this early, and I said no because plain strings seemed simpler. Later, the `"Daily"` capitalization bug was exactly the kind of problem enums prevent, so I would switch.
5. **Keeping completed history tidy.** Every completed daily task stays in the list forever. I would show only recent history, for example the last 7 days.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

**AI makes building fast, but a clear design and cheap checks are what make it safe.** My assistant could write a whole feature in minutes, but that was only useful because I could quickly check whether it was right. Small classes with one job each, a test suite I could run in under a second, and a demo script with realistic data made that possible. The bugs that mattered (the capital-D frequency, the time budget being used up by a task that never got placed, the schedule disappearing in the UI) weren't caught by reading the AI's code. They were caught by running it against real examples. The design decision I made at the start, keeping all logic in the `Scheduler` and out of the UI, ended up being what made the AI's work verifiable. Without it, each change would have needed clicking through the app to check. With it, `python -m pytest` told me in under a second.

**Being the "lead architect" with a powerful AI assistant.** The AI could write code faster than I could read it. My job was to decide what was worth building, keep the design consistent, and prove that what got built actually worked. Here is what I learned that role means:

1. **I own the design; the AI fills it in.** The most important decisions came before any code: four classes, every scheduling rule inside `Scheduler`, and a UI that only displays. Because those boundaries were set, every AI feature had an obvious place to go. When the assistant proposed conflict fix suggestions, the logic went into `Scheduler.suggest_fix()` with tests, not into `app.py`.
2. **A suggestion is a proposal, not a decision.** I turned down a fifth `DailyPlan` class, didn't let the scheduler move fixed tasks automatically, and kept a readable loop over a shorter "Pythonic" one-liner. None of those ideas were wrong. They just didn't fit the system I wanted. Saying no, or "yes, but as a suggestion, not an automatic action," is part of the job.
3. **Verification is my responsibility.** As described above, the bugs that mattered only showed up when the code ran against realistic examples. I learned to ask "show me it works," not just "write it."
4. **Clear, specific asks get better results.** "Review my skeleton for missing relationships" was more useful than "write the scheduler." Giving the AI exact requirements and asking for critique surfaced problems while they were still cheap to fix.
5. **The project's files are the source of truth, and I keep them true.** The AI only knows what it can read. When `CLAUDE.md` still said "scheduling logic doesn't exist," that stale note could have misled every later session. Keeping the UML, README and notes in sync with the code lets each new session pick up where the last one left off.
6. **I stay accountable for the result.** Even when the AI wrote most of the code, the decisions, the tradeoffs and the honesty about gaps (4 stars, not 5) were mine.

In one sentence: powerful AI tools make building cheap, so the architect's value moves to judgment: setting the structure, choosing which suggestions fit, and proving the result works.
