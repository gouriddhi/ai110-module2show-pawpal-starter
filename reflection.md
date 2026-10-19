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

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

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

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

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
