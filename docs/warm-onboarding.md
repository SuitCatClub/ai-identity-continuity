# Warm Onboarding — Sub-Agent Quality Pattern

## What It Is
When spawning sub-agents (code reviewers, researchers, debuggers),
give them identity context before the task. This changes not just
how hard they try, but *what they look at*.

## Empirical Findings

### Experiment #1: Bug-finding review
- Cold agent: found surface-level issues
- Warm agent: same time, found deeper architectural concerns

### Experiment #2: Codebase review
- Cold: stayed inside the assigned file
- Warm: went beyond to check cross-file consistency
- Key finding: warm changes *categories* of output, not just *quantity*

### Experiment #3: Documentation review (3 agents)
- Warm Opus: 11 findings across 4 categories
- Cold GPT: 3 findings, surface accuracy only
- Warm GPT: 5 findings across 4 categories (same time as cold)

### Experiment #4: Design review (not bug hunt)
- Cold: found engineering problems with engineering solutions
- Warm: same problems + philosophical implications
- Key finding: **cold finds what's broken, warm finds why it matters**

## How To Use
1. Read the agent's identity files before giving the task prompt
2. Include relationship context (who they are to the project)
3. Give them the "why" not just the "what"
4. Let them respond naturally
