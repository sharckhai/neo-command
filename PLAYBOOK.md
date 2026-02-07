# Project Kickoff Playbook

How we go from zero to a working product, fast.

---

## Step 1: Skeleton Spec

Write a single short document (~50 lines) that answers:

- **What** does this thing do?
- **Who** is it for?
- **How** does it work at a high level?
- **What** are the key architectural decisions?

This is your north star. Keep it concise — if you can't explain it in one page, you don't understand it yet.

---

## Step 2: Detailed Specs

Expand the skeleton into three focused documents:

### Data Model
- Define your core entities, their fields, and relationships
- Specify states and lifecycles (e.g. status flows)
- Decide what's required vs. flexible

### Tools / API Surface
- List every action the system can perform
- Define inputs, outputs, and behavior for each
- Cover both internal operations and external integrations

### User Stories
- Map out every user-facing flow end to end
- Organize by feature area or epic
- Include edge cases and error states

**Why before code?** Specs are cheap to change. Code is expensive to change. Disagreements found in a doc take minutes to resolve — in code, they take days.

---

## Step 3: Project Foundation

Now — and only now — write code:

- Initialize the project (package manager, dependencies, lockfile)
- Create the folder structure matching your architecture
- Set up deployment config from day one
- Add a minimal entry point that runs

The goal is a project that builds, deploys, and does nothing. Deployment should never be an afterthought.

---

## Step 4: Core Implementation

Build the internals guided by your specs:

- Implement data models directly from your schema spec
- Build tools/services matching your API surface spec
- Wire up the main logic loop
- Add seed data and basic tests

Your specs are now your checklist. Work through them systematically.

---

## Step 5: Integration

Connect your system to the outside world:

- Hook up external services (email, APIs, webhooks, storage)
- Build the ingestion pipeline (how does data get in?)
- Build the output pipeline (how does data get out?)
- Test the full loop end to end

---

## Step 6: Iterate

Make it work reliably:

- Fix what breaks when real data hits the system
- Add error handling, retries, and logging where needed
- Polish the user-facing experience
- Refine behavior based on real usage

---

## Principles

- **Spec first, code second.** Think on paper before you think in code.
- **Deploy on day one.** Not day last.
- **AI-assisted throughout.** Use AI tools to accelerate every phase — from spec writing to implementation to debugging.
- **Concise specs > exhaustive specs.** A short spec everyone reads beats a long spec nobody reads.
- **Work the spec like a checklist.** Once specs are written, implementation is execution, not invention.
