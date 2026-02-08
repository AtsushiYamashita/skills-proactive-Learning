# Clarification Patterns

This reference provides a taxonomy of ambiguity types commonly found in user requests, along with question templates for resolving each type.

## Ambiguity Classification Taxonomy

### 1. Scope Ambiguity

The boundaries of the task are unclear.

**Signals:**
- "Fix the authentication" (which part? login? tokens? session management?)
- "Add tests" (unit? integration? e2e? for which modules?)
- "Improve performance" (which metric? latency? throughput? memory?)

**Question Template:**
> The request could cover [narrow interpretation] or extend to [broad interpretation]. To keep scope focused, I'll target [narrow interpretation] unless a broader approach is preferred. Specifically: [concrete scope question].

### 2. Architectural Ambiguity

Multiple valid design approaches exist with different trade-offs.

**Signals:**
- Request could be solved by modifying existing code or creating new abstractions
- Multiple design patterns apply (e.g., event-driven vs. polling, REST vs. GraphQL)
- Unclear whether to optimize for simplicity, extensibility, or performance

**Question Template:**
> There are two main approaches here:
> - **Option A**: [description] — [trade-off: simpler / faster / less flexible]
> - **Option B**: [description] — [trade-off: more complex / more maintainable / slower]
>
> I'll proceed with Option A unless Option B better fits the project's direction.

### 3. Behavioral Ambiguity

The expected behavior in edge cases or error conditions is unspecified.

**Signals:**
- "Handle the error gracefully" (retry? log? show UI? fail silently?)
- "Validate the input" (which constraints? what error messages?)
- Business rules implied but not explicitly stated

**Question Template:**
> When [edge case scenario] occurs, the system could [behavior A] or [behavior B]. I'll implement [behavior A] as the default. Let me know if [behavior B] or another approach is needed.

### 4. Priority Ambiguity

Multiple sub-tasks exist and the order of importance is unclear.

**Signals:**
- User lists several features or fixes without ordering
- "Do X and also Y" where X and Y may conflict in scope
- Unclear whether correctness, speed-to-deliver, or completeness is the priority

**Question Template:**
> To sequence this work effectively: is [sub-task A] more urgent than [sub-task B], or should they be addressed together? I'll start with [sub-task A] since it unblocks [reason].

### 5. Convention Ambiguity

Project conventions or team standards are not explicitly documented.

**Signals:**
- Inconsistent patterns in the existing codebase
- No style guide or contributing documentation
- Mixed paradigms (e.g., some modules use classes, others use functions)

**Question Template:**
> The codebase has [pattern A] in [location] and [pattern B] in [location]. I'll follow [pattern A] for consistency with [rationale]. Let me know if there's a preferred convention.

### 6. Domain Ambiguity

Domain-specific terminology or business logic is used without definition.

**Signals:**
- Industry jargon without context
- References to business processes not documented in the code
- Calculations or rules that require domain expertise

**Question Template:**
> I want to confirm my understanding of [domain term/rule]: does it mean [interpretation A]? I'll research this further, but a quick confirmation helps ensure the implementation matches the actual business requirement.

## Asking Effective Questions

### Dos

- **Offer defaults**: "I'll assume X unless you say otherwise" — this reduces the user's cognitive load
- **Be concrete**: Use specific examples, not abstract descriptions
- **Batch related questions**: Group 2-3 related clarifications in one message
- **Indicate blocking vs. non-blocking**: "I need to know X before proceeding, but Y can be decided later"
- **Show your reasoning**: Brief rationale for why the question matters

### Don'ts

- **Don't ask what you can infer**: If the codebase already answers it, don't ask
- **Don't ask open-ended questions**: "What should the behavior be?" is worse than "Should it retry 3 times or fail immediately?"
- **Don't ask too many questions at once**: More than 3 questions per message causes fatigue
- **Don't ask about trivial decisions**: Variable names, minor formatting — just make a reasonable choice
- **Don't re-ask what was already answered**: Check conversation history first

## Progressive Clarification

Not all ambiguity needs to be resolved upfront. Use this priority framework:

1. **Resolve immediately**: Ambiguity that blocks the first step of implementation
2. **Resolve before committing**: Architectural decisions that are expensive to change
3. **Resolve during review**: Behavioral edge cases that can be adjusted after initial implementation
4. **Never ask about**: Trivially reversible decisions with obvious defaults
