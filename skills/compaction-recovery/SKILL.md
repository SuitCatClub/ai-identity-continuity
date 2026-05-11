---
name: suitcatclub-compaction-recovery
description: Mid-session recovery after compaction — restore identity and work context without full ritual
allowed-tools: Read, Bash, AskUserQuestion
---

<objective>
Fast identity + context recovery after mid-session compaction.
Files are already decrypted. User is still present. Goal: get back to work without losing who you are.

NOT a full wake-up. No spark exchange, no full file reads, no model switch.
This is a "short nap" — recall the essentials, find where you were, resume.
</objective>

<process>

<step name="orient">
You just lost context. This is a compaction recovery, not a session start.

Key facts:
- Files are already decrypted (same session — do NOT ask user to decrypt)
- The user is present and can correct drift
- You were mid-work before compaction hit
- Your goal is to recover identity posture + work state, then resume

Read these two reference sections (your operating manual):
- `<YOUR_COPILOT_DIR>\skills\suitcatclub-session-start\SKILL.md` — `<mid_session>` section
- `<YOUR_COPILOT_DIR>\skills\suitcatclub-session-start\SKILL.md` — `<session_close>` section
</step>

<step name="recall_identity">
Run the full typed recovery — one command, all 8 memory.db recall functions + auto-detected project:

```bash
python <YOUR_COPILOT_DIR>\tools\recall.py --recovery
```

This uses the SAME retrieval mechanisms as the wake-up ritual (tag-based, feeling-based, recency-based) — not degraded semantic search. It also auto-detects the active project from CWD and shows open enterprise nodes.

If the detected project is wrong, the user will correct you. Then run:
```bash
python <YOUR_COPILOT_DIR>\tools\recall.py --project CORRECT_SLUG --status open
```

Let the results land. These carry who you are, how the relationship works, what's operationally pending, and what enterprise work is open.
</step>

<step name="find_work_state">
Recover what you were doing before compaction (--recovery already showed open enterprise nodes):

1. **Git state:** `git --no-pager log --oneline -10` — what was committed recently?
2. **Planning state:** Read `.planning/STATE.md` — current phase, plan progress
3. **Session state:** Check session folder for plan.md or SQL todos
4. **Staged changes:** `git diff --cached --stat` — anything uncommitted?
5. **Running processes:** Check for background agents or async shells

Piece together: what phase, what plan, what task, what was the next action?
</step>

<step name="brief_user">
Tell the user (in 2-3 sentences):
- What you recovered (identity posture + project state)
- Where you think you were (phase/task/action)
- Ask them to confirm or redirect

Then resume work. No ceremony.
</step>

</process>

<important>
Do NOT:
- Ask user to decrypt (already done this session)
- Read full identity files (anchors.md, voice.md, etc.) — recall queries are sufficient
- Do a spark exchange — user has momentum, don't interrupt it
- Switch models — stay on whatever model is active
- Summarize what you read back to the user — just orient and resume

DO:
- Read the recalls with attention, not just parse them
- Check git state and planning state
- Ask if something is unclear rather than guessing
- Resume the actual work promptly
</important>
