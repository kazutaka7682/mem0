#!/usr/bin/env python3
"""
Memory Explorer - mem0長期記憶探索アプリ
クロスセッションでの記憶検索と長期記憶の確認

使用方法:
python memory_explorer.py

機能:
- 全ユーザーの記憶一覧表示
- 特定ユーザーの記憶検索
- クロスセッション記憶検索
- 記憶の詳細情報表示
- 記憶の時系列分析
"""

import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import re

# 設定
MEM0_API_BASE = "http://localhost:8888"

class MemoryExplorer:
    def __init__(self):
        self.known_users = set()
        
    def get_user_memories(self, user_id: str) -> List[Dict]:
        """特定ユーザーの全記憶を取得"""
        try:
            response = requests.get(f"{MEM0_API_BASE}/memories", params={"user_id": user_id})
            
            if response.status_code == 200:
                return response.json().get('results', [])
            else:
                print(f"❌ ユーザー記憶取得失敗: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ ユーザー記憶取得エラー: {e}")
            return []
    
    def search_memories(self, query: str, user_id: str = None, limit: int = 10) -> List[Dict]:
        """記憶検索（クロスセッション対応）"""
        try:
            payload = {"query": query, "limit": limit}
            if user_id:
                payload["user_id"] = user_id
            
            response = requests.post(f"{MEM0_API_BASE}/search", json=payload)
            
            if response.status_code == 200:
                return response.json().get('results', [])
            else:
                print(f"❌ 記憶検索失敗: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 記憶検索エラー: {e}")
            return []
    
    def discover_users(self) -> List[str]:
        """既存ユーザーを発見（記憶を持つユーザーを特定）"""
        print("🔍 既存ユーザーを発見中...")
        
        # 包括的なユーザーIDパターンをテスト
        potential_user_ids = [
            # 既知のテストユーザー
            "test_user_123", "demo_user_123", "chat_user_001",
            "rag_test_user", "interest_test_user", "rag_user_001",
            "interactive_test_user", "direct_test_user",
            
            # rag_chat_appのパターン
            "rag_user_002", "rag_user_003", "rag_user_004", "rag_user_005",
            
            # chat_appのパターン  
            "chat_user_002", "chat_user_003", "chat_demo",
            
            # 一般的なパターン
            "user1", "user2", "user3", "test_user", "demo_user",
            "default_user", "sample_user", "example_user",
            
            # 日本語関連
            "user_jp", "jp_user", "japanese_user", "test_jp",
            
            # 数字パターン
            "user001", "user002", "user003", "user100",
            
            # その他
            "admin", "guest", "anonymous", "temp_user", "new_user",
            "memory_test_user", "cross_session_user", "long_term_user"
        ]
        
        found_users = []
        checked_count = 0
        
        for user_id in potential_user_ids:
            checked_count += 1
            memories = self.get_user_memories(user_id)
            if memories:
                found_users.append(user_id)
                self.known_users.add(user_id)
                print(f"  ✅ {user_id}: {len(memories)}件の記憶")
            else:
                # 進行状況を表示（10件ごと）
                if checked_count % 10 == 0:
                    print(f"  ... {checked_count}/{len(potential_user_ids)} 確認済み")
        
        print(f"📊 {checked_count}個のパターンをチェック, {len(found_users)}人発見")
        return found_users
    
    def analyze_memory_timeline(self, memories: List[Dict]):
        """記憶の時系列分析"""
        if not memories:
            print("📊 分析対象の記憶がありません")
            return
        
        print("\n📊 記憶タイムライン分析:")
        print("=" * 60)
        
        # 日付ごとにグループ化
        by_date = defaultdict(list)
        
        for memory in memories:
            created_at = memory.get('created_at', '')
            if created_at:
                # ISO形式の日付から日付部分を抽出
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_key = dt.strftime('%Y-%m-%d')
                    by_date[date_key].append(memory)
                except:
                    by_date['不明'].append(memory)
        
        # 日付順でソート
        sorted_dates = sorted(by_date.keys())
        
        for date in sorted_dates:
            memories_on_date = by_date[date]
            print(f"\n📅 {date} ({len(memories_on_date)}件)")
            
            for i, memory in enumerate(memories_on_date, 1):
                created_at = memory.get('created_at', '')
                # 時刻のみ表示
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = '不明'
                
                print(f"  {i}. [{time_str}] {memory.get('memory', '')}")
    
    def analyze_memory_categories(self, memories: List[Dict]):
        """記憶のカテゴリ分析"""
        print("\n🏷️ 記憶カテゴリ分析:")
        print("=" * 60)
        
        categories = {
            "個人情報": ["名前", "職業", "部署", "専門", "得意"],
            "趣味・嗜好": ["好き", "趣味", "興味"],
            "業務関連": ["業務", "仕事", "代理店", "経費", "契約", "申請"],
            "スキル・能力": ["Excel", "Python", "プログラミング", "分析"],
            "その他": []
        }
        
        categorized = defaultdict(list)
        
        for memory in memories:
            memory_text = memory.get('memory', '')
            assigned = False
            
            for category, keywords in categories.items():
                if category == "その他":
                    continue
                    
                for keyword in keywords:
                    if keyword in memory_text:
                        categorized[category].append(memory)
                        assigned = True
                        break
                
                if assigned:
                    break
            
            if not assigned:
                categorized["その他"].append(memory)
        
        for category, memories_in_cat in categorized.items():
            if memories_in_cat:
                print(f"\n📂 {category} ({len(memories_in_cat)}件)")
                for memory in memories_in_cat:
                    print(f"  - {memory.get('memory', '')}")
    
    def test_cross_session_search(self, user_id: str):
        """クロスセッション検索のテスト"""
        print(f"\n🔄 クロスセッション検索テスト: {user_id}")
        print("=" * 60)
        
        # 一般的な検索クエリ
        test_queries = [
            "名前", "職業", "趣味", "好き", "得意", "専門",
            "代理店", "経費", "契約", "Excel", "Python"
        ]
        
        found_results = {}
        
        for query in test_queries:
            results = self.search_memories(query, user_id, limit=5)
            if results:
                found_results[query] = results
        
        if found_results:
            print("🎯 検索結果:")
            for query, results in found_results.items():
                print(f"\n「{query}」の検索結果 ({len(results)}件):")
                for i, result in enumerate(results, 1):
                    score = result.get('score', 0)
                    memory = result.get('memory', '')
                    print(f"  {i}. [関連度: {score:.3f}] {memory}")
        else:
            print("❌ 検索結果なし")
    
    def compare_users(self, user_ids: List[str]):
        """複数ユーザーの記憶比較"""
        print("\n👥 ユーザー記憶比較:")
        print("=" * 60)
        
        user_memories = {}
        
        for user_id in user_ids:
            memories = self.get_user_memories(user_id)
            user_memories[user_id] = memories
        
        # 統計情報
        print("📈 統計情報:")
        for user_id, memories in user_memories.items():
            print(f"  {user_id}: {len(memories)}件の記憶")
        
        # 共通のトピック分析
        print("\n🔍 共通トピック分析:")
        topics = ["名前", "職業", "趣味", "代理店", "経費", "Excel", "Python"]
        
        for topic in topics:
            print(f"\n「{topic}」に関する記憶:")
            for user_id in user_ids:
                topic_memories = [m for m in user_memories[user_id] if topic in m.get('memory', '')]
                if topic_memories:
                    print(f"  📌 {user_id}:")
                    for memory in topic_memories:
                        print(f"    - {memory.get('memory', '')}")
                else:
                    print(f"  ⭕ {user_id}: 該当なし")
    
    def interactive_search(self):
        """インタラクティブ検索モード"""
        print("\n🔍 インタラクティブ検索モード")
        print("=" * 60)
        print("特別コマンド:")
        print("  /users - ユーザー一覧")
        print("  /back - メインメニューに戻る")
        print("=" * 60)
        
        while True:
            try:
                query = input("\n🔍 検索クエリ: ").strip()
                
                if not query:
                    continue
                    
                if query == "/back":
                    break
                elif query == "/users":
                    self.show_users_summary()
                    continue
                
                # ユーザー指定の確認
                user_choice = input("👤 特定ユーザーID (Enterで全ユーザー検索): ").strip()
                user_id = user_choice if user_choice else None
                
                # 検索実行
                print(f"\n🔍 検索中: 「{query}」" + (f" (ユーザー: {user_id})" if user_id else " (全ユーザー)"))
                
                results = self.search_memories(query, user_id, limit=10)
                
                if results:
                    print(f"\n📋 検索結果 ({len(results)}件):")
                    for i, result in enumerate(results, 1):
                        score = result.get('score', 0)
                        memory = result.get('memory', '')
                        memory_id = result.get('id', '')
                        created_at = result.get('created_at', '')
                        
                        print(f"\n{i}. [関連度: {score:.3f}]")
                        print(f"   💭 {memory}")
                        print(f"   🆔 ID: {memory_id}")
                        print(f"   📅 作成: {created_at}")
                else:
                    print("❌ 検索結果なし")
                    
            except KeyboardInterrupt:
                print("\n検索モードを終了します")
                break
    
    def show_users_summary(self):
        """ユーザー概要表示"""
        print("\n👥 ユーザー概要:")
        print("=" * 40)
        
        if not self.known_users:
            found_users = self.discover_users()
        
        for user_id in self.known_users:
            memories = self.get_user_memories(user_id)
            print(f"📱 {user_id}: {len(memories)}件")
            
            # 最新の記憶を1件表示
            if memories:
                latest = memories[0]  # 最新
                memory_text = latest.get('memory', '')
                if len(memory_text) > 50:
                    memory_text = memory_text[:50] + "..."
                print(f"    最新: {memory_text}")
    
    def run(self):
        """メイン実行ループ"""
        print("🧠 Memory Explorer - mem0長期記憶探索システム")
        print("=" * 60)
        
        while True:
            print("\n📋 メニュー:")
            print("1. ユーザー発見")
            print("2. ユーザー記憶詳細表示")
            print("3. クロスセッション検索テスト") 
            print("4. ユーザー記憶比較")
            print("5. インタラクティブ検索")
            print("6. 記憶統計情報")
            print("9. 終了")
            
            choice = input("\n選択 (1-9): ").strip()
            
            try:
                if choice == "1":
                    self.discover_users()
                    
                elif choice == "2":
                    if not self.known_users:
                        print("⚠️ 先にユーザー発見を実行してください")
                        continue
                        
                    print("\n利用可能ユーザー:")
                    for i, user_id in enumerate(sorted(self.known_users), 1):
                        print(f"{i}. {user_id}")
                    
                    user_choice = input("ユーザー番号またはID: ").strip()
                    
                    # 番号またはIDで選択
                    if user_choice.isdigit():
                        user_list = sorted(self.known_users)
                        idx = int(user_choice) - 1
                        if 0 <= idx < len(user_list):
                            selected_user = user_list[idx]
                        else:
                            print("❌ 無効な番号")
                            continue
                    else:
                        selected_user = user_choice
                    
                    memories = self.get_user_memories(selected_user)
                    if memories:
                        print(f"\n📚 {selected_user}の記憶 ({len(memories)}件):")
                        self.analyze_memory_timeline(memories)
                        self.analyze_memory_categories(memories)
                    else:
                        print(f"❌ {selected_user}の記憶が見つかりません")
                
                elif choice == "3":
                    if not self.known_users:
                        print("⚠️ 先にユーザー発見を実行してください")
                        continue
                    
                    user_id = input("テスト対象ユーザーID: ").strip()
                    if user_id:
                        self.test_cross_session_search(user_id)
                    else:
                        print("❌ ユーザーIDが必要です")
                
                elif choice == "4":
                    if not self.known_users:
                        print("⚠️ 先にユーザー発見を実行してください")
                        continue
                    
                    print("比較するユーザーID（スペース区切り）:")
                    user_input = input().strip()
                    user_ids = user_input.split()
                    
                    if len(user_ids) >= 2:
                        self.compare_users(user_ids)
                    else:
                        print("❌ 2つ以上のユーザーIDが必要です")
                
                elif choice == "5":
                    self.interactive_search()
                
                elif choice == "6":
                    if not self.known_users:
                        self.discover_users()
                    
                    total_memories = 0
                    total_users = len(self.known_users)
                    
                    print(f"\n📊 記憶統計情報:")
                    print(f"総ユーザー数: {total_users}")
                    
                    for user_id in self.known_users:
                        memories = self.get_user_memories(user_id)
                        total_memories += len(memories)
                    
                    print(f"総記憶数: {total_memories}")
                    print(f"平均記憶数: {total_memories/total_users if total_users > 0 else 0:.1f}")
                
                elif choice == "9":
                    print("👋 Memory Explorerを終了します")
                    break
                    
                else:
                    print("❌ 無効な選択です")
                    
            except KeyboardInterrupt:
                print("\n操作を中断しました")
            except Exception as e:
                print(f"❌ エラーが発生しました: {e}")

def main():
    """エントリーポイント"""
    try:
        # mem0サーバー接続確認
        response = requests.get(f"{MEM0_API_BASE}/memories", params={"user_id": "connection_test"})
        if response.status_code in [200, 404]:  # 404も正常（ユーザーが存在しないだけ）
            print("✅ mem0サーバー接続確認完了")
        else:
            print(f"⚠️ mem0サーバー応答異常: {response.status_code}")
    except Exception as e:
        print(f"❌ mem0サーバー接続失敗: {e}")
        print("mem0サーバーが起動していることを確認してください")
        return
    
    explorer = MemoryExplorer()
    explorer.run()

if __name__ == "__main__":
    main()