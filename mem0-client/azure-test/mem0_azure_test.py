#!/usr/bin/env python3
"""
Mem0 + Azure統合検証スクリプト
Azure SQL Server + Azure AI Searchを使用したmem0の動作確認

機能:
- mem0ライブラリを直接使用（サーバー起動不要）
- Azure SQL Server: 履歴管理
- Azure AI Search: ベクトル検索
- 対話形式でのメモリ管理テスト

使用方法:
cd azure-test
python mem0_azure_test.py
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv("../.env.azure.test")

try:
    from mem0 import Memory
    from openai import AzureOpenAI
except ImportError as e:
    print(f"❌ 必要なライブラリがインストールされていません: {e}")
    print("以下のコマンドでインストールしてください:")
    print("pip install mem0ai openai azure-search-documents")
    sys.exit(1)


class AzureMem0ChatBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.conversation_history = []
        
        # Azure構成の取得
        self._validate_azure_config()
        self._init_mem0()
        self._init_openai()
        
    def _validate_azure_config(self):
        """Azure設定の検証"""
        required_vars = [
            'AZURE_SEARCH_ENDPOINT',
            'AZURE_SEARCH_API_KEY',
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_ENDPOINT'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"環境変数が設定されていません: {', '.join(missing_vars)}")
    
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
            print(f"   - インデックス: {config['vector_store']['config']['collection_name']}")
            print(f"   - 埋め込み: {config['embedder']['config']['model']}")
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
        """会話をメモリに追加"""
        try:
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message}
            ]
            
            result = self.memory.add(
                messages=messages,
                user_id=self.user_id,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "app": "azure_chat_test"
                }
            )
            
            if result:
                print(f"💾 メモリ保存: {len(result)}件の記憶を追加")
                for memory in result:
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
    
    def cleanup_test_memories(self):
        """テストメモリのクリーンアップ"""
        try:
            all_memories = self.get_all_memories()
            deleted_count = 0
            
            for memory in all_memories:
                try:
                    if isinstance(memory, dict):
                        memory_id = memory.get('id')
                    elif hasattr(memory, 'id'):
                        memory_id = memory.id
                    else:
                        continue
                    
                    if memory_id:
                        self.memory.delete(memory_id=memory_id)
                        deleted_count += 1
                except Exception as delete_error:
                    print(f"削除エラー: {delete_error}")
            
            print(f"🗑️  {deleted_count}件のメモリを削除しました")
            return deleted_count
            
        except Exception as e:
            print(f"❌ クリーンアップエラー: {e}")
            return 0


def test_basic_memory_operations():
    """基本的なメモリ操作のテスト"""
    print("\n" + "="*60)
    print("🧪 基本メモリ操作テスト")
    print("="*60)
    
    test_user = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    chatbot = AzureMem0ChatBot(test_user)
    
    # テストデータ
    test_conversations = [
        ("私の名前は田中太郎です。", "田中太郎さん、よろしくお願いします！"),
        ("趣味はプログラミングとAI技術の学習です。", "プログラミングとAI技術がお好きなんですね！"),
        ("最近、Pythonでチャットボットを作っています。", "Pythonでのチャットボット開発、楽しそうですね！")
    ]
    
    # 1. メモリ追加テスト
    print("\n📝 メモリ追加テスト:")
    for user_msg, assistant_msg in test_conversations:
        result = chatbot.add_memory(user_msg, assistant_msg)
        print(f"   結果: {len(result) if result else 0}件追加")
    
    # 2. メモリ検索テスト
    print("\n🔍 メモリ検索テスト:")
    test_queries = ["名前について", "趣味は何", "プログラミング"]
    for query in test_queries:
        print(f"\n   クエリ: '{query}'")
        results = chatbot.search_memory(query, limit=3)
    
    # 3. 全メモリ取得テスト
    print("\n📚 全メモリ取得テスト:")
    all_memories = chatbot.get_all_memories()
    
    # 4. クリーンアップ
    print("\n🗑️  クリーンアップ:")
    deleted_count = chatbot.cleanup_test_memories()
    
    print(f"\n✅ 基本テスト完了！")
    return True


def interactive_chat():
    """対話形式のチャット"""
    print("\n" + "="*60)
    print("💬 Azure Mem0 対話チャット")
    print("="*60)
    print("コマンド:")
    print("  /memories - 保存済みメモリを表示")
    print("  /search <クエリ> - メモリ検索")
    print("  /cleanup - テストメモリを削除")
    print("  /quit - 終了")
    print("-" * 60)
    
    user_id = f"chat_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    chatbot = AzureMem0ChatBot(user_id)
    
    while True:
        try:
            user_input = input("\n💬 あなた: ").strip()
            
            if not user_input:
                continue
            
            if user_input == "/quit":
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
            elif user_input == "/cleanup":
                confirm = input("本当にメモリを削除しますか？ (y/n): ").strip().lower()
                if confirm == 'y':
                    chatbot.cleanup_test_memories()
            else:
                # 通常の対話
                chatbot.chat(user_input)
                
        except KeyboardInterrupt:
            print("\n\n👋 チャットを終了します")
            break
        except Exception as e:
            print(f"\n❌ エラー: {e}")


def main():
    """メイン実行関数"""
    print("🎯 Mem0 + Azure統合検証スクリプト")
    print("=" * 60)
    
    # 環境確認
    try:
        test_user = "env_test_user"
        AzureMem0ChatBot(test_user)
        print("✅ Azure設定確認完了")
    except Exception as e:
        print(f"❌ 設定エラー: {e}")
        print("\n.env.azure.testファイルを確認してください")
        return 1
    
    while True:
        print("\n実行モードを選択してください:")
        print("1. 基本メモリ操作テスト")
        print("2. 対話形式チャット")
        print("3. 終了")
        
        choice = input("\n選択 (1-3): ").strip()
        
        if choice == "1":
            test_basic_memory_operations()
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