#!/usr/bin/env python3
"""
Mem0 + Azure完全統合検証スクリプト
Azure SQL Server + Azure AI Searchを使用したmem0の完全動作確認

特徴:
- Azure AI Search: ベクトル検索
- Azure SQL Server: 履歴管理
- Azure OpenAI: LLM + 埋め込み

使用方法:
cd azure-test
python mem0_azure_full_test.py
"""

import os
import sys
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

try:
    from mem0 import Memory
    from openai import AzureOpenAI
    import pyodbc
    from azure_sql_storage import AzureSQLManager
except ImportError as e:
    print(f"❌ 必要なライブラリがインストールされていません: {e}")
    print("以下のコマンドでインストールしてください:")
    print("pip install mem0ai openai azure-search-documents pyodbc")
    sys.exit(1)


class FullAzureMem0ChatBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.conversation_history = []
        
        # Azure構成の取得
        self._validate_azure_config()
        self._init_azure_sql()
        self._init_mem0()
        self._init_openai()
        
    def _validate_azure_config(self):
        """Azure設定の検証"""
        required_vars = [
            'AZURE_SEARCH_ENDPOINT',
            'AZURE_SEARCH_API_KEY',
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_SQL_SERVER',
            'AZURE_SQL_DATABASE',
            'AZURE_SQL_USERNAME',
            'AZURE_SQL_PASSWORD'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"環境変数が設定されていません: {', '.join(missing_vars)}")
    
    def _init_azure_sql(self):
        """Azure SQL Server初期化"""
        print("🔧 Azure SQL Server初期化中...")
        
        server = os.getenv('AZURE_SQL_SERVER')
        database = os.getenv('AZURE_SQL_DATABASE')
        username = os.getenv('AZURE_SQL_USERNAME')
        password = os.getenv('AZURE_SQL_PASSWORD')
        
        # Azure SQL ServerのFQDNを確認
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
        
        try:
            print(f"   接続先: {server}")
            print(f"   データベース: {database}")
            print(f"   ユーザー: {username}")
            
            # 接続テスト
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            # カスタム履歴管理インスタンス作成
            self.sql_storage = AzureSQLManager(connection_string)
            
            print(f"✅ Azure SQL Server初期化成功！")
            print(f"   - サーバー: {server}")
            print(f"   - データベース: {database}")
            version_line = version.split('\n')[0]
            print(f"   - バージョン: {version_line}")
            
        except pyodbc.Error as e:
            print(f"❌ Azure SQL Server接続エラー: {e}")
            if 'Login timeout expired' in str(e):
                print("\n考えられる原因:")
                print("1. ファイアウォール設定でクライアントIPが許可されていない")
                print("2. サーバー名が正しくない")
                print("3. ネットワーク接続の問題")
                print("\nAzure Portalで以下を確認してください:")
                print(f"- SQLサーバー名: {server}")
                print("- ファイアウォール設定でクライアントIPを許可")
            elif 'Login failed' in str(e):
                print("\n認証エラー: ユーザー名またはパスワードが正しくありません")
            raise
    
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
            "version": "v1.1",  # 最新のAPI形式を使用
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
            print(f"   - 履歴DB: Azure SQL Server (カスタム)")
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
    
    def add_memory_with_sql_history(self, user_message: str, assistant_message: str):
        """メモリ追加 + Azure SQL履歴記録"""
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
                    "app": "azure_full_test"
                }
            )
            
            # Azure SQLに履歴記録
            # API v1.1の応答形式を確認
            print(f"   デバッグ: result type = {type(result)}")
            
            # API v1.1形式の場合
            if isinstance(result, dict):
                # resultsフィールドを確認
                if 'results' in result:
                    memories_to_save = result['results']
                    print(f"   デバッグ: results = {memories_to_save}")
                else:
                    print(f"   デバッグ: result keys = {list(result.keys())}")
                    memories_to_save = []
            else:
                memories_to_save = result if result else []
            
            # 実際のメモリ数を確認
            actual_memory_count = len(memories_to_save) if isinstance(memories_to_save, list) else 0
            
            for memory_data in memories_to_save:
                # API v1.1の形式に対応
                if isinstance(memory_data, dict):
                    memory_id = memory_data.get('id', str(uuid.uuid4()))
                    memory_text = memory_data.get('memory', '')
                    event = memory_data.get('event', 'ADD')
                    
                    if memory_id and memory_text:
                        # デバッグ情報
                        print(f"   💾 SQL履歴追加: ID={memory_id[:8]}..., Event={event}")
                        
                        self.sql_storage.add(
                            memory_id=memory_id,
                            new_memory=memory_text,
                            event=event,
                            actor_id=self.user_id,
                            role='user'
                        )
            
            if actual_memory_count > 0:
                print(f"💾 メモリ保存: {actual_memory_count}件の記憶を追加")
                for memory in memories_to_save:
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
                # API v1.1形式の確認
                if isinstance(results, dict):
                    results_list = results.get('results', [])
                elif isinstance(results, list) and len(results) > 0 and isinstance(results[0], str):
                    # 文字列のリストの場合
                    results_list = results
                    print(f"🔍 関連記憶: {len(results_list)}件発見")
                    for i, result in enumerate(results_list, 1):
                        print(f"   {i}. {result}")
                    return results_list
                else:
                    results_list = results
                
                print(f"🔍 関連記憶: {len(results_list)}件発見")
                for i, result in enumerate(results_list, 1):
                    if isinstance(result, dict):
                        memory_text = result.get('memory', str(result))
                        score = result.get('score', 'N/A')
                        print(f"   {i}. {memory_text}")
                        if score != 'N/A':
                            print(f"      関連度: {score:.3f}")
                    else:
                        print(f"   {i}. {result}")
            else:
                print("🔍 関連記憶: 見つかりませんでした")
                
            return results
            
        except Exception as e:
            print(f"❌ メモリ検索エラー: {e}")
            return []
    
    def get_sql_history(self, memory_id: str = None):
        """Azure SQL履歴を取得"""
        try:
            # 最新の履歴を取得（actor_idフィルタなし）
            history = self.sql_storage.get_history(
                memory_id=memory_id,
                actor_id=None,  # 全ユーザーの履歴を表示
                limit=50
            )
            
            if history:
                print(f"📜 Azure SQL履歴: {len(history)}件")
                for i, record in enumerate(history, 1):
                    event = record.get('event', 'UNKNOWN')
                    memory_text = record.get('new_memory', record.get('old_memory', ''))
                    memory_id = record.get('memory_id', 'N/A')
                    created_at = record.get('created_at', 'N/A')
                    
                    # メモリ内容を適切に表示
                    display_text = memory_text[:50] + '...' if len(memory_text) > 50 else memory_text
                    
                    print(f"   {i}. [{event}] {display_text}")
                    print(f"      ID: {memory_id[:8]}... | 時刻: {created_at}")
            else:
                print("📜 Azure SQL履歴: なし")
                
            return history
            
        except Exception as e:
            print(f"❌ SQL履歴取得エラー: {e}")
            return []
    
    def get_sql_stats(self):
        """Azure SQL統計情報を取得"""
        try:
            stats = self.sql_storage.get_stats()
            
            print("📊 Azure SQL統計:")
            print(f"   総履歴数: {stats.get('total_count', 0)}")
            print(f"   最新履歴: {stats.get('latest_history', 'N/A')}")
            
            event_stats = stats.get('event_stats', {})
            if event_stats:
                print("   イベント別:")
                for event, count in event_stats.items():
                    print(f"     {event}: {count}件")
            
            return stats
            
        except Exception as e:
            print(f"❌ SQL統計取得エラー: {e}")
            return {}
    
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
        
        # メモリに保存 + SQL履歴記録
        self.add_memory_with_sql_history(user_input, assistant_response)
        
        return assistant_response
    
    def cleanup_all_memories(self):
        """全メモリとSQL履歴を削除"""
        try:
            # 全メモリを取得
            all_memories = self.memory.get_all(user_id=self.user_id)
            deleted_count = 0
            
            # mem0からメモリを削除
            if isinstance(all_memories, list):
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
            
            # SQL履歴の論理削除
            if self.sql_storage:
                print("   🗑️  SQL履歴をクリーンアップ中...")
                sql_deleted = self.sql_storage.delete_all_history(actor_id=self.user_id)
                print(f"   ✅ SQL履歴 {sql_deleted}件を論理削除しました")
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ クリーンアップエラー: {e}")
            return 0


def cleanup_memories(chatbot):
    """テスト後のメモリクリーンアップ"""
    chatbot.cleanup_all_memories()


def test_full_azure_integration():
    """完全Azure統合テスト"""
    print("\n" + "="*60)
    print("🧪 完全Azure統合テスト")
    print("="*60)
    
    test_user = f"full_test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    chatbot = FullAzureMem0ChatBot(test_user)
    
    # テストデータ
    test_conversations = [
        ("私の名前は佐藤花子です。", "佐藤花子さん、よろしくお願いします！"),
        ("職業はソフトウェアエンジニアです。", "ソフトウェアエンジニアなんですね！"),
        ("Azureクラウドの開発が得意です。", "Azureクラウド開発がご専門なんですね！")
    ]
    
    # 1. メモリ追加テスト
    print("\n📝 メモリ追加 + SQL履歴テスト:")
    added_count = 0
    for user_msg, assistant_msg in test_conversations:
        result = chatbot.add_memory_with_sql_history(user_msg, assistant_msg)
        if isinstance(result, dict) and 'results' in result:
            count = len(result['results'])
        else:
            count = 0
        added_count += count
        print(f"   結果: {count}件追加")
    
    # 2. メモリ検索テスト
    print("\n🔍 メモリ検索テスト:")
    test_queries = ["名前について", "職業は何", "Azure"]
    for query in test_queries:
        print(f"\n   クエリ: '{query}'")
        results = chatbot.search_memory(query, limit=3)
    
    # 3. SQL履歴確認
    print("\n📜 SQL履歴確認:")
    chatbot.get_sql_history()
    
    # 4. SQL統計確認
    print("\n📊 SQL統計確認:")
    chatbot.get_sql_stats()
    
    # 5. クリーンアップ（テストデータ削除）
    print("\n🗑️  テストデータのクリーンアップ:")
    cleanup_memories(chatbot)
    
    print(f"\n✅ 完全統合テスト完了！")
    return True


def interactive_chat():
    """対話形式のチャット"""
    print("\n" + "="*60)
    print("💬 完全Azure統合チャット")
    print("="*60)
    print("コマンド:")
    print("  /search <クエリ> - メモリ検索")
    print("  /history - SQL履歴表示")
    print("  /stats - SQL統計表示")
    print("  /quit - 終了")
    print("-" * 60)
    
    user_id = f"chat_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    chatbot = FullAzureMem0ChatBot(user_id)
    
    while True:
        try:
            user_input = input("\n💬 あなた: ").strip()
            
            if not user_input:
                continue
            
            if user_input == "/quit":
                print("\n🗑️  チャットデータをクリーンアップ中...")
                cleanup_memories(chatbot)
                print("\n👋 チャットを終了します")
                break
            elif user_input.startswith("/search "):
                query = user_input[8:].strip()
                if query:
                    chatbot.search_memory(query)
                else:
                    print("使用方法: /search <検索クエリ>")
            elif user_input == "/history":
                chatbot.get_sql_history()
            elif user_input == "/stats":
                chatbot.get_sql_stats()
            else:
                # 通常の対話
                chatbot.chat(user_input)
                
        except KeyboardInterrupt:
            print("\n\n🗑️  チャットデータをクリーンアップ中...")
            cleanup_memories(chatbot)
            print("\n👋 チャットを終了します")
            break
        except Exception as e:
            print(f"\n❌ エラー: {e}")


def main():
    """メイン実行関数"""
    print("🎯 Mem0 + Azure完全統合検証スクリプト")
    print("=" * 60)
    print("Azure AI Search + Azure SQL Server + Azure OpenAI")
    print("=" * 60)
    
    # 環境確認
    try:
        test_user = "env_test_user"
        FullAzureMem0ChatBot(test_user)
        print("✅ 完全Azure設定確認完了")
    except Exception as e:
        print(f"❌ 設定エラー: {e}")
        print("\n環境変数を確認してください:")
        print("- Azure AI Search設定")
        print("- Azure SQL Server設定")
        print("- Azure OpenAI設定")
        return 1
    
    while True:
        print("\n実行モードを選択してください:")
        print("1. 完全Azure統合テスト")
        print("2. 対話形式チャット")
        print("3. 終了")
        
        choice = input("\n選択 (1-3): ").strip()
        
        if choice == "1":
            test_full_azure_integration()
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