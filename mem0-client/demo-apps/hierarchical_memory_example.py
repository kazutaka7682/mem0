#!/usr/bin/env python3
"""
mem0を使用した階層型ユーザー記憶システムの実装例

ユーザー記憶の分類構造：
├── 基本情報（部署、役職、専門分野）
├── 業務記憶
│   ├── 日常業務（手続き、ルール）
│   └── プロジェクト記憶（進行中、完了済み）
└── 学習記憶
    ├── 理解度（習熟レベル）
    └── 関心領域（重点分野）
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from enum import Enum

# 設定
MEM0_API_BASE = "http://localhost:8888"

class MemoryCategory(Enum):
    """記憶カテゴリの定義"""
    BASIC_INFO = "basic_info"
    DAILY_WORK = "daily_work"
    PROJECT = "project"
    UNDERSTANDING = "understanding"
    INTEREST = "interest"

class MemoryImportance(Enum):
    """記憶の重要度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class MemoryMetadata:
    """記憶メタデータの構造定義"""
    category: MemoryCategory
    subcategory: str
    importance: MemoryImportance
    tags: List[str]
    department: str
    role: str
    access_level: int
    expiry_date: Optional[str] = None  # 有効期限
    source: Optional[str] = None       # 情報源
    confidence: float = 1.0            # 信頼度

class HierarchicalMemoryManager:
    """階層型記憶管理システム"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        
    def create_structured_payload(self, content: str, metadata: MemoryMetadata) -> Dict:
        """構造化されたpayloadの作成"""
        
        # mem0のカスタムメタデータとして階層情報を保存
        structured_metadata = {
            # 記憶分類
            "memory_category": metadata.category.value,
            "memory_subcategory": metadata.subcategory,
            "memory_importance": metadata.importance.value,
            
            # 階層構造
            "hierarchy": {
                "level_1": metadata.category.value,
                "level_2": metadata.subcategory,
                "path": f"{metadata.category.value}/{metadata.subcategory}"
            },
            
            # 業務コンテキスト
            "business_context": {
                "department": metadata.department,
                "role": metadata.role,
                "access_level": metadata.access_level
            },
            
            # 記憶属性
            "memory_attributes": {
                "tags": metadata.tags,
                "importance_score": metadata.importance.value,
                "confidence": metadata.confidence,
                "source": metadata.source,
                "expiry_date": metadata.expiry_date
            },
            
            # 検索・フィルタリング用
            "searchable_fields": {
                "category_search": metadata.category.value,
                "tag_search": " ".join(metadata.tags),
                "dept_role": f"{metadata.department}_{metadata.role}"
            },
            
            # タイムスタンプ
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        }
        
        return {
            "messages": [
                {"role": "user", "content": content}
            ],
            "user_id": self.user_id,
            "metadata": structured_metadata
        }
    
    def save_basic_info(self, name: str, department: str, role: str, specialties: List[str]):
        """基本情報の保存"""
        content = f"社員基本情報：氏名は{name}、{department}所属、{role}、専門分野は{', '.join(specialties)}"
        
        metadata = MemoryMetadata(
            category=MemoryCategory.BASIC_INFO,
            subcategory="personal_profile",
            importance=MemoryImportance.CRITICAL,
            tags=["profile", "basic", "personal"] + specialties,
            department=department,
            role=role,
            access_level=1,  # 基本情報は低アクセスレベル
            source="user_registration"
        )
        
        payload = self.create_structured_payload(content, metadata)
        return self._save_memory(payload)
    
    def save_daily_work_memory(self, procedure: str, description: str, department: str, role: str):
        """日常業務記憶の保存"""
        content = f"日常業務手順：{procedure} - {description}"
        
        metadata = MemoryMetadata(
            category=MemoryCategory.DAILY_WORK,
            subcategory="procedures",
            importance=MemoryImportance.HIGH,
            tags=["procedure", "daily", "workflow", procedure.lower()],
            department=department,
            role=role,
            access_level=2
        )
        
        payload = self.create_structured_payload(content, metadata)
        return self._save_memory(payload)
    
    def save_project_memory(self, project_name: str, status: str, details: str, 
                          department: str, role: str):
        """プロジェクト記憶の保存"""
        content = f"プロジェクト記憶：{project_name}（{status}） - {details}"
        
        metadata = MemoryMetadata(
            category=MemoryCategory.PROJECT,
            subcategory=status,  # "ongoing" or "completed"
            importance=MemoryImportance.HIGH,
            tags=["project", status, project_name.lower().replace(" ", "_")],
            department=department,
            role=role,
            access_level=3,
            expiry_date=(datetime.now().replace(year=datetime.now().year + 1)).isoformat() if status == "completed" else None
        )
        
        payload = self.create_structured_payload(content, metadata)
        return self._save_memory(payload)
    
    def save_understanding_level(self, topic: str, level: str, evidence: str, 
                               department: str, role: str):
        """理解度記憶の保存"""
        content = f"理解度記録：{topic}について{level}レベルの理解。根拠：{evidence}"
        
        metadata = MemoryMetadata(
            category=MemoryCategory.UNDERSTANDING,
            subcategory="skill_level",
            importance=MemoryImportance.MEDIUM,
            tags=["understanding", "skill", level.lower(), topic.lower()],
            department=department,
            role=role,
            access_level=1,
            confidence=0.8  # 理解度は変動する可能性があるため信頼度を下げる
        )
        
        payload = self.create_structured_payload(content, metadata)
        return self._save_memory(payload)
    
    def save_interest_area(self, interest: str, intensity: str, context: str, 
                         department: str, role: str):
        """関心領域記憶の保存"""
        content = f"関心領域：{interest}に{intensity}の関心。背景：{context}"
        
        metadata = MemoryMetadata(
            category=MemoryCategory.INTEREST,
            subcategory="learning_preference",
            importance=MemoryImportance.MEDIUM,
            tags=["interest", "learning", intensity.lower(), interest.lower()],
            department=department,
            role=role,
            access_level=1
        )
        
        payload = self.create_structured_payload(content, metadata)
        return self._save_memory(payload)
    
    def search_by_category(self, category: MemoryCategory, limit: int = 10) -> List[Dict]:
        """カテゴリ別記憶検索"""
        try:
            payload = {
                "query": "",  # 空クエリで全記憶を対象
                "user_id": self.user_id,
                "limit": limit,
                "filters": {
                    "memory_category": category.value
                }
            }
            
            response = requests.post(f"{MEM0_API_BASE}/search", json=payload)
            
            if response.status_code == 200:
                return response.json().get('results', [])
            else:
                print(f"❌ カテゴリ検索失敗: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ カテゴリ検索エラー: {e}")
            return []
    
    def search_by_hierarchy_path(self, category: MemoryCategory, subcategory: str, 
                                limit: int = 10) -> List[Dict]:
        """階層パス指定での記憶検索"""
        try:
            payload = {
                "query": "",
                "user_id": self.user_id,
                "limit": limit,
                "filters": {
                    "memory_category": category.value,
                    "memory_subcategory": subcategory
                }
            }
            
            response = requests.post(f"{MEM0_API_BASE}/search", json=payload)
            
            if response.status_code == 200:
                return response.json().get('results', [])
            else:
                print(f"❌ 階層検索失敗: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 階層検索エラー: {e}")
            return []
    
    def search_by_importance(self, min_importance: MemoryImportance, 
                           limit: int = 10) -> List[Dict]:
        """重要度別記憶検索"""
        try:
            # mem0はフィルタの数値比較をサポートしていないため、
            # 各重要度レベルを個別に検索して結合
            all_results = []
            
            for importance in MemoryImportance:
                if importance.value >= min_importance.value:
                    payload = {
                        "query": "",
                        "user_id": self.user_id,
                        "limit": limit,
                        "filters": {
                            "memory_importance": importance.value
                        }
                    }
                    
                    response = requests.post(f"{MEM0_API_BASE}/search", json=payload)
                    
                    if response.status_code == 200:
                        results = response.json().get('results', [])
                        all_results.extend(results)
            
            # 重要度でソート
            all_results.sort(key=lambda x: x.get('memory_importance', 0), reverse=True)
            return all_results[:limit]
                
        except Exception as e:
            print(f"❌ 重要度検索エラー: {e}")
            return []
    
    def get_memory_hierarchy_summary(self) -> Dict:
        """記憶階層のサマリー取得"""
        summary = {
            "basic_info": [],
            "daily_work": [],
            "projects": {"ongoing": [], "completed": []},
            "understanding": [],
            "interests": []
        }
        
        # カテゴリ別に記憶を取得
        for category in MemoryCategory:
            memories = self.search_by_category(category, limit=50)
            
            if category == MemoryCategory.BASIC_INFO:
                summary["basic_info"] = memories
            elif category == MemoryCategory.DAILY_WORK:
                summary["daily_work"] = memories
            elif category == MemoryCategory.PROJECT:
                for memory in memories:
                    subcategory = memory.get('memory_subcategory', 'unknown')
                    if subcategory in summary["projects"]:
                        summary["projects"][subcategory].append(memory)
            elif category == MemoryCategory.UNDERSTANDING:
                summary["understanding"] = memories
            elif category == MemoryCategory.INTEREST:
                summary["interests"] = memories
        
        return summary
    
    def _save_memory(self, payload: Dict) -> Dict:
        """記憶保存の共通処理"""
        try:
            response = requests.post(f"{MEM0_API_BASE}/memories", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"💾 記憶保存成功: {len(result.get('results', []))}件")
                return result
            else:
                print(f"❌ 記憶保存失敗: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ 記憶保存エラー: {e}")
            return {}

def demonstrate_hierarchical_memory():
    """階層型記憶システムのデモンストレーション"""
    print("🧠 階層型記憶システム - デモンストレーション")
    print("=" * 60)
    
    # 記憶管理システムの初期化
    memory_manager = HierarchicalMemoryManager("hierarchical_user_001")
    
    # 1. 基本情報の保存
    print("\n📋 1. 基本情報の保存")
    memory_manager.save_basic_info(
        name="田中太郎",
        department="経理",
        role="課長",
        specialties=["会計", "税務", "予算管理"]
    )
    
    # 2. 日常業務記憶の保存
    print("\n📅 2. 日常業務記憶の保存")
    memory_manager.save_daily_work_memory(
        procedure="経費申請承認",
        description="5万円以上の経費は課長承認が必要、10万円以上は部長承認も必要",
        department="経理",
        role="課長"
    )
    
    # 3. プロジェクト記憶の保存
    print("\n📊 3. プロジェクト記憶の保存")
    memory_manager.save_project_memory(
        project_name="決算システム更新",
        status="ongoing",
        details="来月末までにシステム移行完了予定、テスト段階",
        department="経理",
        role="課長"
    )
    
    memory_manager.save_project_memory(
        project_name="四半期予算見直し",
        status="completed",
        details="各部署の予算配分を最適化、10%コスト削減を達成",
        department="経理",
        role="課長"
    )
    
    # 4. 理解度記憶の保存
    print("\n🎓 4. 理解度記憶の保存")
    memory_manager.save_understanding_level(
        topic="新会計基準",
        level="中級",
        evidence="研修受講済み、実務での適用経験あり",
        department="経理",
        role="課長"
    )
    
    # 5. 関心領域記憶の保存
    print("\n💡 5. 関心領域記憶の保存")
    memory_manager.save_interest_area(
        interest="AI活用による業務効率化",
        intensity="高",
        context="チャットボット導入検討プロジェクトをリード",
        department="経理",
        role="課長"
    )
    
    # 6. 階層別検索のデモ
    print("\n🔍 6. 階層別検索のデモ")
    
    print("\n📋 基本情報の検索:")
    basic_memories = memory_manager.search_by_category(MemoryCategory.BASIC_INFO)
    for memory in basic_memories:
        print(f"  - {memory.get('memory', '')}")
    
    print("\n📊 進行中プロジェクトの検索:")
    ongoing_projects = memory_manager.search_by_hierarchy_path(
        MemoryCategory.PROJECT, "ongoing"
    )
    for memory in ongoing_projects:
        print(f"  - {memory.get('memory', '')}")
    
    print("\n🔥 高重要度記憶の検索:")
    important_memories = memory_manager.search_by_importance(MemoryImportance.HIGH)
    for memory in important_memories:
        importance = memory.get('memory_importance', 'unknown')
        print(f"  - [重要度:{importance}] {memory.get('memory', '')}")
    
    # 7. 記憶階層サマリーの表示
    print("\n📊 7. 記憶階層サマリー:")
    summary = memory_manager.get_memory_hierarchy_summary()
    
    print(f"  📋 基本情報: {len(summary['basic_info'])}件")
    print(f"  📅 日常業務: {len(summary['daily_work'])}件")
    print(f"  📊 進行中プロジェクト: {len(summary['projects']['ongoing'])}件")
    print(f"  ✅ 完了プロジェクト: {len(summary['projects']['completed'])}件")
    print(f"  🎓 理解度記録: {len(summary['understanding'])}件")
    print(f"  💡 関心領域: {len(summary['interests'])}件")
    
    print("\n✅ 階層型記憶システムのデモ完了!")

if __name__ == "__main__":
    demonstrate_hierarchical_memory()