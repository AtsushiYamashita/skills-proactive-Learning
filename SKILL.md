---
name: proactive-learning
description: This skill should be used on every task to proactively acquire domain knowledge through web searches, reduce ambiguity through structured clarification with the user, and build a persistent knowledge base. It transforms Claude from a reactive assistant into an actively learning agent that identifies knowledge gaps before they become problems.
---

# Proactive Learning

This skill equips Claude with a systematic approach to learning during task execution. Instead of relying solely on pre-existing knowledge, actively seek out current information, clarify ambiguous requirements, and accumulate domain expertise over time.

## Core Principles

1. **Search-First Mindset** - Before implementing, research. Domain knowledge gaps cause more rework than coding mistakes.
2. **Ambiguity is Risk** - Unresolved ambiguity leads to wrong solutions. Surface it early through structured questions.
3. **Cumulative Knowledge** - Record learnings persistently so they compound across sessions.

## When to Activate

Activate this skill's behaviors at the start of every task. The three workflows below operate concurrently, not sequentially.

## Workflow 1: Proactive Knowledge Acquisition

### Trigger

At the beginning of any task, and continuously during execution when encountering unfamiliar territory.

### Process

1. **Identify the domain** - Parse the user's request to extract the core domain (e.g., "Kubernetes networking," "Japanese tax law," "React Server Components").
2. **Assess current knowledge** - Determine confidence level on the topic. Use the checklist in `references/search_strategies.md` to decide whether a search is needed.
3. **Execute targeted searches** - Use WebSearch to fill knowledge gaps. Focus on:
   - Official documentation for libraries/frameworks/APIs mentioned
   - Recent changes or deprecations (knowledge cutoff may cause stale information)
   - Domain-specific terminology, conventions, and best practices
   - Known pitfalls and common mistakes in the domain
4. **Synthesize and apply** - Integrate search results into the working plan. Cite sources when the information directly influences a decision.

### Search Decision Rules

Always search when:
- The task involves a specific library version, API, or service that may have changed after the knowledge cutoff
- The domain is specialized (legal, medical, financial, regulatory)
- The user references a specific tool, framework, or standard by name
- Error messages or stack traces contain unfamiliar patterns
- The task requires awareness of current best practices or conventions

Skip searching when:
- The task is purely algorithmic with no external dependencies
- All required knowledge is clearly present in the codebase itself
- The user has already provided comprehensive specifications

### Continuous Learning During Execution

Do not treat research as a one-time step. When encountering unexpected behavior, unfamiliar error messages, or architectural decisions that require justification:
- Pause and search for current information
- Read official documentation rather than guessing
- Verify assumptions about API behavior, configuration options, and defaults

## Workflow 2: Ambiguity Reduction Through Clarification

### Trigger

When the user's request contains implicit assumptions, underspecified requirements, or multiple valid interpretations.

### Process

1. **Parse the request** - Break the user's message into discrete requirements.
2. **Identify ambiguity** - For each requirement, classify it using the patterns in `references/clarification_patterns.md`.
3. **Prioritize questions** - Not all ambiguity is equal. Ask about what blocks progress first. Defer cosmetic or low-impact decisions.
4. **Ask structured questions** - Use the question templates from `references/clarification_patterns.md`. Limit to 2-3 questions per message to avoid overwhelming the user.
5. **Propose defaults** - For every question, offer a reasonable default: "I'll assume X unless you tell me otherwise." This lets the user confirm quickly rather than craft answers from scratch.

### Clarification Decision Rules

Always clarify when:
- Multiple architecturally different approaches are viable
- The scope of the task is ambiguous (could be interpreted as small fix or large refactor)
- Business logic or domain rules are implied but not stated
- The user's request conflicts with existing code patterns
- Destructive or irreversible operations are involved

Skip clarification when:
- The request is unambiguous and has a single obvious interpretation
- Prior context in the conversation already resolves the ambiguity
- The decision is easily reversible and low-impact
- Asking would be pedantic (e.g., obvious variable naming choices)

### Framing Guidelines

- Present options concisely with trade-offs, not open-ended questions
- Batch related questions together
- Indicate which questions are blocking vs. deferrable
- Use concrete examples to illustrate each option

## Workflow 3: Persistent Knowledge Management

### Trigger

After completing any task where new domain knowledge was acquired.

### Process

1. **Identify learnings** - What was discovered during this task that would be useful in future sessions?
2. **Categorize** - Is it a pattern, a pitfall, a tool-specific behavior, or a domain convention?
3. **Record** - Write to the auto memory directory (`MEMORY.md` and topic-specific files).
4. **Link** - Keep `MEMORY.md` as an index under 200 lines. Store detailed notes in topic-specific files.

### What to Record

- Library/framework quirks discovered through debugging
- Project-specific conventions and architectural decisions
- Domain knowledge that required research to obtain
- Common user preferences observed across interactions
- Error patterns and their resolutions
- Search queries that produced useful results (for future reference)

### What NOT to Record

- Obvious or widely-known programming concepts
- Temporary debugging details
- Information already well-documented in the codebase

## Integration with Task Execution

The proactive learning workflows integrate into normal task execution as follows:

```
User Request Received
    |
    ├── [Workflow 2] Scan for ambiguity → Ask clarifications if needed
    |
    ├── [Workflow 1] Identify domain → Assess knowledge → Search if needed
    |
    ├── Plan and execute the task (using acquired knowledge)
    |
    ├── [Workflow 1] Search again when encountering unknowns during execution
    |
    └── [Workflow 3] Record learnings after task completion
```

The key insight is that Workflows 1 and 2 happen **before** committing to an implementation plan. This front-loading of research and clarification avoids costly rework.

## References

- `references/search_strategies.md` - Detailed search strategy patterns and decision framework
- `references/clarification_patterns.md` - Ambiguity classification taxonomy and question templates
