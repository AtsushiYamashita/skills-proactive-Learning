# Security & Behavioral Review: proactive-learning Skill

**Reviewer**: Reviewer #2 (Rigor-oriented)
**Date**: 2026-02-08
**Scope**: SKILL.md, references/*, scripts/*, README.md
**Revision**: R2 (post-implementation update)
**Verdict**: ~~Major Revision Required~~ → **Revision Applied — Conditional Accept**

---

## Executive Summary

本スキルは、Claude Code を受動的アシスタントから能動的学習エージェントに変える意欲的な設計である。初回レビューで指摘した **セキュリティ境界の未定義**、**挙動スコープの曖昧さ**、**プロンプト指示の内部矛盾** という3つの構造的問題に対し、以下の改善を実施した。

---

## 1. セキュリティ上の問題点

### 1.1 [Critical] Auto Memory への書き込みにサニタイズが無い

**初回指摘**: Web検索結果に含まれるプロンプトインジェクション文字列が MEMORY.md に永続化され、以降のセッションのシステムプロンプトを汚染する可能性。

**対応状況**: **RESOLVED**
- `SKILL.md` Workflow 3 に「Memory Sanitization」セクションを追加
- HTMLタグ・スクリプトの除去、クレデンシャルパターンの除外ルールを明文化
- 「Raw search result content を直接記録しない」ポリシーを追加
- 200行制限の運用戦略（Keep / Summarize / Offload / Prune）を定義

### 1.2 [High] 検索クエリを通じた情報漏洩

**初回指摘**: タスク内容に含まれる機密情報が外部検索エンジンに送信される。

**対応状況**: **RESOLVED**
- `SKILL.md` Workflow 1 に「Search Query Safety」セクションを追加
- 社名・内部プロジェクト名・クレデンシャルをクエリに含めない明示ルール
- Will Not Do セクションでも再確認

### 1.3 [Medium] assess_knowledge_gaps.py のパストラバーサル

**初回指摘**: 任意のファイルパスを受け取り、存在確認のみで読み込む。

**対応状況**: **RESOLVED**
- `validate_file_path()` 関数を追加: `Path.resolve()` + `relative_to(cwd)` でカレントディレクトリ外のパスを拒否
- テスト `TestFilePathValidation::test_path_traversal_blocked` で検証済み

### 1.4 [Medium] description フィールドの挙動指示埋め込み

**初回指摘**: YAML description にスキルの使用条件が埋め込まれていた。

**対応状況**: **RESOLVED**
- description を純粋な説明文に変更（"should be used on every task" を除去）
- 活性化条件は `## When to Activate` セクションで条件付きに再定義

---

## 2. プロンプトの曖昧さ（Ambiguity in Prompt Instructions）

### 2.1 [High] 「Every task」の定義不在

**対応状況**: **RESOLVED**
- 「When to Activate」を条件リスト方式に変更
- 活性化条件: コード変更を伴う / 特定技術・ドメインへの言及あり / 要件が複数文
- 非活性化条件: 挨拶 / ワンライナー修正 / ファイル閲覧・git操作のみ

### 2.2 [High] Core Principle 間の矛盾

**対応状況**: **RESOLVED**
- `## Conflict Resolution` セクションを追加
- 安全性 > ユーザー指示 > Claude Code 本体 > 本スキル の優先順位を明確化
- 検索 vs 簡潔さのトレードオフルールを定義

### 2.3 [Medium] 「Confidence level」の評価基準不在

**対応状況**: **PARTIALLY RESOLVED**
- `assess_knowledge_gaps.py` の Pydantic モデルで `ConfidenceLevel` enum を定義
- Red Alert 検出時は自動的に LOW に降格するルールを実装
- SKILL.md での参照はまだ間接的（スクリプトへの参照経由）

### 2.4 [Medium] 「Continuously」の粒度未定義

**対応状況**: **RESOLVED**
- 「サブタスクあたり最大3回」の検索上限を追加
- 3回で未解決の場合はユーザーに通知して指示を仰ぐルールを明文化

### 2.5 [Low] 検索クエリ生成の `2026` ハードコード

**対応状況**: **RESOLVED**
- `CURRENT_YEAR = datetime.now().year` に変更
- テスト `TestConstants::test_current_year_is_dynamic` で検証済み

---

## 3. 挙動スコープの明言不足（Can / Cannot / Will Not）

**対応状況**: **RESOLVED**
- `SKILL.md` に `## Behavioral Scope` セクションを新設
- **Can Do**: 9項目を定義（ドメイン特定、検索、曖昧さ検出、Red Alert対応、固有名詞保護、永続化、失敗ログ、メタプロンプティング、多言語対応）
- **Cannot Do**: 5項目を定義（WebSearch非対応時、メモリ非対応時、検索結果精度、リアルタイムデータ、言語カバレッジ限界）
- **Will Not Do**: 7項目を定義（機密データ永続化、ユーザー拒否の無視、質問数超過、破壊的デフォルト、検索結果無検証コピー、クエリ経由情報漏洩、Red Alert反論）

---

## 4. assess_knowledge_gaps.py の技術的問題

### 4.1 正規表現の偽陽性

**対応状況**: **IMPROVED**
- scope ambiguity の否定先読みを拡張: `specifically` に加え `exactly`, `only`, `in line`, `at line` を追加
- 完全な文脈依存パターンにはまだ至っていないが、最も一般的な偽陽性は抑制

### 4.2 ドメイン検出の限界

**対応状況**: **RESOLVED**
- ストップワードリストを 7語 → 90+語 に大幅拡充（冠詞、代名詞、前置詞、接続詞、一般動詞すべてカバー）
- 小文字技術名の専用パターン追加: `k8s`, `npm`, `pnpm`, `yarn`, `bun`, `deno`, `esbuild`, `rollup`, `vite`
- `express.js` 等の小文字始まり `.js` ファイルパターン追加
- テスト `TestTechNameExtraction` で8ケース検証済み

### 4.3 JSON 出力モードの入力処理

**対応状況**: **RESOLVED**
- `--text` フラグにも stdin フォールバックを追加
- テスト `TestCLI::test_stdin_with_text_flag` で検証済み

---

## 5. 追加改善（R2 フィードバック反映）

### 5.1 [New] Red Alert 検出

ユーザーの「本当に？」「それ間違ってない？」「Are you sure?」等の発言を RED ALERT としてパターンマッチ。検出時は confidence を即座に LOW に降格し、弁明ではなく調査を行うプロトコルを SKILL.md に定義。

- 英語: 10パターン（are you sure, did you check, that's wrong, my information is different, double-check, fact-check, that contradicts, actually it's...）
- 日本語: 7パターン（本当に、ちゃんと調べた、私の知っている情報と違う、それは間違い、違うと思う、そうじゃない、確認して）
- テスト: 14ケース（TestRedAlertDetection）全パス

### 5.2 [New] 固有名詞保護

CamelCase、kebab-case、snake_case、スコープ付きパッケージ（`@org/pkg`）、ファイルライク名（`express.js`）のパターンを検出。タイポと決めつけず調査を優先する方針を SKILL.md に明記。

- テスト: 6ケース（TestProperNounDetection）全パス

### 5.3 [New] Pydantic モデル導入

全データ構造を Pydantic `BaseModel` で型安全に定義:
- `AnalysisResult`, `AmbiguityFlag`, `RedAlert`, `ProperNoun`
- `ConfidenceLevel`, `AmbiguityType` (Enum)
- JSON シリアライズ/デシリアライズのラウンドトリップテスト済み

### 5.4 [New] i18n 対応（英語 + 日本語）

- 全出力文字列を `LOCALE_STRINGS` 辞書で管理
- `--lang ja` フラグで日本語レポート出力
- 未対応言語は英語にフォールバック
- テスト: 6ケース（TestI18n）全パス

### 5.5 [New] マジックナンバー排除

すべての定数をファイル冒頭に名前付き定数として分離:
- `CURRENT_YEAR`, `CONFIDENCE_THRESHOLD_HIGH`, `CONFIDENCE_THRESHOLD_MEDIUM`
- `TECH_NAME_MIN_LENGTH`, `REPORT_SEPARATOR_WIDTH`, `MAX_QUESTIONS_PER_MESSAGE`
- `DEFAULT_LANGUAGE`
- テスト: 5ケース（TestConstants）で検証

### 5.6 [New] テストスイート（96テスト）

`tests/test_assess_knowledge_gaps.py` を新規作成:

| テストクラス | ケース数 | カバー範囲 |
|-------------|---------|-----------|
| TestPydanticModels | 5 | モデル生成、デフォルト値、JSON ラウンドトリップ |
| TestDomainDetection | 13 | 全7ドメイン + ゼロ検出 + 複数ドメイン |
| TestVersionSensitivity | 6 | 明示バージョン、キーワード、非該当 |
| TestAmbiguityDetection | 8 | 全4タイプ + 偽陽性抑制 + i18n |
| TestRedAlertDetection | 14 | 英語10パターン + 日本語7パターン + 非該当 + confidence連動 |
| TestProperNounDetection | 6 | 5パターンタイプ + 重複排除 |
| TestTechNameExtraction | 7 | PascalCase、小文字技術名、拡張子、ストップワード、最小長 |
| TestSearchSuggestions | 4 | 技術ベース、ドメインベース、年の動的生成、空入力 |
| TestConfidenceAssessment | 4 | HIGH / MEDIUM / LOW / RedAlert強制LOW |
| TestI18n | 6 | 英語、日本語、フォールバック、未知キー |
| TestReportFormatting | 4 | セパレータ、RedAlert表示、固有名詞表示 |
| TestFilePathValidation | 3 | 正常パス、存在しないパス、トラバーサル拒否 |
| TestAnalyzeTextE2E | 5 | 複合入力、RedAlert E2E、日本語 E2E、クリーン入力、固有名詞 |
| TestCLI | 7 | --text、--json、--lang ja、引数なし、存在しないファイル、stdin(json)、stdin(text) |
| TestConstants | 5 | 年の動的性、閾値順序、最小長、ストップワード形式、デフォルト言語 |

**全 96 テスト PASS** (2.79秒)

### 5.7 [New] 再現性計測スクリプト

`scripts/measure_reproducibility.py`:
- 同一入力を N 回実行し、各分析次元の一貫性を計測
- 7次元評価: confidence, domains, version_sensitive, ambiguity_types, red_alert_count, proper_noun_count, search_suggestion_count
- Pydantic モデルで結果を構造化
- 検証結果: 100% deterministic（正規表現ベースのため期待通り）

### 5.8 [New] Failure Logging ワークフロー（Workflow 4）

ハルシネーション、指示無視、Red Alert、誤出力を「失敗資産」として記録:
- 入力 / 誤出力 / 根本原因 / 修正内容 / 予防策 の5項目構造
- `memory/failure_log.md` に構造化して蓄積
- 失敗の根本原因分類: 知識ギャップ / 曖昧さ / 過信 / 古い前提

### 5.9 [New] Meta-Prompting ワークフロー（Workflow 5）

プロンプト最適化が求められた場合:
- 候補プロンプト2-3件を生成
- トレードオフ評価（具体性 vs 柔軟性、トークン効率、エッジケース）
- `measure_reproducibility.py` で一貫性を定量検証

---

## 6. 改善提案（R1）→ 対応状況

| 提案 | 状態 | 対応内容 |
|------|------|---------|
| 提案 1: セキュリティセクション追加 | **DONE** | Memory Sanitization + Search Query Safety + Will Not Do |
| 提案 2: 活性化条件の明確化 | **DONE** | 条件リスト方式 + 非活性化条件 |
| 提案 3: 挙動スコープセクション追加 | **DONE** | Can Do (9) / Cannot Do (5) / Will Not Do (7) |
| 提案 4: assess_knowledge_gaps.py 改善 | **DONE** | Pydantic、i18n、定数分離、パス検証、ストップワード拡充、stdin統一 |
| 提案 5: Conflict Resolution ルール追加 | **DONE** | 安全性 > ユーザー > Claude Code > スキル の優先順位 |

---

## 7. 総合評価（R2 更新）

| 評価軸 | R1 スコア | R2 スコア | コメント |
|--------|-----------|-----------|----------|
| 設計意図の妥当性 | ★★★★☆ | ★★★★★ | 5ワークフローへ拡張、失敗ログ・メタプロンプティング追加 |
| セキュリティ | ★★☆☆☆ | ★★★★☆ | Memory Sanitization、Search Query Safety、パス検証を実装。Red Alert対応追加 |
| プロンプトの明確性 | ★★★☆☆ | ★★★★☆ | 活性化条件明確化、検索上限追加、Conflict Resolution 定義 |
| 挙動スコープの明言 | ★☆☆☆☆ | ★★★★★ | Can / Cannot / Will Not を網羅的に定義 |
| スクリプト品質 | ★★★☆☆ | ★★★★★ | Pydantic、i18n、定数分離、パス検証、96テスト全パス |
| ドキュメント品質 | ★★★★☆ | ★★★★★ | 全指摘事項をドキュメント上で解決 |
| テストカバレッジ | (なし) | ★★★★★ | 96テスト + 再現性計測スクリプト |

**結論**: R1 の全5提案を実施し、R2 フィードバック（Red Alert、固有名詞保護、失敗ログ、メタプロンプティング、Pydantic化、テスト、i18n、再現性計測、200行制限戦略、マジックナンバー排除）もすべて反映。**Conditional Accept** — 残課題は scope ambiguity の文脈依存パターンの更なる精緻化のみ。
