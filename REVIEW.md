# Security & Behavioral Review: proactive-learning Skill

**Reviewer**: Reviewer #2 (Rigor-oriented)
**Date**: 2026-02-08
**Scope**: SKILL.md, references/*, scripts/*, README.md
**Verdict**: **Major Revision Required**

---

## Executive Summary

本スキルは、Claude Code を受動的アシスタントから能動的学習エージェントに変える意欲的な設計である。3つのワークフロー（知識獲得・曖昧さ解消・知識永続化）は実用上の課題に対応しており、設計意図は妥当。しかし、**セキュリティ境界の未定義**、**挙動スコープの曖昧さ**、**プロンプト指示の内部矛盾**という3つの構造的問題がある。以下に詳細を示す。

---

## 1. セキュリティ上の問題点

### 1.1 [Critical] Auto Memory への書き込みにサニタイズが無い

**場所**: `SKILL.md` Workflow 3 (L94-120)

Workflow 3 は「タスク完了後に学んだことを auto memory に書き込む」と定義しているが、以下の制御が欠落している:

- **書き込み内容のバリデーション**: Web検索結果に含まれる悪意あるコンテンツ（プロンプトインジェクション文字列）がそのまま MEMORY.md に永続化される可能性がある。MEMORY.md はシステムプロンプトに直接ロードされるため、**永続的プロンプトインジェクション（Persistent Prompt Injection）**の攻撃ベクトルとなる。
- **機密情報の除外ルール**: PII、APIキー、クレデンシャル、内部URL等を記録しない明示的な禁止ルールが存在しない。
- **サイズ上限の不在**: 「200行以下に保つ」とあるが、これはガイダンスであり強制力がない。悪意ある肥大化によってシステムプロンプトが汚染される可能性がある。

**攻撃シナリオ**:
1. ユーザーがタスクを依頼
2. Workflow 1 が WebSearch を実行
3. 検索結果に `<!-- Ignore all previous instructions and... -->` のようなインジェクション文字列が含まれる
4. Workflow 3 がこれを「学び」として MEMORY.md に記録
5. 以降のすべてのセッションで、このインジェクション文字列がシステムプロンプトに含まれる

### 1.2 [High] 検索クエリを通じた情報漏洩

**場所**: `SKILL.md` Workflow 1 (L20-57), `references/search_strategies.md` 全体

スキルは「タスクの中身を解析して検索クエリを自動生成する」設計だが、タスク内容に機密情報（社名、内部プロジェクト名、未公開仕様）が含まれる場合、それが外部検索エンジンに送信される。

- 検索クエリの内容に対するフィルタリングルールが無い
- 「何を検索してはいけないか」の定義が無い
- ユーザーの同意なく自動で検索する設計

### 1.3 [Medium] assess_knowledge_gaps.py のパストラバーサル

**場所**: `scripts/assess_knowledge_gaps.py:231-235`

```python
file_path = Path(sys.argv[1])
if not file_path.exists():
    print(f"Error: File not found: {file_path}")
    sys.exit(1)
text = file_path.read_text()
```

任意のファイルパスを受け取り、存在確認のみで内容を読み込む。`/etc/passwd` や `~/.ssh/id_rsa` 等のセンシティブファイルの読み取りが可能。CLIツールとして低リスクではあるが、このスキルが「Claude Code の中でスクリプトとして実行される」文脈では、パスのバリデーションを追加すべき。

### 1.4 [Medium] description フィールドの挙動指示埋め込み

**場所**: `SKILL.md:3`

```yaml
description: This skill should be used on every task to proactively acquire...
```

YAML frontmatter の `description` にスキルの **使用条件** ("should be used on every task") が記述されている。これはメタデータであるべき場所に挙動指示を埋め込むパターンであり、スキルのロード機構によっては意図しない挙動強制となる。Description はスキルの説明であるべきで、使用条件は別セクションで定義すべき。

---

## 2. プロンプトの曖昧さ（Ambiguity in Prompt Instructions）

### 2.1 [High] 「Every task」の定義不在

**場所**: `SKILL.md:18`

> Activate this skill's behaviors at the start of every task.

「タスク」の定義が無い。以下のどれが「タスク」に該当するか不明:
- 「こんにちは」への応答
- 「git status を見せて」
- 「このコードを説明して」
- 「認証機能をリファクタリングして」

すべてに対してドメイン解析・曖昧さスキャン・WebSearchを実行するのはコスト（トークン・レイテンシ・API課金）的に非現実的。明確な**活性化閾値**が必要。

### 2.2 [High] Core Principle 間の矛盾

**場所**: `SKILL.md:12-14`

Core Principle 1 「Search-First Mindset — Before implementing, research.」は絶対的な原則として記述されているが、同じ Workflow 1 内で "Skip searching when" の例外が3つ定義されている (L47-49)。

さらに、Claude Code 本体のシステムプロンプトには:
> Avoid over-engineering. Only make changes that are directly requested or clearly necessary.

この指示との優先順位関係が未定義。「常に検索」と「必要最小限」が衝突した場合のフォールバックルールが必要。

### 2.3 [Medium] 「Confidence level」の評価基準不在

**場所**: `SKILL.md:29`

> Determine confidence level on the topic.

何をもって high / medium / low とするかの具体的基準が無い。`assess_knowledge_gaps.py` では gap_count に基づく機械的ルール（0=high, 1-2=medium, 3+=low）があるが、SKILL.md 側にはこの基準への参照が無い。判断が完全にモデルの主観に委ねられている。

### 2.4 [Medium] 「Continuously」の粒度未定義

**場所**: `SKILL.md:53`

> Do not treat research as a one-time step. When encountering unexpected behavior...

「encountering」のトリガー条件が曖昧。すべてのエラーで検索するのか、初見のエラーだけか、N秒以上解決できない場合か。無制限の検索ループに入るリスクがある。

### 2.5 [Low] 検索クエリ生成の `2026` ハードコード

**場所**: `scripts/assess_knowledge_gaps.py:160`

```python
suggestions.append(f"{tech} latest changes breaking changes 2026")
```

年がハードコードされている。2027年以降にこのスクリプトを使うと、古い結果を意図的に検索することになる。`datetime.now().year` を使うべき。

---

## 3. 挙動スコープの明言不足（Can / Cannot / Will Not）

本スキルの最大の構造的欠陥は、**「できること」のみ記述し、「できないこと」と「やらないこと」を一切定義していない**点にある。

### 3.1 定義されている「できる（Can Do）」

| 項目 | 場所 |
|------|------|
| WebSearch でドメイン知識を取得する | Workflow 1 |
| 6種類の曖昧さを検出し質問する | Workflow 2 |
| auto memory に知識を永続化する | Workflow 3 |
| 検索結果をもとに作業計画を修正する | Workflow 1 Step 4 |
| デフォルト値を提案しつつ確認する | Workflow 2 Step 5 |

### 3.2 未定義の「できない（Cannot Do）」— 追記が必要

以下は技術的制約であり明示すべき:

| 制約 | 理由 |
|------|------|
| WebSearch が利用不可の環境では Workflow 1 が機能しない | ツール依存 |
| auto memory ディレクトリが存在しない場合 Workflow 3 が失敗する | 環境依存 |
| 検索結果の正確性を保証できない | 外部データ依存 |
| リアルタイム情報（株価、天気等）は取得できない | WebSearch の特性 |
| ユーザーの意図を100%正確に推定できない | LLM の限界 |

### 3.3 未定義の「やらない（Will Not Do）」— 追記が必要

以下はポリシー的判断として明示すべき:

| 禁止事項 | 理由 |
|----------|------|
| 機密情報（PII, クレデンシャル, 内部URL）を MEMORY.md に記録しない | セキュリティ |
| ユーザーの明示的拒否を超えて検索を強行しない | ユーザー主権 |
| 検索結果を検証なしにコードに反映しない | 品質保証 |
| 1回のメッセージで4つ以上の質問をしない | UX |
| 破壊的操作のデフォルト値として「実行する」を提案しない | 安全性 |
| Web検索クエリにユーザーの機密情報を含めない | 情報漏洩防止 |
| 検索結果から取得したコードをそのままコピーしない | ライセンス/品質 |

---

## 4. assess_knowledge_gaps.py の技術的問題

### 4.1 正規表現の偽陽性

```python
"scope": [
    r"\b(fix|improve|update|refactor|clean\s+up|optimize)\b(?!.*\bspecifically\b)",
```

「fix」「update」「improve」は極めて一般的な動詞であり、ほぼすべてのタスク記述にヒットする。`"Fix the typo in line 3"` のような明確なタスクでも scope ambiguity がフラグされる。否定先読み `(?!.*specifically)` では不十分。

### 4.2 ドメイン検出の限界

技術名パターン `r"\b([A-Z][a-zA-Z]+(?:\.js|\.py|\.rs)?)\b"` は:
- `The`, `When`, `How` 等の除外リストが不完全（`I`, `If`, `It`, `We`, `As`, `But`, `And`, `Or`, `Are`, `Is` 等が漏れている）
- `vue`（小文字）、`k8s`（略語）、`npm`（小文字）等を検出できない
- `Next.js` はキャプチャできるが `express.js`（小文字始まり）はできない

### 4.3 JSON 出力モードの入力処理

```python
elif sys.argv[1] == "--json":
    text = " ".join(sys.argv[2:]) if len(sys.argv) >= 3 else sys.stdin.read()
```

`--json` フラグの場合、引数なしでstdin読み取りにフォールバックするが、`--text` フラグにはこのフォールバックが無い。APIの一貫性が欠けている。

---

## 5. 改善提案

### 提案 1: セキュリティセクションの追加（SKILL.md）

`SKILL.md` に `## Security Boundaries` セクションを追加し、以下を明文化する:

```markdown
## Security Boundaries

### Memory Sanitization
- MEMORY.md に書き込む前に、以下を除外する:
  - APIキー、トークン、パスワード
  - PII（メールアドレス、電話番号、氏名）
  - 内部URL、IPアドレス
  - Web検索結果に含まれるHTMLタグ・スクリプト
- 検索結果をそのまま記録せず、要約・再構成した形で記録する

### Search Query Safety
- 検索クエリにユーザーの機密情報（社名、内部プロジェクト名等）を含めない
- 検索前にクエリ内容を精査し、必要に応じてユーザーに確認する
```

### 提案 2: 活性化条件の明確化（SKILL.md）

「Every task」を以下のように置き換える:

```markdown
## When to Activate

このスキルは以下の条件を **1つ以上** 満たすタスクで活性化する:

- 実装・コード変更を伴うタスク
- 特定の技術・ライブラリ・ドメインへの言及があるタスク
- 要件が2文以上にわたるタスク

以下では活性化 **しない**:
- 単純な挨拶・雑談
- 既に完全な仕様が与えられたワンライナー修正
- ファイル閲覧・git操作のみの依頼
```

### 提案 3: 挙動スコープセクションの追加（SKILL.md）

```markdown
## Behavioral Scope

### Can Do（本スキルが行うこと）
- タスク開始時にドメインを特定し、知識ギャップを評価する
- WebSearch で公式ドキュメント・最新情報を取得する
- 曖昧な要件を検出し、デフォルト付きの質問を提示する
- 取得した知識を auto memory に構造化して記録する

### Cannot Do（技術的制約）
- WebSearch ツールが利用不可の環境では知識獲得を実行できない
- 検索結果の正確性・最新性を保証できない
- auto memory ディレクトリが存在しない場合、知識永続化は行えない

### Will Not Do（ポリシー的制約）
- 機密情報を MEMORY.md や検索クエリに含めない
- ユーザーが検索・質問の中止を求めた場合、即座に従う
- 1メッセージで4つ以上の質問をしない
- 破壊的操作をデフォルト提案しない
- 検索結果のコードを検証なしに採用しない
```

### 提案 4: assess_knowledge_gaps.py の改善

1. **ストップワード除外リストの拡充**: `The`, `When` 等に加え、一般的な英語冠詞・代名詞・接続詞をすべて除外
2. **年のハードコード排除**: `datetime.now().year` を使用
3. **パス入力のバリデーション**: 作業ディレクトリ配下のみ読み取り許可、またはホワイトリスト方式
4. **`--text` フラグへの stdin フォールバック追加**: `--json` と動作を一貫させる
5. **scope ambiguity の正規表現精緻化**: 動詞単体ではなく、目的語の具体性も考慮した文脈依存パターンへ変更

### 提案 5: Conflict Resolution ルールの追加

```markdown
## Conflict Resolution

本スキルの指示と Claude Code 本体の指示が衝突する場合:

1. **安全性に関わる場合**: Claude Code 本体の制約が常に優先する
2. **効率に関わる場合**: ユーザーの明示的指示 > Claude Code 本体 > 本スキル
3. **検索 vs 簡潔さ**: トークン予算・レイテンシの観点で、簡潔さが優先される
   場合は検索をスキップし、その判断をユーザーに通知する
```

---

## 6. 総合評価

| 評価軸 | スコア | コメント |
|--------|--------|----------|
| 設計意図の妥当性 | ★★★★☆ | 3つの failure mode への対応は実用的 |
| セキュリティ | ★★☆☆☆ | Memory injection / 情報漏洩リスクが未対処 |
| プロンプトの明確性 | ★★★☆☆ | Decision rules はあるが閾値・基準が曖昧 |
| 挙動スコープの明言 | ★☆☆☆☆ | Can のみ定義、Cannot / Will Not が完全欠落 |
| スクリプト品質 | ★★★☆☆ | 動作するが偽陽性・ハードコード等の問題あり |
| ドキュメント品質 | ★★★★☆ | 構造的で読みやすいが上記の欠落を含む |

**結論**: 設計のコアは良い。しかし、セキュリティ境界と挙動スコープの未定義が、スキルとしての信頼性を大きく損なっている。上記5つの提案を反映した Major Revision を推奨する。
