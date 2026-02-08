#!/usr/bin/env python3
"""
Knowledge Gap Assessor

Analyzes a task description or conversation log to identify potential knowledge
gaps that should be addressed through web search before implementation.

Usage:
    assess_knowledge_gaps.py <task-description-file>
    assess_knowledge_gaps.py --text "Your task description here"
    assess_knowledge_gaps.py --json "Your task description here"
    assess_knowledge_gaps.py --lang ja --text "タスクの説明"

Output:
    A structured report of identified knowledge gaps, suggested search queries,
    ambiguity flags, and red alert indicators.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CURRENT_YEAR: int = datetime.now().year

# Confidence thresholds (gap_count boundaries)
CONFIDENCE_THRESHOLD_HIGH: int = 0      # gap_count == 0 → high
CONFIDENCE_THRESHOLD_MEDIUM: int = 2    # gap_count <= 2 → medium, else low

# Tech name extraction: minimum length to avoid noise
TECH_NAME_MIN_LENGTH: int = 3

# Report formatting
REPORT_SEPARATOR_WIDTH: int = 60

# Maximum clarification questions per message (UX constraint)
MAX_QUESTIONS_PER_MESSAGE: int = 3

# Supported output languages
DEFAULT_LANGUAGE: str = "en"

# Stop words: common English words that should NOT be treated as technology names.
# Comprehensive list to reduce false positives in tech name extraction.
TECH_NAME_STOP_WORDS: frozenset[str] = frozenset({
    # Articles, pronouns, demonstratives
    "The", "This", "That", "These", "Those",
    "It", "Its",
    # Interrogatives
    "When", "What", "How", "Where", "Which", "Who", "Why",
    # Prepositions / conjunctions
    "For", "From", "With", "Into", "About", "Between", "Through",
    "After", "Before", "During", "Without", "Against", "Along",
    "And", "But", "Or", "Nor", "So", "Yet",
    # Pronouns
    "We", "He", "She", "They", "You",
    # Common verbs / auxiliaries (title-cased at sentence start)
    "Are", "Is", "Was", "Were", "Has", "Have", "Had",
    "Can", "Could", "Will", "Would", "Should", "May", "Might",
    "Do", "Does", "Did", "Been", "Being",
    # Common adjectives / adverbs
    "All", "Any", "Each", "Every", "Some", "Most", "Many",
    "New", "Old", "Also", "Just", "Not", "Now", "Then",
    "Here", "There", "Very", "More", "Less",
    # Misc high-frequency words
    "Use", "Set", "Get", "Let", "Add", "Run", "Try", "See",
    "Make", "Take", "Give", "Keep", "Put", "Say",
    "One", "Two", "Way", "Per",
    "Note", "Please", "Sure", "Yes",
    "Error", "File", "Type", "Data", "Test", "Code",
    "Need", "Want", "Like",
    # Sentence starters
    "If", "As", "At", "By", "In", "On", "To", "Up",
    "No",
})

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Patterns that suggest domain-specific knowledge is needed
DOMAIN_INDICATORS: dict[str, list[str]] = {
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
VERSION_PATTERNS: list[str] = [
    r"\b[vV]?\d+\.\d+(?:\.\d+)?\b",
    r"\b(latest|newest|current|recent|updated)\b",
    r"\b(upgrade|migrate|migration|breaking\s+change|deprecated)\b",
]

# Patterns that indicate ambiguity
AMBIGUITY_PATTERNS: dict[str, list[str]] = {
    "scope": [
        r"\b(fix|improve|update|refactor|clean\s+up|optimize)\b(?!.*\b(specifically|exactly|only|in\s+line|at\s+line)\b)",
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

# Red Alert patterns: user pushback indicating the AI's knowledge may be wrong.
# These are signals that the AI should STOP, VERIFY, and SEARCH — not defend.
RED_ALERT_PATTERNS: list[str] = [
    r"本当(に|そう)?[？?]",
    r"ちゃんと調べた[？?]?",
    r"私の知って(いる|る)情報と違う",
    r"それ(は)?間違(い|って)",
    r"違うと思う",
    r"そうじゃない",
    r"確認して(ください|くれ|ほしい)?",
    r"\b(is\s+that\s+(really|actually)\s+(true|correct|right))\b",
    r"\b(are\s+you\s+sure)\b",
    r"\b(did\s+you\s+(actually\s+)?(check|verify|look\s+it\s+up))\b",
    r"\b(that('s|\s+is)\s+(not\s+)?(wrong|incorrect|inaccurate|different\s+from))\b",
    r"\b(I\s+(don't\s+think|believe)\s+that('s|\s+is)\s+(right|correct))\b",
    r"\b(my\s+(understanding|information)\s+(is\s+)?different)\b",
    r"\b(double[\s-]check|fact[\s-]check)\b",
    r"\b(that\s+contradicts)\b",
    r"\b(actually[,\s]+it('s|\s+is))\b",
]

# Proper noun protection: patterns that look like they might be typos but
# should be investigated before correcting.
PROPER_NOUN_INDICATORS: list[str] = [
    r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b",             # CamelCase: likely class/product name
    r"\b[a-z]+(?:-[a-z]+){2,}\b",                     # kebab-case multi-part: likely package
    r"\b[a-z]+(?:_[a-z]+){2,}\b",                     # snake_case multi-part: likely identifier
    r"@[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+",               # Scoped packages: @org/pkg
    r"\b[a-z]+\.(js|ts|py|rs|go|rb|java|swift|kt)\b", # file-like names: express.js
]

# Tech name extraction pattern — includes lowercase-starting known tech patterns
TECH_EXTRACTION_PATTERNS: list[str] = [
    r"\b([A-Z][a-zA-Z]+(?:\.[jJ][sS]|\.[pP][yY]|\.[rR][sS])?)\b",  # PascalCase + extensions
    r"\b(k8s|npm|pnpm|yarn|bun|deno|esbuild|rollup|vite)\b",         # Known lowercase tech
    r"\b([a-z]+\.[jJ][sS])\b",                                        # express.js, vue.js, etc.
]

# ---------------------------------------------------------------------------
# i18n: Localized strings
# ---------------------------------------------------------------------------

LOCALE_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "report_title": "KNOWLEDGE GAP ASSESSMENT REPORT",
        "overall_confidence": "Overall Confidence",
        "domains_detected": "Domains Detected",
        "research_domains": "Research these domains before implementing.",
        "no_domains": "No specialized domains detected.",
        "version_sensitive_yes": "Version-Sensitive Content: YES",
        "version_sensitive_verify": "Verify current versions and check for breaking changes.",
        "version_sensitive_no": "Version-Sensitive Content: No",
        "ambiguity_flags": "Ambiguity Flags",
        "matched": "Matched",
        "no_ambiguity": "No significant ambiguity detected.",
        "suggested_searches": "Suggested Search Queries",
        "red_alerts": "RED ALERTS (User Pushback Detected)",
        "red_alert_warning": "STOP and VERIFY. The user is signaling that your information may be incorrect. Do NOT defend — investigate.",
        "no_red_alerts": "No red alert signals detected.",
        "proper_nouns": "Potential Proper Nouns (Do Not Auto-Correct)",
        "proper_noun_warning": "Investigate these before assuming they are typos.",
        "clarification_scope": "Clarify the exact boundaries of the task. What is included and excluded?",
        "clarification_behavior": "Specify expected behavior for error/edge cases. What should happen when things go wrong?",
        "clarification_architecture": "Identify the architectural constraints and preferences before choosing an approach.",
        "clarification_priority": "Determine which sub-tasks are most important and should be addressed first.",
        "clarification_default": "Ask the user for more details.",
        "usage_header": "Usage:",
        "usage_file": "  assess_knowledge_gaps.py <task-description-file>",
        "usage_text": '  assess_knowledge_gaps.py --text "Your task description"',
        "usage_json": '  assess_knowledge_gaps.py --json "Your task description"',
        "usage_lang": '  assess_knowledge_gaps.py --lang ja --text "タスクの説明"',
        "error_file_not_found": "Error: File not found: {}",
        "error_path_outside_cwd": "Error: File path must be under the current working directory: {}",
    },
    "ja": {
        "report_title": "知識ギャップ評価レポート",
        "overall_confidence": "総合信頼度",
        "domains_detected": "検出されたドメイン",
        "research_domains": "実装前にこれらのドメインを調査してください。",
        "no_domains": "特化ドメインは検出されませんでした。",
        "version_sensitive_yes": "バージョン依存コンテンツ: あり",
        "version_sensitive_verify": "現在のバージョンを確認し、破壊的変更がないか調べてください。",
        "version_sensitive_no": "バージョン依存コンテンツ: なし",
        "ambiguity_flags": "曖昧さフラグ",
        "matched": "マッチ",
        "no_ambiguity": "重大な曖昧さは検出されませんでした。",
        "suggested_searches": "推奨検索クエリ",
        "red_alerts": "レッドアラート（ユーザーからの異議検出）",
        "red_alert_warning": "停止して検証してください。ユーザーはあなたの情報が誤っている可能性を示唆しています。弁明せず、調査してください。",
        "no_red_alerts": "レッドアラートは検出されませんでした。",
        "proper_nouns": "固有名詞の可能性あり（自動修正禁止）",
        "proper_noun_warning": "タイポと決めつけず、まず調査してください。",
        "clarification_scope": "タスクの正確な境界を確認してください。何が含まれ、何が除外されるか？",
        "clarification_behavior": "エラー/エッジケースの期待動作を指定してください。問題発生時にどうなるべきか？",
        "clarification_architecture": "アプローチを選択する前に、アーキテクチャの制約と選好を特定してください。",
        "clarification_priority": "どのサブタスクが最も重要で、最初に取り組むべきか判断してください。",
        "clarification_default": "ユーザーに詳細を確認してください。",
        "usage_header": "使用方法:",
        "usage_file": "  assess_knowledge_gaps.py <タスク説明ファイル>",
        "usage_text": '  assess_knowledge_gaps.py --text "タスクの説明"',
        "usage_json": '  assess_knowledge_gaps.py --json "タスクの説明"',
        "usage_lang": '  assess_knowledge_gaps.py --lang ja --text "タスクの説明"',
        "error_file_not_found": "エラー: ファイルが見つかりません: {}",
        "error_path_outside_cwd": "エラー: ファイルパスはカレントディレクトリ配下である必要があります: {}",
    },
}


def t(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Get a localized string."""
    strings = LOCALE_STRINGS.get(lang, LOCALE_STRINGS[DEFAULT_LANGUAGE])
    return strings.get(key, LOCALE_STRINGS[DEFAULT_LANGUAGE].get(key, key))


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AmbiguityType(str, Enum):
    SCOPE = "scope"
    BEHAVIOR = "behavior"
    ARCHITECTURE = "architecture"
    PRIORITY = "priority"


class AmbiguityFlag(BaseModel):
    """A detected ambiguity in the task description."""
    type: AmbiguityType
    matched_text: str
    suggestion: str


class RedAlert(BaseModel):
    """A detected user-pushback signal indicating potential knowledge error."""
    matched_text: str
    pattern_category: str = Field(
        description="Whether the alert is from 'user_pushback' or 'contradiction'"
    )


class ProperNoun(BaseModel):
    """A detected potential proper noun that should not be auto-corrected."""
    text: str
    pattern_type: str = Field(
        description="Pattern type: camelCase, kebab-case, snake_case, scoped_package, file_like"
    )


class AnalysisResult(BaseModel):
    """Complete result of a knowledge gap analysis."""
    domains_detected: list[str] = Field(default_factory=list)
    version_sensitive: bool = False
    ambiguity_flags: list[AmbiguityFlag] = Field(default_factory=list)
    suggested_searches: list[str] = Field(default_factory=list)
    confidence_assessment: ConfidenceLevel = ConfidenceLevel.HIGH
    red_alerts: list[RedAlert] = Field(default_factory=list)
    proper_nouns: list[ProperNoun] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Analysis Functions
# ---------------------------------------------------------------------------

def detect_domains(text: str) -> list[str]:
    """Detect specialized domains mentioned in the text."""
    domains: list[str] = []
    for domain, patterns in DOMAIN_INDICATORS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                domains.append(domain)
                break
    return domains


def detect_version_sensitive(text: str) -> bool:
    """Check if the text contains version-sensitive content."""
    for pattern in VERSION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def detect_ambiguity(text: str, lang: str = DEFAULT_LANGUAGE) -> list[AmbiguityFlag]:
    """Detect ambiguous requirements in the text."""
    flags: list[AmbiguityFlag] = []
    for ambiguity_type_str, patterns in AMBIGUITY_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ambiguity_type = AmbiguityType(ambiguity_type_str)
                flags.append(AmbiguityFlag(
                    type=ambiguity_type,
                    matched_text=match.group(0),
                    suggestion=get_clarification_suggestion(ambiguity_type, lang),
                ))
                break
    return flags


def detect_red_alerts(text: str) -> list[RedAlert]:
    """Detect user-pushback signals that indicate potential knowledge errors.

    These are RED ALERTS: the user is telling us we might be wrong.
    The correct response is to STOP, VERIFY, and SEARCH — never to defend.
    """
    alerts: list[RedAlert] = []
    for pattern in RED_ALERT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            alerts.append(RedAlert(
                matched_text=match.group(0),
                pattern_category="user_pushback",
            ))
    return alerts


def detect_proper_nouns(text: str) -> list[ProperNoun]:
    """Detect potential proper nouns that should not be auto-corrected as typos.

    The AI should investigate unknown terms before assuming they are errors.
    """
    pattern_type_map = [
        (PROPER_NOUN_INDICATORS[0], "camelCase"),
        (PROPER_NOUN_INDICATORS[1], "kebab-case"),
        (PROPER_NOUN_INDICATORS[2], "snake_case"),
        (PROPER_NOUN_INDICATORS[3], "scoped_package"),
        (PROPER_NOUN_INDICATORS[4], "file_like"),
    ]

    nouns: list[ProperNoun] = []
    seen: set[str] = set()

    for pattern, ptype in pattern_type_map:
        for match in re.finditer(pattern, text):
            term = match.group(0)
            if term not in seen:
                seen.add(term)
                nouns.append(ProperNoun(text=term, pattern_type=ptype))

    return nouns


def extract_tech_names(text: str) -> set[str]:
    """Extract potential technology names from the text."""
    techs: set[str] = set()
    for pattern in TECH_EXTRACTION_PATTERNS:
        for match in re.finditer(pattern, text):
            name = match.group(1) if match.lastindex else match.group(0)
            if (
                len(name) >= TECH_NAME_MIN_LENGTH
                and name not in TECH_NAME_STOP_WORDS
            ):
                techs.add(name)
    return techs


def generate_search_suggestions(
    text: str,
    domains: list[str],
    version_sensitive: bool,
) -> list[str]:
    """Generate suggested search queries based on analysis."""
    suggestions: list[str] = []

    techs = extract_tech_names(text)
    for tech in sorted(techs):
        suggestions.append(f"{tech} documentation official")
        if version_sensitive:
            suggestions.append(
                f"{tech} latest changes breaking changes {CURRENT_YEAR}"
            )

    domain_queries: dict[str, str] = {
        "legal": "current regulatory requirements compliance",
        "finance": "accounting standards current rules",
        "infrastructure": "deployment best practices current",
        "security": "security best practices OWASP current",
        "database": "database optimization patterns",
        "frontend": "frontend framework best practices current",
        "ml_ai": "machine learning implementation patterns current",
    }
    for domain in domains:
        if domain in domain_queries:
            suggestions.append(domain_queries[domain])

    return suggestions


def get_clarification_suggestion(
    ambiguity_type: AmbiguityType,
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    """Return a localized suggestion for resolving a specific type of ambiguity."""
    key_map = {
        AmbiguityType.SCOPE: "clarification_scope",
        AmbiguityType.BEHAVIOR: "clarification_behavior",
        AmbiguityType.ARCHITECTURE: "clarification_architecture",
        AmbiguityType.PRIORITY: "clarification_priority",
    }
    key = key_map.get(ambiguity_type, "clarification_default")
    return t(key, lang)


def assess_confidence(
    domains: list[str],
    ambiguity_flags: list[AmbiguityFlag],
    red_alerts: list[RedAlert],
) -> ConfidenceLevel:
    """Assess overall confidence based on detected gaps.

    Red alerts immediately drop confidence to LOW — the user is telling us
    something is wrong.
    """
    if red_alerts:
        return ConfidenceLevel.LOW

    gap_count = len(domains) + len(ambiguity_flags)
    if gap_count <= CONFIDENCE_THRESHOLD_HIGH:
        return ConfidenceLevel.HIGH
    elif gap_count <= CONFIDENCE_THRESHOLD_MEDIUM:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


def analyze_text(text: str, lang: str = DEFAULT_LANGUAGE) -> AnalysisResult:
    """Analyze task description for knowledge gaps and ambiguity."""
    domains = detect_domains(text)
    version_sensitive = detect_version_sensitive(text)
    ambiguity_flags = detect_ambiguity(text, lang)
    red_alerts = detect_red_alerts(text)
    proper_nouns = detect_proper_nouns(text)
    suggested_searches = generate_search_suggestions(text, domains, version_sensitive)
    confidence = assess_confidence(domains, ambiguity_flags, red_alerts)

    return AnalysisResult(
        domains_detected=domains,
        version_sensitive=version_sensitive,
        ambiguity_flags=ambiguity_flags,
        suggested_searches=suggested_searches,
        confidence_assessment=confidence,
        red_alerts=red_alerts,
        proper_nouns=proper_nouns,
    )


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

def format_report(result: AnalysisResult, lang: str = DEFAULT_LANGUAGE) -> str:
    """Format analysis results as a human-readable, localized report."""
    sep = "=" * REPORT_SEPARATOR_WIDTH
    lines: list[str] = []
    lines.append(sep)
    lines.append(t("report_title", lang))
    lines.append(sep)

    lines.append(
        f"\n{t('overall_confidence', lang)}: "
        f"{result.confidence_assessment.value.upper()}"
    )

    # Domains
    if result.domains_detected:
        lines.append(
            f"\n{t('domains_detected', lang)}: "
            f"{', '.join(result.domains_detected)}"
        )
        lines.append(f"  -> {t('research_domains', lang)}")
    else:
        lines.append(f"\n{t('no_domains', lang)}")

    # Version sensitivity
    if result.version_sensitive:
        lines.append(f"\n{t('version_sensitive_yes', lang)}")
        lines.append(f"  -> {t('version_sensitive_verify', lang)}")
    else:
        lines.append(f"\n{t('version_sensitive_no', lang)}")

    # Red Alerts (highest priority — shown first)
    if result.red_alerts:
        lines.append(
            f"\n!!! {t('red_alerts', lang)} ({len(result.red_alerts)}) !!!"
        )
        lines.append(f"  -> {t('red_alert_warning', lang)}")
        for alert in result.red_alerts:
            lines.append(f'  [RED ALERT] "{alert.matched_text}"')
    else:
        lines.append(f"\n{t('no_red_alerts', lang)}")

    # Ambiguity flags
    if result.ambiguity_flags:
        lines.append(
            f"\n{t('ambiguity_flags', lang)} ({len(result.ambiguity_flags)}):"
        )
        for flag in result.ambiguity_flags:
            lines.append(
                f'  [{flag.type.value.upper()}] {t("matched", lang)}: '
                f'"{flag.matched_text}"'
            )
            lines.append(f"    -> {flag.suggestion}")
    else:
        lines.append(f"\n{t('no_ambiguity', lang)}")

    # Proper nouns
    if result.proper_nouns:
        lines.append(
            f"\n{t('proper_nouns', lang)} ({len(result.proper_nouns)}):"
        )
        lines.append(f"  -> {t('proper_noun_warning', lang)}")
        for noun in result.proper_nouns:
            lines.append(f'  [{noun.pattern_type}] "{noun.text}"')

    # Search suggestions
    if result.suggested_searches:
        lines.append(
            f"\n{t('suggested_searches', lang)} "
            f"({len(result.suggested_searches)}):"
        )
        for i, query in enumerate(result.suggested_searches, 1):
            lines.append(f"  {i}. {query}")

    lines.append(f"\n{sep}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File Path Validation
# ---------------------------------------------------------------------------

def validate_file_path(raw_path: str) -> Path:
    """Validate that a file path exists and is under the current working directory.

    Prevents path traversal attacks when this script is invoked as part of an
    automated pipeline.
    """
    file_path = Path(raw_path).resolve()
    cwd = Path.cwd().resolve()

    if not file_path.exists():
        raise FileNotFoundError(raw_path)

    # Ensure the resolved path is under cwd
    try:
        file_path.relative_to(cwd)
    except ValueError:
        raise PermissionError(raw_path)

    return file_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> tuple[str, str, bool]:
    """Parse CLI arguments. Returns (text, lang, json_mode)."""
    lang = DEFAULT_LANGUAGE
    json_mode = False
    text: Optional[str] = None

    args = argv[1:]  # skip program name
    i = 0

    while i < len(args):
        arg = args[i]

        if arg == "--lang" and i + 1 < len(args):
            lang = args[i + 1]
            if lang not in LOCALE_STRINGS:
                lang = DEFAULT_LANGUAGE
            i += 2
            continue

        if arg == "--json":
            json_mode = True
            remaining = args[i + 1:]
            # Consume remaining as text, or fall back to stdin
            remaining_non_flag = [
                a for a in remaining
                if a not in ("--lang", "--text", "--json")
            ]
            if remaining_non_flag:
                text = " ".join(remaining_non_flag)
            else:
                text = sys.stdin.read()
            return text, lang, json_mode

        if arg == "--text":
            remaining = args[i + 1:]
            remaining_non_flag = []
            j = 0
            while j < len(remaining):
                if remaining[j] == "--lang" and j + 1 < len(remaining):
                    lang = remaining[j + 1]
                    if lang not in LOCALE_STRINGS:
                        lang = DEFAULT_LANGUAGE
                    j += 2
                    continue
                remaining_non_flag.append(remaining[j])
                j += 1
            if remaining_non_flag:
                text = " ".join(remaining_non_flag)
            else:
                text = sys.stdin.read()
            return text, lang, False

        # Assume it's a file path
        file_path = validate_file_path(arg)
        text = file_path.read_text()
        i += 1

    if text is None:
        return "", lang, False

    return text, lang, json_mode


def main() -> None:
    if len(sys.argv) < 2:
        lang = DEFAULT_LANGUAGE
        print(t("usage_header", lang))
        print(t("usage_file", lang))
        print(t("usage_text", lang))
        print(t("usage_json", lang))
        print(t("usage_lang", lang))
        sys.exit(1)

    try:
        text, lang, json_mode = parse_args(sys.argv)
    except FileNotFoundError as e:
        print(t("error_file_not_found", DEFAULT_LANGUAGE).format(e))
        sys.exit(1)
    except PermissionError as e:
        print(t("error_path_outside_cwd", DEFAULT_LANGUAGE).format(e))
        sys.exit(1)

    if not text.strip():
        print(t("usage_header", DEFAULT_LANGUAGE))
        sys.exit(1)

    result = analyze_text(text, lang)

    if json_mode:
        print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))
    else:
        print(format_report(result, lang))


if __name__ == "__main__":
    main()
