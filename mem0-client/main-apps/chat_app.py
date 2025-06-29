#!/usr/bin/env python3
"""
Mem0対話アプリケーション
長期記憶機能付きのチャットボット

使用方法:
python chat_app.py

依存関係:
pip install requests openai
"""

import json
import requests
import time
from datetime import datetime
from openai import AzureOpenAI
import os

# 設定
MEM0_API_BASE = "http://localhost:8888"
USER_ID = "chat_user_001"

# Azure OpenAI設定（.envから読み込み）
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "your-api-key-here")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-endpoint.openai.azure.com/")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# Azure OpenAI クライアント初期化
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2024-12-01-preview"
)

class Mem0ChatBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.conversation_history = []
        
    def save_memory(self, user_message: str, assistant_message: str):
        """会話をMem0に保存"""
        try:
            payload = {
                "messages": [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message}
                ],
                "user_id": self.user_id,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "app": "chat_bot"
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
            else:
                print(f"❌ 記憶保存失敗: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 記憶保存エラー: {e}")
    
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
                    print(f"🔍 関連記憶を{len(results)}件発見:")
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
    
    def generate_response(self, user_input: str):
        """ユーザー入力に対してLLMで応答生成"""
        
        # 関連する記憶を検索
        related_memories = self.search_memory(user_input)
        
        # システムプロンプトを構築
        system_prompt = """あなたは親しみやすいAIアシスタントです。
ユーザーとの過去の会話から得た記憶を活用して、パーソナライズされた応答をしてください。

応答のガイドライン:
- 過去の記憶を自然に会話に織り込む
- ユーザーの好みや状況を考慮する
- 親しみやすく、人間らしい口調で応答する
- 記憶がない場合は、素直に認めて新しい情報を求める
"""

        # 記憶を含むコンテキスト
        context = ""
        if related_memories:
            context = "\n【関連する記憶】\n"
            for memory in related_memories:
                context += f"- {memory['memory']}\n"
            context += "\n"
        
        # 会話履歴を含むメッセージ構築
        messages = [
            {"role": "system", "content": system_prompt + context}
        ]
        
        # 最近の会話履歴を追加（最大5ターン）
        recent_history = self.conversation_history[-10:]
        messages.extend(recent_history)
        
        # 現在のユーザー入力を追加
        messages.append({"role": "user", "content": user_input})
        
        try:
            response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"申し訳ありません。応答生成中にエラーが発生しました: {e}"
    
    def chat(self, user_input: str):
        """1回の対話を処理"""
        print(f"\n👤 ユーザー: {user_input}")
        
        # LLMで応答生成
        assistant_response = self.generate_response(user_input)
        print(f"🤖 アシスタント: {assistant_response}")
        
        # 会話履歴に追加
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        # Mem0に記憶保存
        self.save_memory(user_input, assistant_response)
        
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
    print("🎯 Mem0対話アプリを開始します")
    print("特別コマンド:")
    print("  /memories - 保存済み記憶を表示")
    print("  /quit - アプリを終了")
    print("=" * 50)
    
    # チャットボット初期化
    chatbot = Mem0ChatBot(USER_ID)
    
    while True:
        try:
            user_input = input("\n💬 あなた: ").strip()
            
            if not user_input:
                continue
                
            # 特別コマンド処理
            if user_input == "/quit":
                print("\n👋 チャットを終了します。お疲れさまでした！")
                break
            elif user_input == "/memories":
                chatbot.get_all_memories()
                continue
            
            # 通常の対話処理
            chatbot.chat(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 チャットを終了します。")
            break
        except Exception as e:
            print(f"\n❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()