"""Comprehensive tests for assess_knowledge_gaps.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure the scripts directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from assess_knowledge_gaps import (
    CONFIDENCE_THRESHOLD_HIGH,
    CONFIDENCE_THRESHOLD_MEDIUM,
    CURRENT_YEAR,
    DEFAULT_LANGUAGE,
    TECH_NAME_MIN_LENGTH,
    TECH_NAME_STOP_WORDS,
    AmbiguityFlag,
    AmbiguityType,
    AnalysisResult,
    ConfidenceLevel,
    ProperNoun,
    RedAlert,
    analyze_text,
    assess_confidence,
    detect_ambiguity,
    detect_domains,
    detect_proper_nouns,
    detect_red_alerts,
    detect_version_sensitive,
    extract_tech_names,
    format_report,
    generate_search_suggestions,
    get_clarification_suggestion,
    t,
    validate_file_path,
)

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "assess_knowledge_gaps.py"


# =========================================================================
# Pydantic Model Tests
# =========================================================================

class TestPydanticModels:
    """Ensure Pydantic models validate and serialize correctly."""

    def test_ambiguity_flag_creation(self):
        flag = AmbiguityFlag(
            type=AmbiguityType.SCOPE,
            matched_text="fix",
            suggestion="Clarify scope",
        )
        assert flag.type == AmbiguityType.SCOPE
        assert flag.matched_text == "fix"

    def test_red_alert_creation(self):
        alert = RedAlert(
            matched_text="are you sure",
            pattern_category="user_pushback",
        )
        assert alert.pattern_category == "user_pushback"

    def test_proper_noun_creation(self):
        noun = ProperNoun(text="MyComponent", pattern_type="camelCase")
        assert noun.text == "MyComponent"

    def test_analysis_result_defaults(self):
        result = AnalysisResult()
        assert result.domains_detected == []
        assert result.version_sensitive is False
        assert result.confidence_assessment == ConfidenceLevel.HIGH
        assert result.red_alerts == []
        assert result.proper_nouns == []

    def test_analysis_result_json_serialization(self):
        result = AnalysisResult(
            domains_detected=["security"],
            version_sensitive=True,
            confidence_assessment=ConfidenceLevel.LOW,
            red_alerts=[
                RedAlert(matched_text="are you sure", pattern_category="user_pushback")
            ],
        )
        data = result.model_dump(mode="json")
        assert data["domains_detected"] == ["security"]
        assert data["confidence_assessment"] == "low"
        assert len(data["red_alerts"]) == 1

        # Round-trip
        restored = AnalysisResult.model_validate(data)
        assert restored.domains_detected == ["security"]


# =========================================================================
# Domain Detection Tests
# =========================================================================

class TestDomainDetection:
    def test_legal_gdpr(self):
        assert "legal" in detect_domains("We need GDPR compliance for user data")

    def test_legal_hipaa(self):
        assert "legal" in detect_domains("Ensure HIPAA compliance")

    def test_finance_gaap(self):
        assert "finance" in detect_domains("Follow GAAP revenue recognition rules")

    def test_finance_tax(self):
        assert "finance" in detect_domains("Calculate the tax for this invoice")

    def test_infrastructure_k8s(self):
        assert "infrastructure" in detect_domains("Deploy to Kubernetes cluster")

    def test_infrastructure_k8s_abbreviation(self):
        assert "infrastructure" in detect_domains("Scale k8s pods to 5")

    def test_security_oauth(self):
        assert "security" in detect_domains("Implement OAuth 2.0 flow")

    def test_security_jwt(self):
        assert "security" in detect_domains("Validate the JWT token")

    def test_database_postgresql(self):
        assert "database" in detect_domains("Migrate PostgreSQL schema")

    def test_frontend_react(self):
        assert "frontend" in detect_domains("Create a React component")

    def test_ml_ai_llm(self):
        assert "ml_ai" in detect_domains("Fine-tune the LLM for our use case")

    def test_no_domain(self):
        assert detect_domains("Print hello world") == []

    def test_multiple_domains(self):
        domains = detect_domains(
            "Set up OAuth for the React frontend and migrate PostgreSQL schema"
        )
        assert "security" in domains
        assert "frontend" in domains
        assert "database" in domains


# =========================================================================
# Version Sensitivity Tests
# =========================================================================

class TestVersionSensitivity:
    def test_explicit_version(self):
        assert detect_version_sensitive("Upgrade to v3.2.1") is True

    def test_version_without_v_prefix(self):
        assert detect_version_sensitive("Use React 18.2.0") is True

    def test_latest_keyword(self):
        assert detect_version_sensitive("Use the latest version") is True

    def test_deprecated_keyword(self):
        assert detect_version_sensitive("This API is deprecated") is True

    def test_migration_keyword(self):
        assert detect_version_sensitive("Breaking change in the new release") is True

    def test_no_version_sensitivity(self):
        assert detect_version_sensitive("Write a hello world program") is False


# =========================================================================
# Ambiguity Detection Tests
# =========================================================================

class TestAmbiguityDetection:
    def test_scope_ambiguity_fix(self):
        flags = detect_ambiguity("Fix the authentication")
        types = [f.type for f in flags]
        assert AmbiguityType.SCOPE in types

    def test_scope_ambiguity_improve(self):
        flags = detect_ambiguity("Improve performance")
        types = [f.type for f in flags]
        assert AmbiguityType.SCOPE in types

    def test_scope_no_false_positive_with_specificity(self):
        """'Fix specifically in line 3' should not trigger scope ambiguity."""
        flags = detect_ambiguity("Fix the typo specifically in line 3")
        scope_flags = [f for f in flags if f.type == AmbiguityType.SCOPE]
        assert len(scope_flags) == 0

    def test_behavior_ambiguity(self):
        flags = detect_ambiguity("Handle errors gracefully")
        types = [f.type for f in flags]
        assert AmbiguityType.BEHAVIOR in types

    def test_architecture_ambiguity(self):
        flags = detect_ambiguity("What is the best way to structure this?")
        types = [f.type for f in flags]
        assert AmbiguityType.ARCHITECTURE in types

    def test_priority_ambiguity(self):
        flags = detect_ambiguity("Fix the login and also improve the dashboard")
        types = [f.type for f in flags]
        assert AmbiguityType.PRIORITY in types

    def test_no_ambiguity(self):
        assert detect_ambiguity("Return 42") == []

    def test_ambiguity_localized_suggestion_ja(self):
        flags = detect_ambiguity("Fix the authentication", lang="ja")
        scope_flags = [f for f in flags if f.type == AmbiguityType.SCOPE]
        assert len(scope_flags) > 0
        assert "境界" in scope_flags[0].suggestion  # Japanese word for "boundaries"


# =========================================================================
# Red Alert Detection Tests
# =========================================================================

class TestRedAlertDetection:
    def test_english_are_you_sure(self):
        alerts = detect_red_alerts("Are you sure about that?")
        assert len(alerts) > 0

    def test_english_did_you_check(self):
        alerts = detect_red_alerts("Did you actually check that?")
        assert len(alerts) > 0

    def test_english_thats_wrong(self):
        alerts = detect_red_alerts("That's wrong, the API returns a list")
        assert len(alerts) > 0

    def test_english_my_information_different(self):
        alerts = detect_red_alerts("My understanding is different")
        assert len(alerts) > 0

    def test_english_double_check(self):
        alerts = detect_red_alerts("Can you double-check that?")
        assert len(alerts) > 0

    def test_english_fact_check(self):
        alerts = detect_red_alerts("Please fact-check this claim")
        assert len(alerts) > 0

    def test_japanese_hontou(self):
        alerts = detect_red_alerts("本当に？")
        assert len(alerts) > 0

    def test_japanese_chanto_shirabeta(self):
        alerts = detect_red_alerts("ちゃんと調べた？")
        assert len(alerts) > 0

    def test_japanese_chigau_to_omou(self):
        alerts = detect_red_alerts("違うと思う")
        assert len(alerts) > 0

    def test_japanese_watashi_no_jouhou(self):
        alerts = detect_red_alerts("私の知っている情報と違う")
        assert len(alerts) > 0

    def test_japanese_kakunin_shite(self):
        alerts = detect_red_alerts("確認してください")
        assert len(alerts) > 0

    def test_no_red_alert(self):
        alerts = detect_red_alerts("Please implement the login feature")
        assert len(alerts) == 0

    def test_red_alert_forces_low_confidence(self):
        """Red alerts should always result in LOW confidence."""
        result = analyze_text("Are you sure? That's wrong.")
        assert result.confidence_assessment == ConfidenceLevel.LOW


# =========================================================================
# Proper Noun Detection Tests
# =========================================================================

class TestProperNounDetection:
    def test_camel_case(self):
        nouns = detect_proper_nouns("Check the MyCustomComponent class")
        texts = [n.text for n in nouns]
        assert "MyCustomComponent" in texts

    def test_kebab_case_package(self):
        nouns = detect_proper_nouns("Install my-awesome-package")
        texts = [n.text for n in nouns]
        assert "my-awesome-package" in texts

    def test_snake_case_identifier(self):
        nouns = detect_proper_nouns("Call the my_custom_handler function")
        texts = [n.text for n in nouns]
        assert "my_custom_handler" in texts

    def test_scoped_package(self):
        nouns = detect_proper_nouns("Use @angular/core for DI")
        texts = [n.text for n in nouns]
        assert "@angular/core" in texts

    def test_file_like_name(self):
        nouns = detect_proper_nouns("Use express.js for routing")
        texts = [n.text for n in nouns]
        assert "express.js" in texts

    def test_no_duplicates(self):
        nouns = detect_proper_nouns("MyComponent and MyComponent again")
        my_comp = [n for n in nouns if n.text == "MyComponent"]
        assert len(my_comp) == 1


# =========================================================================
# Tech Name Extraction Tests
# =========================================================================

class TestTechNameExtraction:
    def test_pascal_case_tech(self):
        techs = extract_tech_names("Use React and Vue for the frontend")
        assert "React" in techs
        assert "Vue" in techs

    def test_stop_words_excluded(self):
        techs = extract_tech_names("The When This That How")
        assert len(techs) == 0

    def test_extended_stop_words(self):
        """All new stop words should be excluded."""
        techs = extract_tech_names(
            "If We Are Is Was Were Has Have Had Can Could Will Would Should "
            "May Might Do Does Did Been Being"
        )
        assert len(techs) == 0

    def test_known_lowercase_tech(self):
        techs = extract_tech_names("Use npm and vite for the build")
        assert "npm" in techs
        assert "vite" in techs

    def test_lowercase_js_extension(self):
        techs = extract_tech_names("Use express.js for the server")
        assert "express.js" in techs

    def test_min_length_filter(self):
        """Names shorter than TECH_NAME_MIN_LENGTH should be excluded."""
        techs = extract_tech_names("Go is great")
        # "Go" is only 2 chars, should be excluded by min length
        assert "Go" not in techs

    def test_nextjs_detected(self):
        techs = extract_tech_names("Build with Next.js")
        # Should capture "Next" at minimum via PascalCase pattern
        assert any("Next" in t for t in techs)


# =========================================================================
# Search Suggestion Tests
# =========================================================================

class TestSearchSuggestions:
    def test_tech_based_suggestion(self):
        suggestions = generate_search_suggestions(
            "Migrate to React 18", ["frontend"], True
        )
        assert any("React" in s for s in suggestions)
        assert any(str(CURRENT_YEAR) in s for s in suggestions)

    def test_domain_based_suggestion(self):
        suggestions = generate_search_suggestions(
            "Set up encryption", ["security"], False
        )
        assert any("OWASP" in s for s in suggestions)

    def test_no_hardcoded_year(self):
        """Year should always be dynamic, not hardcoded."""
        suggestions = generate_search_suggestions(
            "Upgrade React to latest", ["frontend"], True
        )
        year_suggestions = [s for s in suggestions if "2026" in s or "2025" in s]
        for s in year_suggestions:
            assert str(CURRENT_YEAR) in s

    def test_empty_input(self):
        suggestions = generate_search_suggestions("hello", [], False)
        assert suggestions == []


# =========================================================================
# Confidence Assessment Tests
# =========================================================================

class TestConfidenceAssessment:
    def test_high_confidence(self):
        assert assess_confidence([], [], []) == ConfidenceLevel.HIGH

    def test_medium_confidence(self):
        flag = AmbiguityFlag(
            type=AmbiguityType.SCOPE, matched_text="fix", suggestion="x"
        )
        assert assess_confidence(["security"], [flag], []) == ConfidenceLevel.MEDIUM

    def test_low_confidence_many_gaps(self):
        flags = [
            AmbiguityFlag(type=AmbiguityType.SCOPE, matched_text="fix", suggestion="x"),
            AmbiguityFlag(type=AmbiguityType.BEHAVIOR, matched_text="handle", suggestion="x"),
        ]
        assert assess_confidence(["security", "database"], flags, []) == ConfidenceLevel.LOW

    def test_red_alert_forces_low(self):
        """Any red alert immediately drops to LOW regardless of gap count."""
        alert = RedAlert(matched_text="are you sure", pattern_category="user_pushback")
        assert assess_confidence([], [], [alert]) == ConfidenceLevel.LOW


# =========================================================================
# i18n Tests
# =========================================================================

class TestI18n:
    def test_english_default(self):
        assert t("report_title") == "KNOWLEDGE GAP ASSESSMENT REPORT"

    def test_japanese_report_title(self):
        assert t("report_title", "ja") == "知識ギャップ評価レポート"

    def test_fallback_to_english(self):
        """Unknown language falls back to English."""
        assert t("report_title", "fr") == "KNOWLEDGE GAP ASSESSMENT REPORT"

    def test_unknown_key_returns_key(self):
        assert t("nonexistent_key") == "nonexistent_key"

    def test_japanese_report_formatting(self):
        result = analyze_text("Reactコンポーネントを修正して", lang="ja")
        report = format_report(result, lang="ja")
        assert "知識ギャップ評価レポート" in report

    def test_japanese_clarification_suggestions(self):
        suggestion = get_clarification_suggestion(AmbiguityType.SCOPE, "ja")
        assert "境界" in suggestion


# =========================================================================
# Report Formatting Tests
# =========================================================================

class TestReportFormatting:
    def test_report_contains_separator(self):
        result = AnalysisResult()
        report = format_report(result)
        assert "=" * 60 in report

    def test_report_shows_red_alerts_when_present(self):
        result = AnalysisResult(
            red_alerts=[
                RedAlert(matched_text="are you sure", pattern_category="user_pushback")
            ]
        )
        report = format_report(result)
        assert "RED ALERT" in report
        assert "are you sure" in report

    def test_report_shows_proper_nouns(self):
        result = AnalysisResult(
            proper_nouns=[
                ProperNoun(text="MyComponent", pattern_type="camelCase")
            ]
        )
        report = format_report(result)
        assert "MyComponent" in report
        assert "Do Not Auto-Correct" in report

    def test_report_no_red_alerts_message(self):
        result = AnalysisResult()
        report = format_report(result)
        assert "No red alert" in report


# =========================================================================
# File Path Validation Tests
# =========================================================================

class TestFilePathValidation:
    def test_valid_path(self, tmp_path):
        test_file = tmp_path / "task.txt"
        test_file.write_text("test content")
        with patch("assess_knowledge_gaps.Path.cwd", return_value=tmp_path):
            result = validate_file_path(str(test_file))
            assert result == test_file.resolve()

    def test_nonexistent_path(self):
        with pytest.raises(FileNotFoundError):
            validate_file_path("/nonexistent/file.txt")

    def test_path_traversal_blocked(self, tmp_path):
        """Paths outside cwd should be rejected."""
        outside_file = Path("/etc/hostname")
        if outside_file.exists():
            with patch("assess_knowledge_gaps.Path.cwd", return_value=tmp_path):
                with pytest.raises(PermissionError):
                    validate_file_path(str(outside_file))


# =========================================================================
# End-to-End analyze_text Tests
# =========================================================================

class TestAnalyzeTextE2E:
    def test_complex_input(self):
        text = (
            "Migrate our PostgreSQL 14 database to use JSONB columns "
            "with proper indexing. Handle errors gracefully. "
            "Also update the React frontend and fix the OAuth flow."
        )
        result = analyze_text(text)
        assert "database" in result.domains_detected
        assert "frontend" in result.domains_detected
        assert "security" in result.domains_detected
        assert result.version_sensitive is True
        assert len(result.ambiguity_flags) > 0
        assert len(result.suggested_searches) > 0

    def test_red_alert_e2e(self):
        text = "Are you sure that's correct? My understanding is different."
        result = analyze_text(text)
        assert len(result.red_alerts) > 0
        assert result.confidence_assessment == ConfidenceLevel.LOW

    def test_japanese_red_alert_e2e(self):
        text = "本当に？ちゃんと調べた？私の知っている情報と違う"
        result = analyze_text(text)
        assert len(result.red_alerts) >= 3
        assert result.confidence_assessment == ConfidenceLevel.LOW

    def test_clean_input(self):
        text = "Return the sum of two integers"
        result = analyze_text(text)
        assert result.confidence_assessment == ConfidenceLevel.HIGH
        assert result.domains_detected == []
        assert result.red_alerts == []

    def test_proper_noun_preservation(self):
        text = "Use the MyCustomService class from @company/auth-lib"
        result = analyze_text(text)
        noun_texts = [n.text for n in result.proper_nouns]
        assert "MyCustomService" in noun_texts
        assert "@company/auth-lib" in noun_texts


# =========================================================================
# CLI Integration Tests
# =========================================================================

class TestCLI:
    def test_text_flag(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--text", "Deploy to Kubernetes"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert "KNOWLEDGE GAP ASSESSMENT REPORT" in proc.stdout

    def test_json_flag(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--json", "Set up OAuth flow"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert "domains_detected" in data
        assert "red_alerts" in data
        assert "proper_nouns" in data

    def test_lang_ja_flag(self):
        proc = subprocess.run(
            [
                sys.executable, str(SCRIPT_PATH),
                "--lang", "ja",
                "--text", "Reactコンポーネントを修正する",
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert "知識ギャップ評価レポート" in proc.stdout

    def test_no_args_shows_usage(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1
        assert "Usage" in proc.stdout or "使用方法" in proc.stdout

    def test_nonexistent_file(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "/nonexistent/file.txt"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1

    def test_stdin_with_json_flag(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--json"],
            input="Check the PostgreSQL migration",
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert "database" in data["domains_detected"]

    def test_stdin_with_text_flag(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--text"],
            input="Deploy to Kubernetes cluster",
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert "KNOWLEDGE GAP ASSESSMENT REPORT" in proc.stdout


# =========================================================================
# Constants Tests
# =========================================================================

class TestConstants:
    def test_current_year_is_dynamic(self):
        """CURRENT_YEAR should reflect the actual current year."""
        from datetime import datetime
        assert CURRENT_YEAR == datetime.now().year

    def test_confidence_thresholds_ordered(self):
        assert CONFIDENCE_THRESHOLD_HIGH < CONFIDENCE_THRESHOLD_MEDIUM

    def test_tech_name_min_length_positive(self):
        assert TECH_NAME_MIN_LENGTH > 0

    def test_stop_words_are_title_case(self):
        """All stop words should start with uppercase (title-cased at sentence start)."""
        for word in TECH_NAME_STOP_WORDS:
            assert word[0].isupper(), f"Stop word '{word}' does not start uppercase"

    def test_default_language_is_supported(self):
        from assess_knowledge_gaps import LOCALE_STRINGS
        assert DEFAULT_LANGUAGE in LOCALE_STRINGS
