#!/usr/bin/env python3
"""
RAG + Mem0長期記憶システム
RAG検索と長期記憶を組み合わせた対話システム

使用方法:
python rag_chat_app.py

依存関係:
pip install requests openai python-dotenv
"""

import json
import requests
import time
import re
import uuid
from datetime import datetime
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional

# 環境変数読み込み（複数のファイルを試行）
load_dotenv(".env.rag")  # RAG専用環境変数
load_dotenv(".env")      # デフォルト環境変数

# 設定
MEM0_API_BASE = "http://localhost:8888"
RAG_API_BASE = "http://localhost:8001"  # RAGシステムのエンドポイント

# Azure OpenAI設定
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# Azure OpenAI クライアント初期化
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2024-12-01-preview"
)

# RAG API用ヘッダー（環境変数から動的に取得）
def get_rag_headers():
    headers = {
        "llm-api-key": os.getenv("OPEN_AI_API_KEY"),
        "llm-api-version": os.getenv("OPEN_AI_API_VERSION"),
        "llm-endpoint": os.getenv("OPEN_AI_ENDPOINT"),
        "llm-model": os.getenv("OPEN_AI_MODEL"),
        "search-endpoint": os.getenv("SEARCH_ENDPOINT"),
        "search-api-key": os.getenv("SEARCH_API_KEY"),
        "search-index-name": os.getenv("INDEX_NAME"),
        "semantic-config-name": os.getenv("SEMANTIC_CONFIGURATION_NAME"),
        "azure-storage-connection-string": os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        "azure-container-name": os.getenv("AZURE_CONTAINER_NAME"),
    }
    
    # デバッグ用：環境変数の確認
    missing_vars = [key for key, value in headers.items() if not value]
    if missing_vars:
        print(f"⚠️ 未設定の環境変数: {missing_vars}")
    
    return headers

def debug_environment():
    """環境変数の確認用デバッグ関数"""
    env_vars = [
        "OPEN_AI_API_KEY", "OPEN_AI_API_VERSION", "OPEN_AI_ENDPOINT", "OPEN_AI_MODEL",
        "SEARCH_ENDPOINT", "SEARCH_API_KEY", "INDEX_NAME", "SEMANTIC_CONFIGURATION_NAME",
        "AZURE_STORAGE_CONNECTION_STRING", "AZURE_CONTAINER_NAME"
    ]
    
    print("\n🔍 環境変数確認:")
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # APIキーなどは最初の10文字のみ表示
            if "key" in var.lower() or "connection" in var.lower():
                display_value = value[:10] + "..." if len(value) > 10 else value
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: 未設定")
    print()

def remove_reference_section(text: str) -> str:
    """<reference>タグで囲まれた部分をテキストから削除"""
    cleaned_text = re.sub(r"<reference>.*?</reference>", "", text, flags=re.DOTALL)
    return cleaned_text.strip()

class RAGMem0ChatBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
    
    def extract_user_interests(self, user_message: str) -> str:
        """ユーザーの関心事項を明示的に抽出するためのコンテキスト追加"""
        interests_keywords = [
            "代理店", "契約", "経費", "分析", "項目", "名称", "社外飲食", 
            "手続き", "申請", "書類", "マニュアル", "規則", "要領"
        ]
        
        # 質問に含まれるキーワードを特定
        found_keywords = [kw for kw in interests_keywords if kw in user_message]
        
        context_info = f"""
【ユーザーの関心領域】
このユーザーは以下について関心を持っています：
- 主要なトピック: {', '.join(found_keywords) if found_keywords else '業務全般'}
- 質問の性質: 業務手続きに関する具体的な相談
- 学習すべき内容: ユーザーの業務上の課題と関心事項

【記憶すべき情報】
- ユーザーが気にしている具体的な業務領域
- 今後役立つ可能性のある関連トピック
- ユーザーの知識レベルや業務状況
"""
        return context_info
        
    def save_memory(self, user_message: str, assistant_message: str, metadata: Dict = None):
        """会話をMem0に保存（関心事項の抽出を重視）"""
        try:
            # ユーザーの関心事項を抽出
            interests_context = self.extract_user_interests(user_message)
            
            # より詳細な文脈情報を含むメッセージを構築
            enhanced_user_message = f"""
ユーザーの質問: {user_message}

{interests_context}

【会話の背景】
- このユーザーは業務上の具体的な問題について相談している
- 今後の類似相談に役立つ情報として記憶すべき
- ユーザーの専門分野や関心領域を把握して個人化された対応を可能にする
"""
            
            payload = {
                "messages": [
                    {"role": "user", "content": enhanced_user_message},
                    {"role": "assistant", "content": assistant_message}
                ],
                "user_id": self.user_id,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                    "app": "rag_chat_bot",
                    "conversation_type": "business_consultation",
                    "extract_user_interests": True,
                    **(metadata or {})
                }
            }
            
            response = requests.post(f"{MEM0_API_BASE}/memories", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"💾 記憶保存: {len(result.get('results', []))}件の新しい記憶")
                for memory in result.get('results', []):
                    if memory['event'] == 'ADD':
                        print(f"   📝 追加: {memory['memory']}")
                    elif memory['event'] == 'UPDATE':
                        print(f"   🔄 更新: {memory['memory']}")
                
                # 関心事項が少ない場合は、追加で明示的な記憶保存を実行
                if len(result.get('results', [])) == 0:
                    print("🧠 関心事項を明示的に記憶中...")
                    self._save_explicit_interests(user_message, metadata)
            else:
                print(f"❌ 記憶保存失敗: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 記憶保存エラー: {e}")
    
    def _save_explicit_interests(self, user_message: str, metadata: Dict = None):
        """明示的にユーザーの関心事項を記憶として保存"""
        try:
            # 関心事項を明示的に記述
            interest_message = f"""
このユーザーは以下について関心を持ち、相談している:

元の質問: {user_message}

【抽出すべき関心事項】
- ユーザーは代理店関連の業務について詳しく知りたがっている
- 経費の分類や会計処理について関心がある  
- 契約前後の取り扱いの違いについて理解を深めたい
- 業務マニュアルや規則の適用について学習したい

このユーザーの今後の質問傾向として記憶すべき。
"""
            
            payload = {
                "messages": [
                    {"role": "user", "content": interest_message},
                    {"role": "assistant", "content": "ユーザーの関心事項を記録しました。代理店業務や経費分類について今後もサポートします。"}
                ],
                "user_id": self.user_id,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                    "app": "rag_chat_bot",
                    "type": "explicit_interest_extraction",
                    **(metadata or {})
                }
            }
            
            response = requests.post(f"{MEM0_API_BASE}/memories", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   🎯 明示的関心事項: {len(result.get('results', []))}件追加")
                for memory in result.get('results', []):
                    if memory['event'] == 'ADD':
                        print(f"   📌 関心: {memory['memory']}")
                        
        except Exception as e:
            print(f"❌ 明示的記憶保存エラー: {e}")
    
    def search_memory(self, query: str, limit: int = 5):
        """関連する記憶を検索"""
        try:
            payload = {
                "query": query,
                "user_id": self.user_id,
                "limit": limit
            }
            
            response = requests.post(f"{MEM0_API_BASE}/search", json=payload)
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    print(f"🧠 長期記憶から{len(results)}件発見:")
                    for i, memory in enumerate(results, 1):
                        score = memory.get('score', 0)
                        print(f"   {i}. {memory['memory']} (関連度: {score:.3f})")
                return results
            else:
                print(f"❌ 記憶検索失敗: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 記憶検索エラー: {e}")
            return []
    
    def search_documents(self, query: str, filter_option: Optional[str] = None) -> Dict:
        """RAGシステムでの文書検索"""
        print("🔍 文書検索を実行中...")
        
        # フィルターの設定
        filters = []
        if filter_option:
            filter_map = {
                "1": "10_法人事務_オンライン操作マニュアル",
                "2": "20_法人事務_事務のしおり",
                "3": "40_事務要領（20241008時点）",
            }
            if filter_option in filter_map:
                filters = [filter_map[filter_option]]

        # 検索リクエスト
        search_request = {
            "conversation_id": self.session_id,
            "prompt": query,
            "filter": filters,
            "top": 10
        }

        try:
            headers = get_rag_headers()
            response = requests.post(
                f"{RAG_API_BASE}/search",
                json=search_request,
                headers=headers
            )
            
            if response.status_code == 200:
                results = response.json()
                search_count = len(results.get("all_search_results", []))
                print(f"📄 文書検索結果: {search_count}件")
                return results
            else:
                print(f"❌ 文書検索失敗: {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 文書検索エラー: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   ステータスコード: {e.response.status_code}")
                try:
                    error_detail = e.response.json()
                    print(f"   エラー詳細: {error_detail}")
                except:
                    print(f"   レスポンス: {e.response.text[:200]}")
            return {}
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            return {}

    def generate_rag_completion(self, query: str, search_results: Dict) -> Dict:
        """RAGシステムでの回答生成"""
        print("💭 RAG回答を生成中...")

        # 検索結果からチャンクを抽出
        selected_chunks = search_results.get("all_search_results", [])

        # 完了リクエスト
        completion_request = {
            "conversation_id": self.session_id,
            "prompt": query,
            "selected_chunks": selected_chunks,
            "conversation_history": self.conversation_history
        }

        try:
            headers = get_rag_headers()
            response = requests.post(
                f"{RAG_API_BASE}/completions",
                json=completion_request,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ RAG回答生成失敗: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ RAG回答生成エラー: {e}")
            return {}

    def should_use_rag(self, query: str, memories: List[Dict]) -> bool:
        """RAGを使用すべきかを判定"""
        
        # 記憶が十分にある場合（閾値は調整可能）
        if memories and len(memories) >= 2 and memories[0].get('score', 0) > 0.8:
            # 特定のキーワードがある場合はRAGを優先
            rag_keywords = [
                "マニュアル", "手順", "規則", "要領", "操作", "申請", "書類", 
                "システム", "処理", "事務", "業務", "法人", "手続き"
            ]
            
            for keyword in rag_keywords:
                if keyword in query:
                    return True
            
            # 記憶だけで回答可能と判断
            return False
        
        # 記憶が不十分な場合はRAGを使用
        return True

    def generate_memory_response(self, query: str, memories: List[Dict]):
        """記憶ベースでの応答生成"""
        print("🧠 記憶ベースで回答生成中...")
        
        # 記憶を含むシステムプロンプト
        system_prompt = """あなたは親しみやすいAIアシスタントです。
ユーザーとの過去の会話から得た記憶を活用して、パーソナライズされた応答をしてください。

応答のガイドライン:
- 過去の記憶を自然に会話に織り込む
- ユーザーの好みや状況を考慮する
- 親しみやすく、人間らしい口調で応答する
- 記憶の内容に基づいて具体的で有用な回答をする
"""

        # 記憶を含むコンテキスト
        context = "\n【関連する記憶】\n"
        for memory in memories:
            context += f"- {memory['memory']}\n"
        context += "\n"
        
        # メッセージ構築
        messages = [
            {"role": "system", "content": system_prompt + context}
        ]
        
        # 最近の会話履歴を追加
        recent_history = self.conversation_history[-10:]
        messages.extend(recent_history)
        
        # 現在のユーザー入力を追加
        messages.append({"role": "user", "content": query})
        
        try:
            response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"申し訳ありません。記憶ベース応答生成中にエラーが発生しました: {e}"

    def chat(self, user_input: str, filter_option: Optional[str] = None):
        """1回の対話を処理"""
        print(f"\n👤 ユーザー: {user_input}")
        
        # 1. 記憶検索
        related_memories = self.search_memory(user_input)
        
        # 2. RAGを使用するかを判定
        use_rag = self.should_use_rag(user_input, related_memories)
        
        assistant_response = ""
        rag_metadata = {}
        
        if use_rag:
            print("📊 判定: RAG検索を使用します")
            
            # 3. RAG文書検索
            search_results = self.search_documents(user_input, filter_option)
            
            if search_results:
                # 4. RAG回答生成
                completion_results = self.generate_rag_completion(user_input, search_results)
                
                if completion_results:
                    # referencesタグを削除
                    raw_answer = completion_results.get("answer", "回答を生成できませんでした")
                    assistant_response = remove_reference_section(raw_answer)
                    
                    # 参照情報の表示
                    references = completion_results.get("references", [])
                    if references:
                        print("\n📚 参照文書:")
                        for ref in references:
                            pages = ", ".join(map(str, ref.get("page_numbers", [])))
                            print(f"  - {ref.get('filename', 'N/A')}: {pages}ページ")
                    
                    # RAGメタデータを保存
                    rag_metadata = {
                        "rag_used": True,
                        "search_results_count": len(search_results.get("all_search_results", [])),
                        "references": references,
                        "filter_used": filter_option
                    }
                else:
                    # RAG失敗時は記憶ベースにフォールバック
                    assistant_response = self.generate_memory_response(user_input, related_memories)
                    rag_metadata = {"rag_used": False, "fallback_reason": "rag_completion_failed"}
            else:
                # 検索失敗時は記憶ベースにフォールバック
                assistant_response = self.generate_memory_response(user_input, related_memories)
                rag_metadata = {"rag_used": False, "fallback_reason": "rag_search_failed"}
        else:
            print("🧠 判定: 記憶ベースで回答します")
            
            # 5. 記憶ベース回答生成
            assistant_response = self.generate_memory_response(user_input, related_memories)
            rag_metadata = {"rag_used": False, "memory_based": True}
        
        print(f"🤖 アシスタント: {assistant_response}")
        
        # 6. 会話履歴に追加
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        # 7. Mem0に記憶保存
        self.save_memory(user_input, assistant_response, rag_metadata)
        
        return assistant_response
    
    def get_all_memories(self):
        """保存されている全記憶を表示"""
        try:
            response = requests.get(f"{MEM0_API_BASE}/memories", params={"user_id": self.user_id})
            
            if response.status_code == 200:
                memories = response.json().get('results', [])
                if memories:
                    print(f"\n📚 保存済み記憶 ({len(memories)}件):")
                    for i, memory in enumerate(memories, 1):
                        created_at = memory.get('created_at', '')
                        print(f"   {i}. {memory['memory']} ({created_at})")
                else:
                    print("\n📚 保存済み記憶: なし")
            else:
                print(f"❌ 記憶取得失敗: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 記憶取得エラー: {e}")

def main():
    """メイン実行関数"""
    print("🎯 RAG + Mem0 長期記憶対話システムを開始します")
    print("=" * 60)
    
    # 環境変数の確認
    debug_environment()
    print("特別コマンド:")
    print("  /memories - 保存済み記憶を表示")
    print("  /quit - アプリを終了")
    print("\nフィルターオプション:")
    print("  1: オンライン操作マニュアル")
    print("  2: 事務のしおり") 
    print("  3: 事務要領")
    print("=" * 60)
    
    # ユーザーIDの設定
    user_id = input("👤 ユーザーID (Enterでデフォルト): ").strip() or "rag_user_001"
    
    # チャットボット初期化
    chatbot = RAGMem0ChatBot(user_id)
    print(f"✅ セッション開始: {chatbot.session_id}")
    
    while True:
        try:
            user_input = input("\n💬 質問: ").strip()
            
            if not user_input:
                continue
                
            # 特別コマンド処理
            if user_input == "/quit":
                print("\n👋 チャットを終了します。お疲れさまでした！")
                break
            elif user_input == "/memories":
                chatbot.get_all_memories()
                continue
            
            # フィルター選択
            print("\n📁 フィルターを選択してください (Enterでスキップ):")
            filter_choice = input("  選択 (1-3): ").strip() or None
            
            # 通常の対話処理
            chatbot.chat(user_input, filter_choice)
            
        except KeyboardInterrupt:
            print("\n\n👋 チャットを終了します。")
            break
        except Exception as e:
            print(f"\n❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()