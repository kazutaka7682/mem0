#!/usr/bin/env python3
"""
Direct Mem0 Chat App
Memoryクラスを直接使用した対話アプリ
HTTP API経由ではなく、mem0ライブラリを直接活用

使用方法:
python direct_chat_app.py
"""

import sys
import os
from datetime import datetime

# mem0ライブラリを直接インポート（バージョンチェックを回避）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 環境変数読み込み
from dotenv import load_dotenv
load_dotenv(".env.rag")
load_dotenv(".env")

# mem0クラスを直接インポート（依存関係を回避）
try:
    from mem0.memory.main import Memory
    from mem0.configs.base import MemoryConfig
    DIRECT_IMPORT_SUCCESS = True
    print("✅ Direct import成功: Memoryクラスを直接使用できます")
except Exception as e:
    print(f"❌ Direct import失敗: {e}")
    print("📝 結論: HTTP API経由の方が安全で、依存関係の問題を回避できます")
    DIRECT_IMPORT_SUCCESS = False

class DirectMem0ChatBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        
        # Mem0設定（サーバーと同じ設定）
        config = MemoryConfig(
            vector_store={
                "provider": "pgvector",
                "config": {
                    "host": "localhost",
                    "port": 5432,
                    "dbname": "postgres",
                    "user": "postgres", 
                    "password": "postgres",
                    "collection_name": "memories_direct",
                    "embedding_model_dims": 3072,
                },
            },
            llm={
                "provider": "azure_openai",
                "config": {
                    "model": "gpt-4o",
                    "temperature": 0.2,
                    "azure_kwargs": {
                        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                        "azure_deployment": "gpt-4o",
                        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                        "api_version": "2024-12-01-preview",
                    },
                },
            },
            embedder={
                "provider": "azure_openai",
                "config": {
                    "model": "text-embedding-3-large",
                    "embedding_dims": 3072,
                    "azure_kwargs": {
                        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                        "azure_deployment": "text-embedding-3-large",
                        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                        "api_version": "2024-12-01-preview",
                    },
                },
            },
        )
        
        # Memory直接インスタンス化
        try:
            self.memory = Memory(config)
            print("✅ Memory直接インスタンス化成功!")
        except Exception as e:
            print(f"❌ Memory初期化エラー: {e}")
            raise
    
    def save_and_get_response(self, user_input: str):
        """ユーザー入力を処理し、記憶保存と応答生成を行う"""
        print(f"\n👤 ユーザー: {user_input}")
        
        # 1. 関連記憶検索
        print("🧠 関連記憶を検索中...")
        related_memories = self.search_memories(user_input)
        
        # 2. 応答生成（記憶ベース）
        if related_memories:
            print(f"🔍 {len(related_memories)}件の関連記憶を発見")
            assistant_response = self.generate_memory_based_response(user_input, related_memories)
        else:
            assistant_response = f"承知いたしました。「{user_input}」について記録し、今後のサポートに活用します。"
        
        print(f"🤖 アシスタント: {assistant_response}")
        
        # 3. 新しい会話を記憶に追加
        print("💾 記憶保存中...")
        self.add_memory(user_input, assistant_response)
        
        return assistant_response
    
    def add_memory(self, user_message: str, assistant_message: str):
        """記憶を追加（mem0の内部ロジックを直接活用）"""
        try:
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message}
            ]
            
            # Memory.add()を直接呼び出し
            result = self.memory.add(
                messages=messages,
                user_id=self.user_id,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "app": "direct_chat_bot"
                }
            )
            
            print(f"📝 記憶抽出結果: {len(result.get('results', []))}件")
            for item in result.get('results', []):
                event = item.get('event', 'UNKNOWN')
                memory = item.get('memory', '')
                print(f"   {event}: {memory}")
                
        except Exception as e:
            print(f"❌ 記憶保存エラー: {e}")
    
    def search_memories(self, query: str, limit: int = 5):
        """記憶検索（mem0の内部ロジックを直接活用）"""
        try:
            # Memory.search()を直接呼び出し
            results = self.memory.search(
                query=query,
                user_id=self.user_id,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            print(f"❌ 記憶検索エラー: {e}")
            return []
    
    def generate_memory_based_response(self, query: str, memories: list):
        """記憶を活用した応答生成"""
        if not memories:
            return "申し訳ありませんが、関連する記憶が見つかりませんでした。"
        
        memory_context = "\n".join([f"- {mem.get('memory', '')}" for mem in memories])
        
        response = f"""
過去の記憶を参考にお答えします：

{memory_context}

{query}について、これらの記憶から判断すると、継続してサポートさせていただきます。
"""
        return response.strip()
    
    def get_all_memories(self):
        """全記憶を取得"""
        try:
            # Memory.get_all()を直接呼び出し
            memories = self.memory.get_all(user_id=self.user_id)
            
            if memories:
                print(f"\n📚 保存済み記憶 ({len(memories)}件):")
                for i, memory in enumerate(memories, 1):
                    created_at = memory.get('created_at', '')
                    print(f"   {i}. {memory.get('memory', '')} ({created_at})")
            else:
                print("\n📚 保存済み記憶: なし")
                
        except Exception as e:
            print(f"❌ 記憶取得エラー: {e}")

def test_direct_memory():
    """直接Memory使用のテスト"""
    print("🧪 Direct Memory使用テスト")
    print("=" * 50)
    
    try:
        chatbot = DirectMem0ChatBot("direct_test_user")
        
        # テスト会話
        test_queries = [
            "私は経理部の田中と申します。代理店契約について学びたいです。",
            "経費の分類について教えてください",
            "私の専門分野は何でしたっけ？"
        ]
        
        for query in test_queries:
            print("\n" + "="*50)
            chatbot.save_and_get_response(query)
        
        # 記憶確認
        print("\n" + "="*50)
        chatbot.get_all_memories()
        
        print("\n✅ Direct Memory使用テスト完了!")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")

def main():
    """メイン実行関数"""
    print("🎯 Direct Mem0 対話システム")
    print("=" * 50)
    print("Memory APIを直接使用（HTTP経由なし）")
    print("=" * 50)
    
    if not DIRECT_IMPORT_SUCCESS:
        print("\n【結論】")
        print("✅ HTTPエンドポイント経由: 安全で依存関係の問題なし")
        print("❌ Direct Memory使用: 依存関係エラーが発生")
        print("\n💡 推奨: 現在のHTTP API経由の実装を継続使用")
        print("   - 環境の分離ができている")
        print("   - 依存関係の問題を回避")
        print("   - mem0サーバーの設定を活用")
        return
    
    # テスト実行の選択
    print("1. 自動テスト実行")
    print("2. インタラクティブモード")
    choice = input("選択 (1-2): ").strip()
    
    if choice == "1":
        test_direct_memory()
    elif choice == "2":
        # インタラクティブモード
        user_id = input("ユーザーID: ").strip() or "interactive_user"
        chatbot = DirectMem0ChatBot(user_id)
        
        print("\n特別コマンド:")
        print("  /memories - 保存済み記憶を表示") 
        print("  /quit - 終了")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\n💬 質問: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input == "/quit":
                    print("👋 終了します")
                    break
                elif user_input == "/memories":
                    chatbot.get_all_memories()
                    continue
                
                chatbot.save_and_get_response(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 終了します")
                break
            except Exception as e:
                print(f"❌ エラー: {e}")
    else:
        print("無効な選択です")

if __name__ == "__main__":
    main()