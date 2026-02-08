#!/usr/bin/env python3
"""
Knowledge Gap Assessor

Analyzes a task description or conversation log to identify potential knowledge
gaps that should be addressed through web search before implementation.

Usage:
    assess_knowledge_gaps.py <task-description-file>
    assess_knowledge_gaps.py --text "Your task description here"

Output:
    A structured report of identified knowledge gaps, suggested search queries,
    and ambiguity flags that should be clarified with the user.
"""

import sys
import json
import re
from pathlib import Path


# Patterns that suggest domain-specific knowledge is needed
DOMAIN_INDICATORS = {
    "legal": [
        r"\b(GDPR|HIPAA|SOC\s*2|PCI[\s-]DSS|compliance|regulation|privacy\s+policy)\b",
        r"\b(copyright|trademark|patent|license|liability)\b",
    ],
    "finance": [
        r"\b(GAAP|IFRS|revenue\s+recognition|depreciation|amortization)\b",
        r"\b(tax|invoice|accounting|ledger|reconciliation)\b",
    ],
    "infrastructure": [
        r"\b(Kubernetes|k8s|Docker|terraform|ansible|helm|ECS|EKS|GKE|AKS)\b",
        r"\b(CI/CD|pipeline|deployment|load\s+balancer|CDN|DNS)\b",
    ],
    "security": [
        r"\b(OAuth|JWT|SAML|SSO|RBAC|encryption|certificate|TLS|SSL)\b",
        r"\b(vulnerability|CVE|injection|XSS|CSRF|authentication)\b",
    ],
    "database": [
        r"\b(migration|schema|index|replication|sharding|partitioning)\b",
        r"\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|DynamoDB)\b",
    ],
    "frontend": [
        r"\b(React|Vue|Angular|Svelte|Next\.js|Nuxt|Remix|Astro)\b",
        r"\b(SSR|SSG|hydration|bundle|webpack|vite|turbopack)\b",
    ],
    "ml_ai": [
        r"\b(model|training|inference|embedding|transformer|fine[\s-]?tun)\b",
        r"\b(PyTorch|TensorFlow|HuggingFace|LLM|RAG|vector\s+database)\b",
    ],
}

# Patterns that suggest version-sensitive information
VERSION_PATTERNS = [
    r"\b[vV]?\d+\.\d+(?:\.\d+)?\b",  # Version numbers like v1.2.3
    r"\b(latest|newest|current|recent|updated)\b",
    r"\b(upgrade|migrate|migration|breaking\s+change|deprecated)\b",
]

# Patterns that indicate ambiguity
AMBIGUITY_PATTERNS = {
    "scope": [
        r"\b(fix|improve|update|refactor|clean\s+up|optimize)\b(?!.*\bspecifically\b)",
        r"\b(everything|all|entire|whole)\b",
    ],
    "behavior": [
        r"\b(handle|manage|process)\b.*\b(error|failure|edge\s+case)\b",
        r"\b(gracefully|properly|correctly|appropriately)\b",
    ],
    "architecture": [
        r"\b(should\s+(?:we|I)|best\s+way|approach|strategy|pattern)\b",
        r"\b(design|architect|structure|organize)\b",
    ],
    "priority": [
        r"\b(and\s+also|plus|additionally|as\s+well\s+as)\b",
        r"\b(first|then|after\s+that|eventually)\b",
    ],
}


def analyze_text(text: str) -> dict:
    """Analyze task description for knowledge gaps and ambiguity."""
    results = {
        "domains_detected": [],
        "version_sensitive": False,
        "ambiguity_flags": [],
        "suggested_searches": [],
        "confidence_assessment": "high",
    }

    text_lower = text.lower()

    # Detect domains
    for domain, patterns in DOMAIN_INDICATORS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                results["domains_detected"].append(domain)
                break

    # Check for version-sensitive content
    for pattern in VERSION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            results["version_sensitive"] = True
            break

    # Detect ambiguity
    for ambiguity_type, patterns in AMBIGUITY_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                results["ambiguity_flags"].append({
                    "type": ambiguity_type,
                    "matched_text": match.group(0),
                    "suggestion": get_clarification_suggestion(ambiguity_type),
                })
                break

    # Generate search suggestions
    results["suggested_searches"] = generate_search_suggestions(
        text, results["domains_detected"], results["version_sensitive"]
    )

    # Assess overall confidence
    gap_count = len(results["domains_detected"]) + len(results["ambiguity_flags"])
    if gap_count == 0:
        results["confidence_assessment"] = "high"
    elif gap_count <= 2:
        results["confidence_assessment"] = "medium"
    else:
        results["confidence_assessment"] = "low"

    return results


def get_clarification_suggestion(ambiguity_type: str) -> str:
    """Return a suggestion for resolving a specific type of ambiguity."""
    suggestions = {
        "scope": "Clarify the exact boundaries of the task. What is included and excluded?",
        "behavior": "Specify expected behavior for error/edge cases. What should happen when things go wrong?",
        "architecture": "Identify the architectural constraints and preferences before choosing an approach.",
        "priority": "Determine which sub-tasks are most important and should be addressed first.",
    }
    return suggestions.get(ambiguity_type, "Ask the user for more details.")


def generate_search_suggestions(text: str, domains: list, version_sensitive: bool) -> list:
    """Generate suggested search queries based on analysis."""
    suggestions = []

    # Extract potential technology names (capitalized words, known patterns)
    tech_pattern = r"\b([A-Z][a-zA-Z]+(?:\.js|\.py|\.rs)?)\b"
    techs = set(re.findall(tech_pattern, text))

    for tech in techs:
        if len(tech) > 2 and tech not in {"The", "This", "That", "When", "What", "How", "For"}:
            suggestions.append(f"{tech} documentation official")
            if version_sensitive:
                suggestions.append(f"{tech} latest changes breaking changes 2026")

    for domain in domains:
        domain_queries = {
            "legal": "current regulatory requirements compliance",
            "finance": "accounting standards current rules",
            "infrastructure": "deployment best practices current",
            "security": "security best practices OWASP current",
            "database": "database optimization patterns",
            "frontend": "frontend framework best practices current",
            "ml_ai": "machine learning implementation patterns current",
        }
        if domain in domain_queries:
            suggestions.append(domain_queries[domain])

    return suggestions


def format_report(results: dict) -> str:
    """Format analysis results as a readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("KNOWLEDGE GAP ASSESSMENT REPORT")
    lines.append("=" * 60)

    lines.append(f"\nOverall Confidence: {results['confidence_assessment'].upper()}")

    if results["domains_detected"]:
        lines.append(f"\nDomains Detected: {', '.join(results['domains_detected'])}")
        lines.append("  → Research these domains before implementing.")
    else:
        lines.append("\nNo specialized domains detected.")

    if results["version_sensitive"]:
        lines.append("\nVersion-Sensitive Content: YES")
        lines.append("  → Verify current versions and check for breaking changes.")
    else:
        lines.append("\nVersion-Sensitive Content: No")

    if results["ambiguity_flags"]:
        lines.append(f"\nAmbiguity Flags ({len(results['ambiguity_flags'])}):")
        for flag in results["ambiguity_flags"]:
            lines.append(f"  [{flag['type'].upper()}] Matched: \"{flag['matched_text']}\"")
            lines.append(f"    → {flag['suggestion']}")
    else:
        lines.append("\nNo significant ambiguity detected.")

    if results["suggested_searches"]:
        lines.append(f"\nSuggested Search Queries ({len(results['suggested_searches'])}):")
        for i, query in enumerate(results["suggested_searches"], 1):
            lines.append(f"  {i}. {query}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  assess_knowledge_gaps.py <task-description-file>")
        print('  assess_knowledge_gaps.py --text "Your task description"')
        sys.exit(1)

    if sys.argv[1] == "--text" and len(sys.argv) >= 3:
        text = " ".join(sys.argv[2:])
    elif sys.argv[1] == "--json":
        text = " ".join(sys.argv[2:]) if len(sys.argv) >= 3 else sys.stdin.read()
        results = analyze_text(text)
        print(json.dumps(results, indent=2))
        sys.exit(0)
    else:
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        text = file_path.read_text()

    results = analyze_text(text)
    print(format_report(results))


if __name__ == "__main__":
    main()
