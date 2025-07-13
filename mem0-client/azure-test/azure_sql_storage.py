#!/usr/bin/env python3
"""
Azure SQL Server用のカスタムストレージ実装
mem0のSQLiteManagerをAzure SQL Serverに置き換え
"""
import logging
import threading
import uuid
import pyodbc
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AzureSQLManager:
    """Azure SQL Server用の履歴管理クラス"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._lock = threading.Lock()
        self._create_history_table()
    
    def _get_connection(self):
        """Azure SQL Server接続を取得"""
        return pyodbc.connect(self.connection_string)
    
    def _create_history_table(self) -> None:
        """履歴テーブルの作成"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # テーブル存在確認
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = 'mem0_history'
                """)
                
                if cursor.fetchone()[0] == 0:
                    # テーブル作成
                    cursor.execute("""
                        CREATE TABLE mem0_history (
                            id           NVARCHAR(255) PRIMARY KEY,
                            memory_id    NVARCHAR(255),
                            old_memory   NVARCHAR(MAX),
                            new_memory   NVARCHAR(MAX),
                            event        NVARCHAR(50),
                            created_at   DATETIME2,
                            updated_at   DATETIME2,
                            is_deleted   INT,
                            actor_id     NVARCHAR(255),
                            role         NVARCHAR(50)
                        )
                    """)
                    
                    # インデックス作成
                    cursor.execute("""
                        CREATE INDEX IX_mem0_history_memory_id ON mem0_history(memory_id)
                    """)
                    cursor.execute("""
                        CREATE INDEX IX_mem0_history_created_at ON mem0_history(created_at)
                    """)
                    
                    conn.commit()
                    logger.info("Azure SQL Server履歴テーブルを作成しました")
                
                conn.close()
                
            except Exception as e:
                logger.error(f"履歴テーブル作成エラー: {e}")
                raise
    
    def add(
        self,
        memory_id: str,
        old_memory: Optional[str] = None,
        new_memory: Optional[str] = None,
        event: Optional[str] = None,
        actor_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> str:
        """履歴エントリを追加"""
        with self._lock:
            try:
                history_id = str(uuid.uuid4())
                now = datetime.now()
                
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO mem0_history 
                    (id, memory_id, old_memory, new_memory, event, created_at, updated_at, is_deleted, actor_id, role)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    history_id, memory_id, old_memory, new_memory, event,
                    now, now, 0, actor_id, role
                ))
                
                conn.commit()
                conn.close()
                
                logger.debug(f"履歴追加: {event} - {memory_id}")
                return history_id
                
            except Exception as e:
                logger.error(f"履歴追加エラー: {e}")
                raise
    
    def get_history(
        self,
        memory_id: Optional[str] = None,
        limit: int = 100,
        actor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """履歴を取得"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = "SELECT * FROM mem0_history WHERE is_deleted = 0"
            params = []
            
            if memory_id:
                query += " AND memory_id = ?"
                params.append(memory_id)
            
            if actor_id:
                query += " AND actor_id = ?"
                params.append(actor_id)
            
            if limit:
                # SQL ServerではTOPを使う場合、ORDER BYは外側に
                query = f"SELECT TOP {limit} * FROM mem0_history WHERE is_deleted = 0"
                if memory_id:
                    query += " AND memory_id = ?"
                if actor_id:
                    query += " AND actor_id = ?"
                query += " ORDER BY created_at DESC"
            else:
                query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            columns = [column[0] for column in cursor.description]
            
            results = []
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                # datetime型を文字列に変換
                if result['created_at']:
                    result['created_at'] = result['created_at'].isoformat()
                if result['updated_at']:
                    result['updated_at'] = result['updated_at'].isoformat()
                results.append(result)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"履歴取得エラー: {e}")
            return []
    
    def delete_history(self, memory_id: str) -> bool:
        """履歴を論理削除"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE mem0_history 
                    SET is_deleted = 1, updated_at = ? 
                    WHERE memory_id = ?
                """, (datetime.now(), memory_id))
                
                rows_affected = cursor.rowcount
                conn.commit()
                conn.close()
                
                logger.debug(f"履歴削除: {memory_id} ({rows_affected}件)")
                return rows_affected > 0
                
            except Exception as e:
                logger.error(f"履歴削除エラー: {e}")
                return False
    
    def delete_all_history(self, actor_id: Optional[str] = None) -> int:
        """全履歴を論理削除"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                if actor_id:
                    cursor.execute("""
                        UPDATE mem0_history 
                        SET is_deleted = 1, updated_at = ? 
                        WHERE actor_id = ? AND is_deleted = 0
                    """, (datetime.now(), actor_id))
                else:
                    cursor.execute("""
                        UPDATE mem0_history 
                        SET is_deleted = 1, updated_at = ? 
                        WHERE is_deleted = 0
                    """, (datetime.now(),))
                
                rows_affected = cursor.rowcount
                conn.commit()
                conn.close()
                
                logger.debug(f"全履歴削除: {rows_affected}件")
                return rows_affected
                
            except Exception as e:
                logger.error(f"全履歴削除エラー: {e}")
                return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 総履歴数
            cursor.execute("SELECT COUNT(*) FROM mem0_history WHERE is_deleted = 0")
            total_count = cursor.fetchone()[0]
            
            # イベント別集計
            cursor.execute("""
                SELECT event, COUNT(*) as count 
                FROM mem0_history 
                WHERE is_deleted = 0 
                GROUP BY event
            """)
            event_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 最新の履歴
            cursor.execute("""
                SELECT TOP 1 created_at 
                FROM mem0_history 
                WHERE is_deleted = 0 
                ORDER BY created_at DESC
            """)
            latest_row = cursor.fetchone()
            latest_history = latest_row[0].isoformat() if latest_row else None
            
            conn.close()
            
            return {
                "total_count": total_count,
                "event_stats": event_stats,
                "latest_history": latest_history
            }
            
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
            return {}


def create_azure_sql_storage(connection_string: str) -> AzureSQLManager:
    """Azure SQL Server履歴管理インスタンスを作成"""
    return AzureSQLManager(connection_string)