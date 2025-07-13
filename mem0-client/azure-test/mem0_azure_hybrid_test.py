#!/usr/bin/env python3
"""
Mem0 + Azureハイブリッド検証スクリプト
Azure SQL Serverが利用できない場合でも動作する柔軟なバージョン

動作モード:
1. フルAzure: Azure AI Search + Azure SQL Server
2. ハイブリッド: Azure AI Search + SQLite（ローカル）

使用方法:
cd azure-test
python mem0_azure_hybrid_test.py
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

try:
    from mem0 import Memory
    from openai import AzureOpenAI
    import pyodbc
except ImportError as e:
    print(f"❌ 必要なライブラリがインストールされていません: {e}")
    print("以下のコマンドでインストールしてください:")
    print("pip install mem0ai openai azure-search-documents pyodbc")
    sys.exit(1)


class HybridAzureMem0ChatBot:
    def __init__(self, user_id: str, use_azure_sql: bool = True):
        self.user_id = user_id
        self.conversation_history = []
        self.use_azure_sql = use_azure_sql
        self.sql_storage = None
        
        # Azure構成の取得
        self._validate_azure_config()
        
        # Azure SQL初期化（オプション）
        if self.use_azure_sql:
            try:
                self._init_azure_sql()
            except Exception as e:
                print(f"⚠️  Azure SQL Server接続失敗。ローカルSQLiteで継続します: {e}")
                self.use_azure_sql = False
        
        self._init_mem0()
        self._init_openai()
        
    def _validate_azure_config(self):
        """Azure設定の検証（SQL Serverはオプション）"""
        required_vars = [
            'AZURE_SEARCH_ENDPOINT',
            'AZURE_SEARCH_API_KEY',
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_ENDPOINT'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"必須環境変数が設定されていません: {', '.join(missing_vars)}")
        
        # SQL Server設定確認（オプション）
        sql_vars = ['AZURE_SQL_SERVER', 'AZURE_SQL_DATABASE', 'AZURE_SQL_USERNAME', 'AZURE_SQL_PASSWORD']
        missing_sql = [var for var in sql_vars if not os.getenv(var)]
        if missing_sql and self.use_azure_sql:
            print(f"⚠️  Azure SQL Server設定が不完全です: {', '.join(missing_sql)}")
            print("   ローカルSQLiteモードで実行します")
            self.use_azure_sql = False
    
    def _init_azure_sql(self):
        """Azure SQL Server初期化"""
        from azure_sql_storage import AzureSQLManager
        
        print("🔧 Azure SQL Server初期化中...")
        
        server = os.getenv('AZURE_SQL_SERVER')
        database = os.getenv('AZURE_SQL_DATABASE')
        username = os.getenv('AZURE_SQL_USERNAME')
        password = os.getenv('AZURE_SQL_PASSWORD')
        
        if not server.endswith('.database.windows.net'):
            server = f'{server}.database.windows.net'
        
        connection_string = (
            f'DRIVER={{ODBC Driver 18 for SQL Server}};'
            f'SERVER=tcp:{server},1433;'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            f'Encrypt=yes;'
            f'TrustServerCertificate=no;'
            f'Connection Timeout=30;'
        )
        
        # 接続テスト
        conn = pyodbc.connect(connection_string)
        conn.close()
        
        # カスタム履歴管理インスタンス作成
        self.sql_storage = AzureSQLManager(connection_string)
        
        print(f"✅ Azure SQL Server初期化成功！")
        print(f"   - サーバー: {server}")
        print(f"   - データベース: {database}")
    
    def _init_mem0(self):
        """Mem0初期化（Azure構成）"""
        print("🔧 Mem0をAzure構成で初期化中...")
        
        # サービス名を抽出
        endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        service_name = None
        if endpoint:
            import re
            match = re.search(r'https://([^.]+)\.search\.windows\.net', endpoint)
            if match:
                service_name = match.group(1)
        
        if not service_name:
            raise ValueError("AZURE_SEARCH_ENDPOINTからサービス名を抽出できません")
        
        # Mem0設定
        config = {
            "vector_store": {
                "provider": "azure_ai_search",
                "config": {
                    "service_name": service_name,
                    "api_key": os.getenv('AZURE_SEARCH_API_KEY'),
                    "collection_name": os.getenv('AZURE_SEARCH_INDEX_NAME', 'mem0-test'),
                    "embedding_model_dims": int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))
                }
            },
            "llm": {
                "provider": "azure_openai",
                "config": {
                    "model": os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o'),
                    "azure_kwargs": {
                        "api_key": os.getenv('AZURE_OPENAI_API_KEY'),
                        "azure_deployment": os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o'),
                        "azure_endpoint": os.getenv('AZURE_OPENAI_ENDPOINT'),
                        "api_version": "2024-12-01-preview"
                    }
                }
            },
            "embedder": {
                "provider": "azure_openai",
                "config": {
                    "model": "text-embedding-3-small",
                    "azure_kwargs": {
                        "api_key": os.getenv('AZURE_OPENAI_API_KEY'),
                        "azure_deployment": os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small'),
                        "azure_endpoint": os.getenv('AZURE_OPENAI_ENDPOINT'),
                        "api_version": "2024-12-01-preview"
                    }
                }
            }
        }
        
        try:
            self.memory = Memory.from_config(config)
            print(f"✅ Mem0初期化成功！")
            print(f"   - ベクトルDB: Azure AI Search ({service_name})")
            print(f"   - 履歴DB: {'Azure SQL Server' if self.use_azure_sql else 'SQLite (ローカル)'}")
            print(f"   - インデックス: {config['vector_store']['config']['collection_name']}")
        except Exception as e:
            print(f"❌ Mem0初期化失敗: {e}")
            raise
    
    def _init_openai(self):
        """Azure OpenAI初期化"""
        try:
            self.client = AzureOpenAI(
                api_key=os.getenv('AZURE_OPENAI_API_KEY'),
                azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
                api_version="2024-12-01-preview"
            )
            print("✅ Azure OpenAI初期化成功！")
        except Exception as e:
            print(f"❌ Azure OpenAI初期化失敗: {e}")
            raise
    
    def add_memory(self, user_message: str, assistant_message: str):
        """メモリ追加（SQL履歴はオプション）"""
        try:
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message}
            ]
            
            # mem0でメモリ追加
            result = self.memory.add(
                messages=messages,
                user_id=self.user_id,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "app": "azure_hybrid_test"
                }
            )
            
            # Azure SQLに履歴記録（利用可能な場合）
            if self.use_azure_sql and self.sql_storage:
                for memory_data in result:
                    if isinstance(memory_data, dict) and 'id' in memory_data:
                        memory_id = memory_data['id']
                        memory_text = memory_data.get('memory', '')
                        event = memory_data.get('event', 'ADD')
                        
                        self.sql_storage.add(
                            memory_id=memory_id,
                            new_memory=memory_text,
                            event=event,
                            actor_id=self.user_id,
                            role='user'
                        )
            
            if result:
                print(f"💾 メモリ保存: {len(result)}件の記憶を追加")
                for memory in result:
                    if isinstance(memory, dict):
                        print(f"   📝 {memory.get('memory', memory)}")
                    else:
                        print(f"   📝 {memory}")
            else:
                print("💾 メモリ保存: 新しい記憶なし（既存と重複）")
                
            return result
            
        except Exception as e:
            print(f"❌ メモリ追加エラー: {e}")
            return []
    
    def search_memory(self, query: str, limit: int = 5):
        """関連メモリを検索"""
        try:
            results = self.memory.search(
                query=query,
                user_id=self.user_id,
                limit=limit
            )
            
            if results:
                print(f"🔍 関連記憶: {len(results)}件発見")
                for i, result in enumerate(results, 1):
                    memory_text = result.get('memory', str(result))
                    score = result.get('score', 'N/A')
                    print(f"   {i}. {memory_text}")
                    if score != 'N/A':
                        print(f"      関連度: {score:.3f}")
            else:
                print("🔍 関連記憶: 見つかりませんでした")
                
            return results
            
        except Exception as e:
            print(f"❌ メモリ検索エラー: {e}")
            return []
    
    def get_all_memories(self):
        """全メモリを取得"""
        try:
            all_memories = self.memory.get_all(user_id=self.user_id)
            
            if all_memories:
                print(f"📚 保存済みメモリ: {len(all_memories)}件")
                for i, memory in enumerate(all_memories, 1):
                    if isinstance(memory, dict):
                        memory_text = memory.get('memory', str(memory))
                        memory_id = memory.get('id', 'N/A')
                        created_at = memory.get('created_at', 'N/A')
                    else:
                        memory_text = str(memory)
                        memory_id = 'N/A'
                        created_at = 'N/A'
                    
                    print(f"   {i}. {memory_text}")
                    print(f"      ID: {memory_id} | 作成: {created_at}")
            else:
                print("📚 保存済みメモリ: なし")
                
            return all_memories
            
        except Exception as e:
            print(f"❌ メモリ取得エラー: {e}")
            return []
    
    def generate_response(self, user_input: str):
        """LLMで応答生成（記憶を活用）"""
        # 関連記憶を検索
        related_memories = self.search_memory(user_input)
        
        # システムプロンプト
        system_prompt = """あなたは親しみやすいAIアシスタントです。
ユーザーとの過去の会話記憶を活用して、パーソナライズされた応答をしてください。

応答ガイドライン:
- 過去の記憶を自然に会話に織り込む
- ユーザーの好みや状況を考慮する
- 親しみやすく人間らしい口調で応答する
- 記憶がない場合は素直に認めて新しい情報を求める"""

        # 記憶を含むコンテキスト
        context = ""
        if related_memories:
            context = "\n【関連する記憶】\n"
            for memory in related_memories:
                if isinstance(memory, dict):
                    memory_text = memory.get('memory', str(memory))
                else:
                    memory_text = str(memory)
                context += f"- {memory_text}\n"
            context += "\n"
        
        # メッセージ構築
        messages = [
            {"role": "system", "content": system_prompt + context}
        ]
        
        # 最近の会話履歴を追加（最大5ターン）
        recent_history = self.conversation_history[-10:]
        messages.extend(recent_history)
        
        # 現在のユーザー入力
        messages.append({"role": "user", "content": user_input})
        
        try:
            response = self.client.chat.completions.create(
                model=os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o'),
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"申し訳ありません。応答生成中にエラーが発生しました: {e}"
    
    def chat(self, user_input: str):
        """1回の対話処理"""
        print(f"\n👤 ユーザー: {user_input}")
        
        # LLMで応答生成
        assistant_response = self.generate_response(user_input)
        print(f"🤖 アシスタント: {assistant_response}")
        
        # 会話履歴に追加
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        # メモリに保存
        self.add_memory(user_input, assistant_response)
        
        return assistant_response
    
    def cleanup_all_memories(self):
        """全メモリを削除"""
        try:
            all_memories = self.get_all_memories()
            deleted_count = 0
            
            for memory in all_memories:
                try:
                    if isinstance(memory, dict) and 'id' in memory:
                        memory_id = memory['id']
                        self.memory.delete(memory_id=memory_id)
                        deleted_count += 1
                        print(f"   🗑️  メモリ削除: {memory_id[:8]}...")
                except Exception as e:
                    print(f"   ❌ 削除エラー: {e}")
            
            print(f"   ✅ {deleted_count}件のメモリを削除しました")
            return deleted_count
            
        except Exception as e:
            print(f"❌ クリーンアップエラー: {e}")
            return 0


def test_hybrid_mode():
    """ハイブリッドモードのテスト"""
    print("\n" + "="*60)
    print("🧪 ハイブリッドモードテスト")
    print("="*60)
    
    test_user = f"hybrid_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Azure SQL接続を試みる
    print("\n--- Azure SQL接続テスト ---")
    chatbot = HybridAzureMem0ChatBot(test_user, use_azure_sql=True)
    
    # テストデータ
    test_conversations = [
        ("私の名前は山田太郎です。", "山田太郎さん、よろしくお願いします！"),
        ("趣味は写真撮影です。", "写真撮影が趣味なんですね！素敵です！")
    ]
    
    # メモリ追加テスト
    print("\n📝 メモリ追加テスト:")
    for user_msg, assistant_msg in test_conversations:
        result = chatbot.add_memory(user_msg, assistant_msg)
        print(f"   結果: {len(result) if result else 0}件追加")
    
    # メモリ検索テスト
    print("\n🔍 メモリ検索テスト:")
    chatbot.search_memory("趣味", limit=3)
    
    # クリーンアップ
    print("\n🗑️  テストデータのクリーンアップ:")
    chatbot.cleanup_all_memories()
    
    print(f"\n✅ テスト完了！")
    print(f"   動作モード: {'フルAzure' if chatbot.use_azure_sql else 'ハイブリッド（SQLite）'}")
    
    return True


def interactive_chat():
    """対話形式のチャット"""
    print("\n" + "="*60)
    print("💬 Azureハイブリッドチャット")
    print("="*60)
    print("コマンド:")
    print("  /memories - 保存済みメモリを表示")
    print("  /search <クエリ> - メモリ検索")
    print("  /mode - 現在の動作モード表示")
    print("  /quit - 終了")
    print("-" * 60)
    
    user_id = f"chat_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    chatbot = HybridAzureMem0ChatBot(user_id, use_azure_sql=True)
    
    while True:
        try:
            user_input = input("\n💬 あなた: ").strip()
            
            if not user_input:
                continue
            
            if user_input == "/quit":
                print("\n🗑️  チャットデータをクリーンアップ中...")
                chatbot.cleanup_all_memories()
                print("\n👋 チャットを終了します")
                break
            elif user_input == "/memories":
                chatbot.get_all_memories()
            elif user_input.startswith("/search "):
                query = user_input[8:].strip()
                if query:
                    chatbot.search_memory(query)
                else:
                    print("使用方法: /search <検索クエリ>")
            elif user_input == "/mode":
                mode = "フルAzure（SQL Server）" if chatbot.use_azure_sql else "ハイブリッド（SQLite）"
                print(f"🔧 現在の動作モード: {mode}")
            else:
                # 通常の対話
                chatbot.chat(user_input)
                
        except KeyboardInterrupt:
            print("\n\n🗑️  チャットデータをクリーンアップ中...")
            chatbot.cleanup_all_memories()
            print("\n👋 チャットを終了します")
            break
        except Exception as e:
            print(f"\n❌ エラー: {e}")


def main():
    """メイン実行関数"""
    print("🎯 Mem0 + Azureハイブリッド検証スクリプト")
    print("=" * 60)
    print("Azure AI Search + Azure SQL Server/SQLite + Azure OpenAI")
    print("=" * 60)
    
    while True:
        print("\n実行モードを選択してください:")
        print("1. ハイブリッドモードテスト")
        print("2. 対話形式チャット")
        print("3. 終了")
        
        choice = input("\n選択 (1-3): ").strip()
        
        if choice == "1":
            test_hybrid_mode()
        elif choice == "2":
            interactive_chat()
        elif choice == "3":
            print("👋 プログラムを終了します")
            break
        else:
            print("❌ 無効な選択です")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())