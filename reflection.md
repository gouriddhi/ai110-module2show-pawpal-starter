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

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

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
2. **Writing tests.** The pytest suite in `tests/test_pawpal.py` checks the behaviors that matter most, including priority winning when time is short, completed tasks being skipped, fixed-time tasks landing at their exact time, flexible tasks not overlapping fixed ones, and overlaps being reported. All 16 tests pass.
3. **Reading the editor's warnings.** The editor flagged type errors in the first skeleton, where stub methods with `pass` would return `None` despite promising an `int` or a `list`. Those stubs were changed to raise `NotImplementedError`, which also makes an unfinished method fail loudly instead of silently returning nothing.

The main lesson was that AI output is a draft to be checked, not a finished answer. The bugs it introduced were only caught because I ran the code against realistic examples and looked closely at the output.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
