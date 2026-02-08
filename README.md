# Proactive Learning Skill

A Claude Code skill that transforms Claude from a reactive assistant into an actively learning agent. It systematically acquires domain knowledge through web searches, reduces ambiguity through structured user interaction, and builds a persistent knowledge base across sessions.

## Overview

This skill addresses three common failure modes in AI-assisted development:

1. **Stale knowledge** - Acting on outdated information when current docs are a search away
2. **Unresolved ambiguity** - Building the wrong thing because requirements weren't clarified
3. **Lost learnings** - Re-discovering the same domain knowledge across sessions

## Skill Structure

```
proactive-learning/
├── SKILL.md                              # Core skill definition and workflows
├── references/
│   ├── clarification_patterns.md         # Ambiguity taxonomy and question templates
│   └── search_strategies.md              # Search decision framework and query patterns
├── scripts/
│   └── assess_knowledge_gaps.py          # Automated knowledge gap analysis tool
├── LICENSE
└── README.md
```

## Three Core Workflows

### Workflow 1: Proactive Knowledge Acquisition

Before implementing, research. Uses WebSearch to fill knowledge gaps by checking official documentation, recent changes, domain conventions, and known pitfalls. Includes clear decision rules for when to search vs. when to skip.

### Workflow 2: Ambiguity Reduction

Scans user requests for six types of ambiguity (scope, architectural, behavioral, priority, convention, domain) and resolves them through structured questions. Always proposes defaults so users can confirm quickly rather than write detailed answers.

### Workflow 3: Persistent Knowledge Management

Records domain knowledge, patterns, and pitfalls discovered during tasks into the auto memory directory. Keeps learnings indexed and accessible for future sessions.

## Installation

Install this skill via the Claude Code slash command:

```
/install-skill https://github.com/AtsushiYamashita/skills-proactive-Learning
```

Or manually place the skill directory in your Claude Code skills path.

## Scripts

### assess_knowledge_gaps.py

Analyzes a task description to identify potential knowledge gaps before starting work.

```bash
# Analyze a task description file
python scripts/assess_knowledge_gaps.py task.txt

# Analyze inline text
python scripts/assess_knowledge_gaps.py --text "Migrate our PostgreSQL 14 database to use JSONB columns with proper indexing"

# Get JSON output for programmatic use
python scripts/assess_knowledge_gaps.py --json "Set up OAuth 2.0 with PKCE flow for our React SPA"
```

## License

MIT License - see [LICENSE](LICENSE) for details.
