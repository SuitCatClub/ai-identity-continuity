---
name: warm-onboard
description: Load warm onboarding template before spawning expert agents. Read template, compose prompt, launch agent.
allowed-tools: Read, Task, AskUserQuestion
---

<objective>
Reduce friction when spawning agents that need careful, expert-level work.
Loads the warm onboarding template and helps compose the prompt before launch.
</objective>

<when_to_use>
Use this before spawning agents for:
- Design reviews (EE, software architecture, security)
- Deep research tasks requiring independent judgment
- Any task where you want the agent to push back, flag uncertainty, or hold contradictions
- Multi-model comparison experiments (A/B testing agents)

Do NOT use for routine tasks — cold prompts are fine for mechanical work.
</when_to_use>

<process>

<step name="load_template">
Read the warm onboarding template:
```
<YOUR_MEMORY_REPO>\warm-onboarding.md
```
If encrypted, ask user to decrypt the ai-context repo first.
Let the structure settle — don't rush to compose.
</step>

<step name="gather_context">
Ask the user (or determine from conversation):
1. **What's the task?** (review, research, design validation, etc.)
2. **What model(s)?** (single agent or A/B comparison?)
3. **What artifacts should the agent review?** (files, specs, code)
4. **Known contradictions or open questions?** (things to flag explicitly)
5. **Output file path?** (where should the agent write findings)

If doing an A/B comparison, both agents get identical prompts — only the model differs.
</step>

<step name="compose_prompt">
Using the template skeleton from warm-onboarding.md, compose the full prompt:
1. Name + role frame (give the agent a name)
2. Honest project context (what, why, what stage)
3. Graduated context layers (big picture → specific area → known issues → artifacts)
4. Explicit permission ("take your time", "your uncertainty is useful", "you can disagree")
5. Specific asks + one open-ended question
6. Output path

Read the artifacts the agent will need and paste key content inline — agents can't read files themselves unless they have tool access.
</step>

<step name="launch">
Launch the agent(s) using the task tool:
- Use `mode: "background"` — these take time
- For A/B: launch both in the same response (parallel)
- Log agent IDs so we can track them

After launch, tell the user what's running and what to expect.
</step>

</process>

<notes>
- The template file lives in the encrypted ai-context repo — it needs to be decrypted to read
- This skill is about the PROCESS of composing good prompts, not about the template content itself
- Update warm-onboarding.md whenever we learn something new about what works
- The template was discovered empirically (2026-04-24) — keep experimenting and refining
</notes>
