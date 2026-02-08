# Search Strategies

This reference provides a decision framework for when and how to perform web searches during task execution.

## Knowledge Gap Assessment Checklist

Before starting any task, evaluate each item. If any answer is "yes," conduct a targeted search.

| Question | If Yes → Search For |
|----------|---------------------|
| Does the task mention a specific library or framework? | Official docs, latest version, changelog |
| Could the API/behavior have changed after the knowledge cutoff? | Current documentation, migration guides |
| Does the task involve a domain I have low confidence in? | Domain overview, terminology, conventions |
| Are there error messages or stack traces I don't recognize? | Error message exact text, known issues |
| Does the task require awareness of legal/regulatory rules? | Current regulations, compliance requirements |
| Is the user referencing a tool or service by name? | Official documentation, quickstart guides |
| Am I about to recommend a pattern I'm not sure is current best practice? | Current best practices, community consensus |
| Does the task involve infrastructure or deployment? | Provider-specific docs, current pricing/limits |

## Search Strategies by Context

### Strategy 1: Documentation Lookup

**When**: A specific library, framework, API, or service is mentioned.

**How**:
1. Search for `[library name] documentation [specific feature]`
2. Prefer official documentation over blog posts
3. Check version compatibility if a specific version is mentioned
4. Look for migration guides if upgrading

**Example queries**:
- `Next.js 15 app router middleware documentation`
- `PostgreSQL 16 JSON functions`
- `AWS Lambda Node.js 22 runtime changes`

### Strategy 2: Error Resolution

**When**: Encountering unfamiliar errors or unexpected behavior.

**How**:
1. Search the exact error message in quotes
2. Add the framework/language name as context
3. Check GitHub issues for the relevant repository
4. Look for recent (last 6 months) solutions — older solutions may be outdated

**Example queries**:
- `"Cannot find module 'next/headers'" Next.js 15`
- `"ECONNREFUSED" docker compose networking`
- `TypeScript "Type instantiation is excessively deep" fix`

### Strategy 3: Best Practice Verification

**When**: About to make an architectural or design decision.

**How**:
1. Search for `[technology] best practices [specific concern] [current year]`
2. Look for official recommendations first, then community consensus
3. Cross-reference multiple sources for contested topics
4. Pay attention to context — best practices vary by scale and use case

**Example queries**:
- `React state management best practices 2026`
- `Kubernetes pod security standards current`
- `Python async database access patterns`

### Strategy 4: Domain Knowledge Acquisition

**When**: The task involves a specialized domain (finance, healthcare, legal, etc.).

**How**:
1. Start with terminology — search for glossary or overview articles
2. Identify the regulatory or compliance frameworks that apply
3. Look for domain-specific conventions and standards
4. Find authoritative sources (government sites, professional bodies)

**Example queries**:
- `HIPAA technical safeguards requirements summary`
- `Japanese consumption tax invoice system 2026 requirements`
- `GAAP revenue recognition rules SaaS`

### Strategy 5: Competitive/Landscape Research

**When**: The user asks to evaluate options, compare tools, or make a technology choice.

**How**:
1. Search for recent comparison articles and benchmarks
2. Check each option's GitHub activity and maintenance status
3. Look for migration stories and real-world experience reports
4. Identify deal-breaker limitations for the user's specific context

**Example queries**:
- `Prisma vs Drizzle ORM comparison 2026`
- `Bun vs Node.js production readiness`
- `Tailwind CSS v4 breaking changes from v3`

## Search Quality Guidelines

### Evaluating Search Results

- **Prefer official sources**: Documentation > Blog posts > Stack Overflow > Forum posts
- **Check recency**: Prefer results from the last 12 months for fast-moving technologies
- **Verify relevance**: Ensure the version, platform, and context match the user's situation
- **Cross-reference**: For important decisions, verify with at least 2 independent sources

### When Search Results Conflict

1. Weight official documentation highest
2. Check the date — newer information usually wins
3. Consider the context — advice for large-scale systems may not apply to small projects
4. When truly ambiguous, present both perspectives to the user with trade-offs

### When Search Yields No Useful Results

1. Reformulate the query with different terminology
2. Search in the specific technology's GitHub issues or discussions
3. Try breaking the problem into smaller, more searchable sub-problems
4. If still no results, explicitly state the knowledge gap to the user and proceed with best available judgment

## Integrating Search Results into Work

### Citation Practices

- When a search result directly influences a design decision, mention the source
- When using a code pattern found through search, note any adaptations made
- Do not blindly copy code from search results — evaluate it for the user's context

### Knowledge Persistence

After completing a task that required significant research:
1. Record key findings in the auto memory directory
2. Note which search queries were most effective
3. Document any domain knowledge that will be useful in future sessions
4. Flag information that may become outdated quickly
