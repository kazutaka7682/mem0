# Mem0 クライアントアプリケーション集

mem0の長期記憶機能を活用したクライアントアプリケーションとデモンストレーション群です。

## 📁 ディレクトリ構成

```
mem0-client/
├── main-apps/          # 実用的なメインアプリケーション
├── demo-apps/          # デモ・検証用アプリケーション  
├── config/             # 設定ファイル・ドキュメント
└── README.md           # このファイル
```

## 🎯 メインアプリケーション (`main-apps/`)

### chat_app.py
**基本的な長期記憶チャットボット**
- Azure OpenAI との直接統合
- ユーザー別記憶管理
- シンプルな対話システム

```bash
cd main-apps
python chat_app.py
```

### rag_chat_app.py
**RAG + 長期記憶システム**
- 文書検索 (RAG) と長期記憶の融合
- ビジネスドキュメント検索
- 個人の関心事項の継続学習

```bash
cd main-apps
python rag_chat_app.py
```

## 🧪 デモアプリケーション (`demo-apps/`)

### memory_explorer.py
**記憶探索・分析ツール**
- 保存された記憶の一覧表示
- ユーザー横断検索
- 記憶統計と可視化

```bash
cd demo-apps  
python memory_explorer.py
```

### hierarchical_memory_example.py
**階層型記憶システムのデモ**
- 企業組織の記憶分類
- カテゴリ別記憶管理
- メタデータ活用例

```bash
cd demo-apps
python hierarchical_memory_example.py
```

### enterprise_chatbot_example.py
**企業向けチャットボットのプロトタイプ**
- 社員認証シミュレーション
- 部署・役職別パーソナライゼーション
- セキュリティ機能のデモ

```bash
cd demo-apps
python enterprise_chatbot_example.py
```

### direct_chat_app.py
**Memory クラス直接使用の検証**
- HTTP API vs 直接ライブラリ使用の比較
- 依存関係の問題検証
- パフォーマンス比較

```bash
cd demo-apps
python direct_chat_app.py
```

## ⚙️ 設定ファイル (`config/`)

### 環境変数ファイル
- `.env.chat` - chat_app用の設定
- `.env.rag` - RAGシステム用の設定

### ドキュメント
- `README_chat.md` - チャットアプリの詳細説明
- `README_rag.md` - RAGシステムの設定・使用方法

## 🚀 クイックスタート

### 1. 前提条件
```bash
# mem0サーバーの起動
cd ../
docker-compose up -d

# 依存関係のインストール
pip install requests openai python-dotenv
```

### 2. 環境変数の設定
```bash
# Azure OpenAI の設定
cp config/.env.chat.example config/.env.chat
cp config/.env.rag.example config/.env.rag

# APIキーを設定
nano config/.env.chat
nano config/.env.rag
```

### 3. アプリケーションの実行
```bash
# 基本チャット
cd main-apps && python chat_app.py

# RAG + 記憶システム  
cd main-apps && python rag_chat_app.py

# 記憶の確認
cd demo-apps && python memory_explorer.py
```

## 📊 用途別ガイド

### 💼 ビジネス評価・デモ
1. `enterprise_chatbot_example.py` - 企業価値の説明
2. `hierarchical_memory_example.py` - データ構造の紹介
3. `rag_chat_app.py` - 実用的なユースケース

### 🔧 技術検証・開発
1. `memory_explorer.py` - データの確認・デバッグ
2. `direct_chat_app.py` - アーキテクチャ選択の検証
3. `chat_app.py` - 基本機能の理解

### 🎓 学習・理解
1. `chat_app.py` - mem0の基本概念
2. `hierarchical_memory_example.py` - 応用的なデータ設計
3. `memory_explorer.py` - 内部動作の確認

## 🔗 関連ファイル

- `../mds/` - 企業導入提案・技術解説資料
- `../server/` - mem0サーバー本体
- `../docker-compose.yml` - 環境構築ファイル

## ⚠️ 注意事項

- **デモ用途**: これらは検証・デモ用アプリです
- **セキュリティ**: 本番環境では適切なセキュリティ対策が必要
- **APIキー**: 環境変数ファイルの管理に注意
- **依存関係**: 各アプリの requirements を確認してください

## 🆘 トラブルシューティング

### よくある問題

1. **mem0サーバーに接続できない**
   ```bash
   # サーバー状態確認
   docker-compose ps
   docker-compose logs mem0-server
   ```

2. **記憶が保存されない**
   ```bash
   # memory_explorer で確認
   cd demo-apps && python memory_explorer.py
   ```

3. **環境変数エラー**
   ```bash
   # 設定ファイル確認
   ls -la config/
   cat config/.env.chat
   ```

---

**mem0の長期記憶で、あなたのAIシステムを次のレベルへ！** 🧠✨