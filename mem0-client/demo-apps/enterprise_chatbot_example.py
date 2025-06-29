#!/usr/bin/env python3
"""
企業チャットボット with Mem0 - 実装例
ビジネスシナリオに特化した長期記憶活用システム

機能:
- 社員認証連携
- 部署・役職に応じたパーソナライゼーション  
- 業務ナレッジの継続学習
- セキュリティ・プライバシー保護
"""

import json
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import hashlib
import os
from openai import AzureOpenAI

# 企業環境設定
MEM0_API_BASE = "http://localhost:8888"
COMPANY_NAME = "サンプル商事株式会社"

# Azure OpenAI設定（企業用）
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-12-01-preview"
)

@dataclass
class UserProfile:
    """社員プロファイル"""
    employee_id: str
    name: str
    department: str
    role: str
    access_level: int  # 1:一般社員, 2:主任, 3:課長, 4:部長
    email: str

class EnterpriseMemoryManager:
    """企業向け記憶管理システム"""
    
    def __init__(self):
        self.session_cache = {}
    
    def create_user_memory_id(self, employee_id: str) -> str:
        """プライバシー保護された記憶用ID生成"""
        # 社員IDをハッシュ化して個人を特定できないようにする
        hash_object = hashlib.sha256(f"{COMPANY_NAME}_{employee_id}".encode())
        return f"emp_{hash_object.hexdigest()[:16]}"
    
    def extract_business_context(self, message: str, user_profile: UserProfile) -> str:
        """業務コンテキストの抽出と強化"""
        
        # 業務キーワードの特定
        business_keywords = {
            "経理": ["経費", "申請", "精算", "会計", "予算", "決算"],
            "人事": ["採用", "評価", "給与", "研修", "労務", "制度"],
            "営業": ["顧客", "契約", "提案", "売上", "目標", "商談"],
            "IT": ["システム", "ネットワーク", "セキュリティ", "開発", "運用"],
            "総務": ["契約", "法務", "施設", "備品", "手続き", "規程"]
        }
        
        # ユーザーの部署に関連するキーワードを特定
        dept_keywords = business_keywords.get(user_profile.department, [])
        found_keywords = [kw for kw in dept_keywords if kw in message]
        
        # 役職レベルに応じた情報強化
        authority_context = {
            1: "一般社員として基本的な業務支援が必要",
            2: "主任として部下指導や効率化に関心あり", 
            3: "課長として管理業務や戦略的判断が重要",
            4: "部長として組織運営や意思決定に責任"
        }
        
        enhanced_context = f"""
【社員情報】
- 部署: {user_profile.department}
- 役職: {user_profile.role} 
- 権限レベル: {user_profile.access_level}

【業務コンテキスト】
- 質問内容: {message}
- 関連業務領域: {', '.join(found_keywords) if found_keywords else '一般業務'}
- 役職特性: {authority_context.get(user_profile.access_level, '一般業務')}

【記憶すべき要素】
- この社員の業務関心領域と専門性
- 質問の難易度レベルと求められる回答の深さ
- 今後の類似業務での活用可能性
- 部署特有の業務パターンや課題
"""
        return enhanced_context
    
    def anonymize_sensitive_data(self, content: str) -> str:
        """機密情報の自動匿名化"""
        
        # 個人情報のマスキング
        patterns = {
            r'\b\d{4}-\d{4}-\d{4}-\d{4}\b': '[カード番号]',
            r'\b\d{3}-\d{4}-\d{4}\b': '[電話番号]', 
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '[メールアドレス]',
            r'\b\d{3}-\d{4}\b': '[郵便番号]',
            r'パスワード.*': '[パスワード情報]',
            r'暗証番号.*': '[暗証番号情報]'
        }
        
        for pattern, replacement in patterns.items():
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        return content
    
    def save_conversation_memory(self, user_message: str, assistant_response: str, 
                               user_profile: UserProfile, metadata: Dict = None):
        """企業コンテキストを含む記憶保存"""
        
        try:
            # コンテキスト強化
            business_context = self.extract_business_context(user_message, user_profile)
            
            # 機密情報の匿名化
            safe_message = self.anonymize_sensitive_data(user_message)
            safe_response = self.anonymize_sensitive_data(assistant_response)
            
            # 記憶用データ構築
            enhanced_message = f"""
{business_context}

【実際の質問】
{safe_message}

【提供した回答】  
{safe_response}

この対話から、社員の業務理解度、関心領域、必要なサポートレベルを学習し、
今後より個人に最適化されたサポートを提供するために記憶すること。
"""
            
            # 記憶保存API呼び出し
            memory_id = self.create_user_memory_id(user_profile.employee_id)
            
            payload = {
                "messages": [
                    {"role": "user", "content": enhanced_message},
                    {"role": "assistant", "content": "業務サポート情報として記録しました。今後の対話で活用します。"}
                ],
                "user_id": memory_id,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "department": user_profile.department,
                    "role": user_profile.role,
                    "access_level": user_profile.access_level,
                    "app": "enterprise_chatbot",
                    "company": COMPANY_NAME,
                    "anonymized": True,
                    **(metadata or {})
                }
            }
            
            response = requests.post(f"{MEM0_API_BASE}/memories", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"💾 記憶保存完了: {len(result.get('results', []))}件")
                return result
            else:
                print(f"❌ 記憶保存失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 記憶保存エラー: {e}")
            return None
    
    def search_relevant_memories(self, query: str, user_profile: UserProfile, limit: int = 5) -> List[Dict]:
        """ユーザー固有の記憶検索"""
        
        try:
            memory_id = self.create_user_memory_id(user_profile.employee_id)
            
            payload = {
                "query": query,
                "user_id": memory_id,
                "limit": limit
            }
            
            response = requests.post(f"{MEM0_API_BASE}/search", json=payload)
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                print(f"🧠 関連記憶発見: {len(results)}件")
                return results
            else:
                print(f"❌ 記憶検索失敗: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 記憶検索エラー: {e}")
            return []

class EnterpriseChatBot:
    """企業向けチャットボット"""
    
    def __init__(self):
        self.memory_manager = EnterpriseMemoryManager()
        self.conversation_history = {}
    
    def get_personalized_response(self, user_message: str, user_profile: UserProfile) -> str:
        """パーソナライズされた企業回答生成"""
        
        # 1. 関連記憶の検索
        memories = self.memory_manager.search_relevant_memories(user_message, user_profile)
        
        # 2. 記憶ベースのコンテキスト構築
        memory_context = ""
        if memories:
            memory_context = "【過去の記憶】\n"
            for memory in memories:
                score = memory.get('score', 0)
                content = memory.get('memory', '')
                memory_context += f"- [関連度: {score:.2f}] {content}\n"
            memory_context += "\n"
        
        # 3. 役職・部署に応じたシステムプロンプト
        role_prompts = {
            1: "基本的で分かりやすい説明を心がけ、必要に応じて詳細な手順を提供してください。",
            2: "実務的なアドバイスと効率化の提案を含めてください。部下への指導ポイントも考慮してください。",
            3: "管理の観点からの判断材料や、チーム運営に関する示唆を含めてください。",
            4: "戦略的視点と組織全体への影響を考慮した回答を提供してください。"
        }
        
        system_prompt = f"""
あなたは{COMPANY_NAME}の社内AIアシスタントです。
社員の{user_profile.name}さん（{user_profile.department}・{user_profile.role}）からの質問にお答えします。

{memory_context}

【回答ガイドライン】
- 過去の記憶を自然に活用して個人に最適化された回答を提供
- {user_profile.department}業務の専門性を考慮
- {role_prompts.get(user_profile.access_level, '適切なレベルで')}
- 企業の規程や手続きに準拠した正確な情報を提供
- 必要に応じて関連部署や担当者への案内も含める

【注意事項】
- 機密情報は適切に保護する
- 不明な点は推測せず、確認を促す
- 常に建設的で業務効率向上に寄与する回答を心がける
"""
        
        # 4. 会話履歴の取得
        user_id = user_profile.employee_id
        history = self.conversation_history.get(user_id, [])
        
        # 5. LLMによる回答生成
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-10:])  # 直近10件の履歴
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,  # 企業用途では保守的に
                max_tokens=800
            )
            
            assistant_response = response.choices[0].message.content
            
            # 6. 会話履歴の更新
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            self.conversation_history[user_id].extend([
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ])
            
            # 7. 記憶への保存
            self.memory_manager.save_conversation_memory(
                user_message, assistant_response, user_profile
            )
            
            return assistant_response
            
        except Exception as e:
            return f"申し訳ありません。システムエラーが発生しました。IT部門にお問い合わせください。(エラー: {e})"
    
    def get_user_memory_summary(self, user_profile: UserProfile) -> str:
        """ユーザーの記憶サマリー取得"""
        
        memories = self.memory_manager.search_relevant_memories("", user_profile, limit=20)
        
        if not memories:
            return "記憶データがありません。"
        
        # 記憶の分析
        topics = {}
        for memory in memories:
            content = memory.get('memory', '')
            # 簡単なトピック分類（実際にはより高度な分析が可能）
            if '経費' in content:
                topics['経費関連'] = topics.get('経費関連', 0) + 1
            elif '申請' in content:
                topics['申請業務'] = topics.get('申請業務', 0) + 1
            elif '契約' in content:
                topics['契約業務'] = topics.get('契約業務', 0) + 1
        
        summary = f"""
📊 {user_profile.name}さんの学習サマリー
部署: {user_profile.department}
役職: {user_profile.role}

📚 記憶件数: {len(memories)}件
🔍 主な関心領域: {', '.join(topics.keys()) if topics else '様々な業務'}

💡 この情報により、より個人に最適化されたサポートを提供しています。
"""
        return summary

def demo_enterprise_chatbot():
    """企業チャットボットのデモンストレーション"""
    
    print(f"🏢 {COMPANY_NAME} 社内AIアシスタント")
    print("=" * 60)
    
    # サンプル社員プロファイル
    users = [
        UserProfile("E001", "田中太郎", "経理", "課長", 3, "tanaka@company.com"),
        UserProfile("E002", "佐藤花子", "人事", "主任", 2, "sato@company.com"),
        UserProfile("E003", "山田次郎", "営業", "一般社員", 1, "yamada@company.com")
    ]
    
    chatbot = EnterpriseChatBot()
    
    # 各ユーザーでのデモ対話
    demo_conversations = [
        ("E001", "経費申請の承認フローについて教えてください"),
        ("E002", "新入社員研修の計画立案で注意すべき点は？"),
        ("E003", "顧客提案書の作成手順を教えてください"),
        ("E001", "四半期決算の準備で優先すべき業務は？")  # 田中さんの2回目
    ]
    
    for employee_id, question in demo_conversations:
        # ユーザープロファイル取得
        user = next(u for u in users if u.employee_id == employee_id)
        
        print(f"\n👤 {user.name}さん（{user.department}・{user.role}）")
        print(f"💬 質問: {question}")
        
        # チャットボット回答
        response = chatbot.get_personalized_response(question, user)
        print(f"🤖 回答: {response}")
        
        print("-" * 60)
    
    # 記憶サマリーの表示
    print("\n📊 ユーザー記憶サマリー:")
    for user in users:
        summary = chatbot.get_user_memory_summary(user)
        print(summary)

if __name__ == "__main__":
    demo_enterprise_chatbot()