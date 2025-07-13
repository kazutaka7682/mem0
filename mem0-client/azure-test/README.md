# Azure Test Environment for Mem0

このディレクトリには、mem0ライブラリのAzure環境での動作検証用スクリプトとドキュメントが含まれています。

## 📋 テストスクリプト一覧

### 1. `mem0_azure_test.py` - 基本Azure統合テスト
- **目的**: Azure AI Search + SQLite構成でのmem0動作確認
- **ベクターDB**: Azure AI Search
- **履歴管理**: SQLite（mem0標準）
- **特徴**: 最もシンプルなAzure統合パターン
- **用途**: Azure AI Searchの基本動作確認、開発・テスト環境

### 2. `mem0_azure_full_test.py` - 完全Azure統合テスト
- **目的**: Azure AI Search + Azure SQL Server構成での完全検証
- **ベクターDB**: Azure AI Search
- **履歴管理**: Azure SQL Server（カスタム実装）
- **特徴**: エンタープライズ向けフル機能テスト
- **用途**: 本番環境想定での動作確認

#### 🎯 Full Test起動モード詳細

##### モード1: 完全Azure統合テスト
- **機能**: 自動化されたテストシーケンス
- **処理内容**:
  - テストデータでメモリ追加・SQL履歴記録
  - メモリ検索機能の検証
  - Azure SQL履歴確認・統計取得
  - 自動クリーンアップ実行
- **用途**: CI/CD、定期的な動作確認

##### モード2: 対話形式チャット
- **機能**: インタラクティブなチャット環境
- **処理内容**:
  - リアルタイム会話とメモリ蓄積
  - 関連記憶を活用した応答生成
  - 手動でのSQL履歴・統計確認
- **特殊コマンド**:
  - `/search <クエリ>` - メモリ検索
  - `/history` - SQL履歴表示
  - `/stats` - SQL統計表示
  - `/quit` - 終了（自動クリーンアップ）
- **用途**: 機能デモ、インタラクティブな動作確認

### 3. `mem0_azure_hybrid_test.py` - ハイブリッド構成テスト
- **目的**: Azure SQL Serverが利用できない場合の柔軟な対応
- **ベクターDB**: Azure AI Search
- **履歴管理**: Azure SQL Server（利用可能時）→ SQLite（フォールバック）
- **特徴**: 環境に応じた自動切り替え
- **用途**: 開発環境、Azure SQL接続が不安定な環境

### 4. `azure_sql_storage.py` - カスタムストレージ実装
- **目的**: Azure SQL Server用の履歴管理クラス
- **機能**: mem0のSQLiteManagerをAzure SQL Server対応に拡張
- **実装内容**:
  - `mem0_history`テーブルの作成・管理
  - 履歴の追加・取得・削除操作
  - Azure SQL Server固有の最適化
- **用途**: 他のテストスクリプトから利用される共通ライブラリ

## 📚 ドキュメント（docsディレクトリ）

### 1. `sqlite_to_azure_sql_migration_guide.md`
- **内容**: SQLiteからAzure SQL Serverへの移行ガイド
- **説明項目**:
  - スキーマ・データ型の比較分析
  - 設計判断の理由と根拠
  - API設計の差分
  - 移行時の考慮事項とパフォーマンス最適化
- **対象読者**: 開発者、インフラエンジニア

### 2. `mem0_library_vs_api_comparison.md`
- **内容**: mem0ライブラリ直接利用 vs APIサーバー経由の比較
- **説明項目**:
  - 実装方法の違い
  - アーキテクチャパターンの比較
  - それぞれのメリット・デメリット
  - 使い分けの指針と実装例
- **対象読者**: アーキテクト、開発チームリーダー

### 3. `mem0_microservice_architecture_analysis.md`
- **内容**: mem0マイクロサービス化の詳細分析
- **説明項目**:
  - server/main.pyの実装事実
  - マイクロサービス化のメリット・デメリット
  - 適用判断のガイドライン
  - Azure環境での実装考慮事項
- **対象読者**: システムアーキテクト、DevOpsエンジニア

## 📦 依存関係スナップショット

### `requirements.txt` - 動作確認済み依存関係
**取得日時**: 2024年7月13日  
**動作確認**: `mem0_azure_full_test.py`完全動作時点  
**取得意図**: 
- Azure環境での完全動作が確認されたライブラリバージョンの固定
- 再現可能な環境構築のためのバージョン管理
- トラブルシューティング時の基準バージョンとして利用
- CI/CD環境での一貫性保証

**重要な依存関係**:
- `mem0ai` - mem0コアライブラリ
- `openai` - Azure OpenAI連携
- `azure-search-documents` - Azure AI Search連携
- `pyodbc` - Azure SQL Server接続
- `python-dotenv` - 環境変数管理

## 🔧 環境設定

### 必要な環境変数（`.env.example`参照）

```bash
# Azure AI Search設定
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_API_KEY=your-search-api-key
AZURE_SEARCH_INDEX_NAME=mem0-test

# Azure OpenAI設定
AZURE_OPENAI_API_KEY=your-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

# Azure SQL Server設定（完全版・ハイブリッド版で必要）
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database
AZURE_SQL_USERNAME=your-username
AZURE_SQL_PASSWORD=your-password

# 埋め込みモデル設定
EMBEDDING_DIMENSIONS=1536
```

## 🚀 実行手順

### 1. 環境準備
```bash
# 仮想環境作成（推奨）
python -m venv venv-azure
source venv-azure/bin/activate  # Linux/Mac

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .envファイルを編集して実際の値を設定
```

### 2. テスト実行
```bash
# 基本テスト
python mem0_azure_test.py

# 完全統合テスト
python mem0_azure_full_test.py

# ハイブリッドテスト
python mem0_azure_hybrid_test.py
```

## ⚠️ 注意事項

### セキュリティ
- `.env`ファイルは絶対にコミットしない
- APIキーとパスワードの適切な管理
- Azure SQL Serverのファイアウォール設定

### パフォーマンス
- Azure AI Searchのインデックス作成には時間がかかる場合がある
- 大量データでのテスト時はクォータ制限に注意
- Azure SQL ServerとAzure AI Searchのリージョン配置を考慮

### トラブルシューティング
- 接続エラー時はファイアウォール設定を確認
- APIキーとエンドポイントの正確性を確認
- エラーログは詳細に出力されるため、メッセージを参考に対処

## 🔄 開発フロー

1. **基本テスト**で Azure AI Search連携を確認
2. **ハイブリッドテスト**で柔軟性を検証
3. **完全統合テスト**で本番環境想定の動作確認
4. ドキュメントを参照して設計判断を検討

このテスト環境により、Azure環境でのmem0の動作を包括的に検証できます。