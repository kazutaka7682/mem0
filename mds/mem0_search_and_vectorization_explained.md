# Mem0 検索システムとベクトル化の詳細解説

## 🧠 mem0のデータ構造

### PostgreSQL + pgvectorのスキーマ
```sql
-- メインテーブル（記憶データ）
CREATE TABLE memories (
    id UUID PRIMARY KEY,                    -- 記憶の一意識別子
    vector vector(3072),                    -- 3072次元ベクトル（text-embedding-3-large）
    payload JSONB                           -- 柔軟なメタデータとコンテンツ
);

-- 高速検索用インデックス
CREATE INDEX memories_hnsw_idx ON memories 
USING hnsw (vector vector_cosine_ops);

-- メタデータ検索用インデックス
CREATE INDEX memories_user_idx ON memories ((payload->>'user_id'));
CREATE INDEX memories_category_idx ON memories ((payload->>'memory_category'));
```

### payloadの内部構造
```json
{
  "data": "実際の記憶内容テキスト",
  "hash": "MD5ハッシュ値",
  "created_at": "2024-06-29T10:30:00Z",
  "user_id": "emp_a1b2c3d4e5f67890",
  
  // カスタムメタデータ（自由定義可能）
  "memory_category": "basic_info",
  "memory_subcategory": "personal_profile", 
  "memory_importance": 4,
  "hierarchy": {
    "level_1": "basic_info",
    "level_2": "personal_profile",
    "path": "basic_info/personal_profile"
  },
  "business_context": {
    "department": "経理",
    "role": "課長",
    "access_level": 3
  },
  "tags": ["profile", "basic", "personal"],
  "confidence": 0.95
}
```

## 🔍 検索システムの詳細

### 1. ハイブリッド検索アーキテクチャ

mem0は**ベクトル検索**と**メタデータフィルタリング**を組み合わせたハイブリッド検索を実装しています：

```python
# 検索クエリの実行フロー
def search_memories(query: str, user_id: str, filters: dict):
    # 1. クエリをベクトル化
    query_embedding = embedding_model.embed(query)
    
    # 2. PostgreSQLでハイブリッド検索実行
    sql = """
    SELECT id, vector <=> %s::vector AS distance, payload
    FROM memories
    WHERE payload->>'user_id' = %s           -- ユーザーフィルタ
      AND payload->>'memory_category' = %s   -- カテゴリフィルタ
      AND payload->'tags' ? %s               -- タグフィルタ
    ORDER BY distance                        -- ベクトル類似度順
    LIMIT %s
    """
    
    return execute_query(sql, [query_embedding, user_id, category, tag, limit])
```

### 2. ベクトル化の対象と処理

#### A. 記憶保存時のベクトル化
```python
# main.py - Memory.add() メソッドより
def add_memory(messages, user_id, metadata):
    # 1. LLMによる事実抽出（infer=True時）
    if self.config.llm.enable_infer:
        facts = self.llm.extract_facts(messages)
        # 抽出された事実: "田中太郎は経理部の課長で会計が専門"
        vectorizable_content = facts
    else:
        # 元メッセージをそのまま使用
        vectorizable_content = messages[0]['content']
    
    # 2. ベクトル化実行
    embeddings = self.embedding_model.embed(
        text=vectorizable_content,
        doc_type="document"  # 文書として埋め込み
    )
    
    # 3. PostgreSQLに保存
    self.vector_store.add(
        vectors=[embeddings],
        payloads=[{
            "data": vectorizable_content,  # ベクトル化されたテキスト
            "hash": generate_hash(vectorizable_content),
            "user_id": user_id,
            **metadata  # カスタムメタデータ
        }]
    )
```

#### B. 検索時のベクトル化
```python
# main.py - Memory.search() メソッドより  
def search_memory(query, user_id, filters):
    # 1. 検索クエリをベクトル化
    query_embeddings = self.embedding_model.embed(
        text=query,
        doc_type="search"  # 検索クエリとして埋め込み
    )
    
    # 2. ベクトル類似度検索実行
    results = self.vector_store.search(
        query_vectors=query_embeddings,
        limit=limit,
        filters=filters  # メタデータフィルタ
    )
    
    return results
```

### 3. 重要な発見：何がベクトル化されるか

#### 🎯 ベクトル化される内容
1. **推論モード（デフォルト）**: LLMが抽出した**「事実（facts）」**
2. **非推論モード**: **元のメッセージ内容**

#### 具体例
```python
# 入力メッセージ
input_message = "私は田中太郎です。経理部で働いています。会計と税務が専門で、最近はAI導入に興味があります。"

# 推論モード（infer=True）でのベクトル化対象
extracted_facts = [
    "田中太郎は経理部で働いている",
    "田中太郎の専門は会計と税務",  
    "田中太郎はAI導入に興味がある"
]

# 非推論モード（infer=False）でのベクトル化対象
raw_content = "私は田中太郎です。経理部で働いています。会計と税務が専門で、最近はAI導入に興味があります。"
```

## 🏗️ 階層型記憶の実装戦略

### 1. メタデータによる階層構造

```python
# 階層型記憶の設計例
hierarchical_metadata = {
    # 第1レベル：主カテゴリ
    "memory_category": "business",
    
    # 第2レベル：サブカテゴリ  
    "memory_subcategory": "daily_procedures",
    
    # 階層パス（検索最適化用）
    "hierarchy_path": "business/daily_procedures",
    
    # 階層レベル（深度管理用）
    "hierarchy_level": 2,
    
    # 親子関係（参照用）
    "parent_category": "business",
    "child_categories": ["approvals", "forms", "deadlines"],
    
    # 分類タグ（多面的分類用）
    "classification_tags": {
        "domain": ["finance", "accounting"],
        "complexity": ["intermediate"],
        "frequency": ["daily"]
    }
}
```

### 2. 検索戦略の使い分け

#### A. 階層ドリルダウン検索
```python
# レベル1：カテゴリ検索
business_memories = search(filters={"memory_category": "business"})

# レベル2：サブカテゴリ検索  
procedure_memories = search(filters={
    "memory_category": "business",
    "memory_subcategory": "daily_procedures"
})

# レベル3：詳細フィルタ検索
approval_memories = search(filters={
    "hierarchy_path": "business/daily_procedures",
    "classification_tags.domain": "finance"
})
```

#### B. セマンティック検索
```python
# 自然言語での検索（ベクトル類似度重視）
semantic_results = search(
    query="経費申請の手順を教えて",
    filters={"memory_category": "business"}  # カテゴリで絞り込み
)
```

#### C. ハイブリッド検索
```python
# セマンティック + 階層フィルタの組み合わせ
hybrid_results = search(
    query="予算管理のベストプラクティス",
    filters={
        "hierarchy_path": "business/procedures",
        "memory_importance": [3, 4],  # 高重要度のみ
        "classification_tags.complexity": "advanced"
    }
)
```

## 🚀 最適化のポイント

### 1. インデックス戦略
```sql
-- ベクトル検索最適化
CREATE INDEX memories_vector_idx ON memories 
USING hnsw (vector vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- メタデータ検索最適化
CREATE INDEX memories_category_path_idx ON memories 
((payload->>'hierarchy_path'));

CREATE INDEX memories_composite_idx ON memories 
((payload->>'user_id'), (payload->>'memory_category'));

-- 複合インデックス（よく使用されるフィルタ組み合わせ）
CREATE INDEX memories_business_idx ON memories 
((payload->>'user_id'), (payload->>'memory_category'), (payload->>'memory_importance'));
```

### 2. パフォーマンス考慮事項

#### A. ベクトル次元数の選択
- **text-embedding-3-large**: 3072次元（高精度、やや重い）
- **text-embedding-3-small**: 1536次元（軽量、十分な精度）
- **text-embedding-ada-002**: 1536次元（コスト効率）

#### B. 検索パフォーマンス
```python
# 効率的な検索パターン
def optimized_search(query: str, user_id: str, category: str = None):
    filters = {"user_id": user_id}
    
    # カテゴリが指定されている場合は最初にフィルタ
    if category:
        filters["memory_category"] = category
    
    # 段階的検索：まずメタデータで絞り込み、次にベクトル検索
    return search(
        query=query,
        filters=filters,
        limit=20,  # 適切な制限値
        include_metadata=True
    )
```

### 3. メモリ使用量最適化
```python
# ベクトルの効率的な管理
class EfficientVectorManager:
    def __init__(self):
        # ベクトルキャッシュ（最近使用した記憶）
        self.vector_cache = LRUCache(maxsize=1000)
        
    def get_similar_memories(self, query_vector, user_id, limit=10):
        # キャッシュから検索
        cache_key = f"{user_id}_{hash(query_vector.tobytes())}"
        
        if cache_key in self.vector_cache:
            return self.vector_cache[cache_key]
        
        # データベース検索
        results = self.vector_store.search(
            query_vectors=query_vector,
            filters={"user_id": user_id},
            limit=limit
        )
        
        # 結果をキャッシュ
        self.vector_cache[cache_key] = results
        return results
```

## 📊 実装効果の測定

### 検索精度指標
```python
class SearchQualityMetrics:
    def calculate_recall_at_k(self, query, relevant_memories, k=10):
        """検索結果のRecall@K計算"""
        search_results = self.search(query, limit=k)
        retrieved_relevant = len(set(search_results) & set(relevant_memories))
        return retrieved_relevant / len(relevant_memories)
    
    def calculate_precision_at_k(self, query, relevant_memories, k=10):
        """検索結果のPrecision@K計算"""
        search_results = self.search(query, limit=k)
        retrieved_relevant = len(set(search_results) & set(relevant_memories))
        return retrieved_relevant / len(search_results)
```

---

## まとめ

**mem0の検索とベクトル化の特徴:**

1. **ベクトル化対象**: LLMが抽出した事実（推論モード）または元コンテンツ（非推論モード）
2. **検索方式**: ベクトル類似度検索 + メタデータフィルタリングのハイブリッド
3. **階層管理**: 自由定義のメタデータによる柔軟な階層構造
4. **高速検索**: pgvectorのHNSWインデックスによる最適化

この仕組みにより、企業での複雑な記憶分類と高速検索を両立できます。