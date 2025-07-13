# SQLite to Azure SQL Server 移行ガイド

このドキュメントは、mem0の標準SQLiteストレージからAzure SQL Serverへの移行における実装の差分と設計判断について説明します。

## 概要

mem0は標準でSQLiteを使用して履歴データを管理していますが、エンタープライズ環境での使用を考慮し、Azure SQL Serverへの移行を実装しました。本ドキュメントでは、両実装の差分と移行時の考慮点を説明します。

## スキーマの比較

### SQLite版 (オリジナル)

```sql
CREATE TABLE IF NOT EXISTS history (
    id           TEXT PRIMARY KEY,
    memory_id    TEXT,
    old_memory   TEXT,
    new_memory   TEXT,
    event        TEXT,
    created_at   DATETIME,
    updated_at   DATETIME,
    is_deleted   INTEGER,
    actor_id     TEXT,
    role         TEXT
)
```

参照: `mem0/memory/storage.py:106-117`

### Azure SQL Server版

```sql
CREATE TABLE mem0_history (
    id           NVARCHAR(255) PRIMARY KEY,
    memory_id    NVARCHAR(255),
    old_memory   NVARCHAR(MAX),
    new_memory   NVARCHAR(MAX),
    event        NVARCHAR(50),
    created_at   DATETIME2,
    updated_at   DATETIME2,
    is_deleted   INT,
    actor_id     NVARCHAR(255),
    role         NVARCHAR(50)
)

-- パフォーマンス最適化のためのインデックス
CREATE INDEX IX_mem0_history_memory_id ON mem0_history(memory_id)
CREATE INDEX IX_mem0_history_created_at ON mem0_history(created_at)
```

参照: `azure_sql_storage.py:44-64`

## 主要な差分

### 1. データ型のマッピング

| SQLite | Azure SQL Server | 理由 |
|--------|------------------|------|
| TEXT | NVARCHAR(255) / NVARCHAR(MAX) | SQL Serverの標準的な文字列型。MAXは大きなテキスト用 |
| DATETIME | DATETIME2 | より高精度なタイムスタンプのサポート |
| INTEGER | INT | SQL Serverの標準的な整数型 |

### 2. テーブル名

- **SQLite**: `history`
- **Azure SQL**: `mem0_history`

**理由**: Azure SQL Serverは複数のアプリケーションで共有される可能性があるため、名前空間の衝突を避けるためにプレフィックスを追加。

### 3. インデックス

Azure SQL版では以下のインデックスを追加：
- `IX_mem0_history_memory_id`: 特定のメモリIDの履歴を高速検索
- `IX_mem0_history_created_at`: 時系列でのソートを高速化

**理由**: エンタープライズ環境では大量のデータが蓄積されることを想定し、クエリパフォーマンスを最適化。

### 4. API設計の差分

#### メソッド名
- **SQLite**: `add_history()`
- **Azure SQL**: `add()`

**理由**: カスタム実装として明確にするため、より簡潔な名前を採用。

#### パラメータ処理
```python
# SQLite版
def add_history(
    self,
    memory_id: str,
    old_memory: Optional[str],
    new_memory: Optional[str],
    event: str,
    *,  # キーワード引数のみ
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
    is_deleted: int = 0,
    actor_id: Optional[str] = None,
    role: Optional[str] = None,
) -> None:

# Azure SQL版
def add(
    self,
    memory_id: str,
    old_memory: Optional[str] = None,
    new_memory: Optional[str] = None,
    event: Optional[str] = None,
    actor_id: Optional[str] = None,
    role: Optional[str] = None,
) -> str:  # history_idを返す
```

**理由**: 
- タイムスタンプは内部で自動生成（`datetime.now()`）
- `is_deleted`は常に0で初期化
- 履歴IDを返すことで、追跡可能性を向上

### 5. 接続管理

- **SQLite**: 永続的な接続を保持
- **Azure SQL**: 各操作で新しい接続を作成

**理由**: Azure SQL Serverの接続プール機能を活用し、接続の信頼性を向上。

## 機能的な互換性

以下の点で両実装は機能的に互換性があります：

1. **データモデル**: 同じフィールドを保持
2. **基本操作**: 追加、取得、削除の操作が同等
3. **履歴追跡**: メモリの変更履歴を同じ形式で記録

## 移行時の考慮事項

1. **接続文字列**: Azure SQL Server用の接続情報が必要
2. **認証**: SQL認証またはAzure AD認証の設定
3. **ファイアウォール**: クライアントIPの許可設定
4. **データ移行**: 既存のSQLiteデータをAzure SQLに移行する場合は、別途ETLプロセスが必要

## パフォーマンスの最適化

Azure SQL版では以下の最適化を実装：

1. **インデックス**: 頻繁に検索されるカラムにインデックスを追加
2. **接続プーリング**: pyodbcの接続プール機能を活用
3. **バッチ処理**: 将来的な拡張として、バルクインサートの実装を検討

## まとめ

Azure SQL Server版は、mem0のSQLiteストレージと機能的に同等でありながら、エンタープライズ環境での使用に適した以下の改善を含んでいます：

- スケーラビリティの向上
- パフォーマンスの最適化
- Azure環境との統合
- 運用管理の容易性

両実装は同じデータモデルを使用しているため、アプリケーションレベルでの変更は最小限で済みます。