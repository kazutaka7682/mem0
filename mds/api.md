# Mem0 API リファレンス

## 利用可能なエンドポイント

### メモリ管理
- `POST /memories` - 会話からメモリを保存
- `GET /memories` - user/agent/run IDでメモリを取得
- `GET /memories/{memory_id}` - 特定のメモリをIDで取得
- `PUT /memories/{memory_id}` - 既存のメモリを更新
- `DELETE /memories/{memory_id}` - 特定のメモリを削除
- `DELETE /memories` - 識別子の全メモリを削除

### 検索・クエリ
- `POST /search` - テキストクエリでメモリを検索（フィルター対応）

### 設定・履歴
- `POST /configure` - メモリ設定を更新
- `GET /memories/{memory_id}/history` - メモリ変更履歴を取得
- `POST /reset` - 全メモリをリセット

## メモリ保存プロセス

### 1. 入力処理 (`POST /memories`)

**必須：** 最低1つの識別子（`user_id`, `agent_id`, `run_id`）

**入力形式：**
```json
{
  "messages": [
    {"role": "user", "content": "私の名前はJohnでピザが好きです"},
    {"role": "assistant", "content": "Johnさん、はじめまして！"}
  ],
  "user_id": "user123",
  "metadata": {"任意": "カスタムデータ"}
}
```

### 2. LLM処理（2段階）

**段階1: 事実抽出**
- LLMが会話から構造化された事実を抽出
- 個人的嗜好、計画、職業詳細などを識別
- 戻り値: `{"facts": ["名前はJohn", "ピザが好き"]}`

**段階2: メモリ操作**
- LLMが事実を既存メモリと比較
- 操作を決定: ADD, UPDATE, DELETE, NONE
- 重複排除と統合を処理

### 3. データ保存場所

#### メインストレージ: PostgreSQL + pgvector

**テーブル: `memories`**
```sql
id      UUID (主キー)
vector  vector(3072)      -- Azure OpenAI text-embedding-3-large
payload JSONB             -- 全メタデータとコンテンツ
```

**Payload構造:**
```json
{
  "data": "抽出されたメモリテキスト",
  "hash": "重複排除用MD5ハッシュ", 
  "user_id": "セッション識別子",
  "agent_id": "オプションのエージェント識別子",
  "run_id": "オプションの実行識別子",
  "actor_id": "メッセージの話者名",
  "created_at": "2025-06-29T05:30:00-07:00",
  "updated_at": "更新時のタイムスタンプ"
}
```

#### サブストレージ: SQLite履歴

**目的：** 全メモリ変更を追跡（ADD/UPDATE/DELETE）

**場所：** `/app/history/history.db`

### 4. 現在のデータ

**保存状況：**
- PostgreSQLに2件のメモリを保存
- ユーザー: "test_user_123" 
- メモリ: "Name is John", "Loves pizza"
- ベクトル次元: 3072 (text-embedding-3-large)

**設定：**
- **LLM:** Azure OpenAI GPT-4o
- **Embedder:** Azure OpenAI text-embedding-3-large (3072次元)
- **Vector Store:** PostgreSQL + pgvector
- **履歴:** SQLiteデータベース

## 主要機能

1. **多階層メモリスコープ** - User、Agent、Runレベルでの分離
2. **セマンティック検索** - ベクトル類似度とメタデータフィルタリング  
3. **自動重複排除** - ハッシュベースの重複防止
4. **変更追跡** - メモリ操作の完全な監査証跡
5. **発話者認識** - 会話で誰が何を言ったかを追跡
6. **メタデータサポート** - メモリごとのカスタムJSONメタデータ