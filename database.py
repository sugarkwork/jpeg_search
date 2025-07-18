# database.py (修正版)
import sqlite3
import os
import time
from typing import List, Tuple

class ImageDatabase:
    def __init__(self, db_path: str = "image_search.db"):
        self.db_path = db_path
        self.init_database()
        self.optimize_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """データベースとテーブルを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 画像テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # タグテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT NOT NULL UNIQUE
        )
        ''')
        
        # 画像-タグ関連テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            tag_id INTEGER,
            confidence REAL DEFAULT 1.0,
            FOREIGN KEY (image_id) REFERENCES images (id),
            FOREIGN KEY (tag_id) REFERENCES tags (id),
            UNIQUE(image_id, tag_id)
        )
        ''')
        
        # 既存のインデックスを削除（再構築のため）
        cursor.execute('DROP INDEX IF EXISTS idx_tags_tag_name')
        cursor.execute('DROP INDEX IF EXISTS idx_image_tags_image_id')
        cursor.execute('DROP INDEX IF EXISTS idx_image_tags_tag_id')
        cursor.execute('DROP INDEX IF EXISTS idx_image_tags_image_tag')
        
        # 最適化されたインデックスの作成
        # tag_nameの検索を高速化（UNIQUE制約で自動的にインデックスが作成されるため、追加のインデックスは不要）
        # tags.tag_nameには既にUNIQUE制約があるため、これで十分
        
        # tag_id → image_id の順で検索するカバーリングインデックス
        # JOINとグループ化の両方で使用される
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_it_tagid_imageid 
        ON image_tags(tag_id, image_id)
        ''')
        
        # NOT EXISTS句でimage_idだけを探す場合に使用
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_it_imageid 
        ON image_tags(image_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def optimize_database(self):
        """データベースの最適化を実行"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            print("データベースの最適化を開始...")
            
            # 統計情報を更新
            cursor.execute('ANALYZE')
            
            # SQLiteの最適化を実行
            cursor.execute('PRAGMA optimize')
            
            conn.commit()
            print("データベースの最適化が完了しました")
            
        except Exception as e:
            print(f"データベース最適化中にエラーが発生しました: {e}")
        finally:
            conn.close()
    
    def add_image_with_tags(self, filepath: str, tags: List[str]):
        """画像とそのタグをデータベースに追加"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 画像を追加
            filename = os.path.basename(filepath)
            cursor.execute('INSERT OR IGNORE INTO images (filepath, filename) VALUES (?, ?)', 
                         (filepath, filename))
            
            # 画像IDを取得
            cursor.execute('SELECT id FROM images WHERE filepath = ?', (filepath,))
            result = cursor.fetchone()
            if not result:
                # 新しく挿入された場合のID取得
                image_id = cursor.lastrowid
            else:
                image_id = result[0]
            
            # タグを追加（小文字に統一）
            for tag in tags:
                tag_lower = tag.lower().strip()
                if not tag_lower:
                    continue
                    
                # タグを追加（存在しない場合）
                cursor.execute('INSERT OR IGNORE INTO tags (tag_name) VALUES (?)', (tag_lower,))
                
                # タグIDを取得
                cursor.execute('SELECT id FROM tags WHERE tag_name = ?', (tag_lower,))
                tag_result = cursor.fetchone()
                if tag_result:
                    tag_id = tag_result[0]
                    
                    # 画像-タグ関連を追加
                    cursor.execute('INSERT OR IGNORE INTO image_tags (image_id, tag_id) VALUES (?, ?)', 
                                 (image_id, tag_id))
            
            conn.commit()
            print(f"Added image {filename} with {len(tags)} tags")
            return image_id
            
        except Exception as e:
            conn.rollback()
            print(f"Error adding image {filepath}: {e}")
            raise e
        finally:
            conn.close()
    
    def get_all_image_filenames(self):
        """画像ファイル名を取得（デバッグ用）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT filename FROM images')
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results
    
    def search_images(self, positive_tags: List[str], negative_tags: List[str] = None, limit: int = 50):
        """タグで画像を検索（デバッグ機能付き）"""
        search_start_time = time.time()
        
        if negative_tags is None:
            negative_tags = []
            
        # タグを小文字に統一
        tag_normalize_start = time.time()
        positive_tags = [tag.lower().strip() for tag in positive_tags if tag.strip()]
        negative_tags = [tag.lower().strip() for tag in negative_tags if tag.strip()]
        tag_normalize_time = time.time() - tag_normalize_start
        
        print(f"Searching for positive tags: {positive_tags}")
        print(f"Excluding negative tags: {negative_tags}")
        print(f"タグ正規化時間: {tag_normalize_time:.4f}秒")
        
        # データベース接続時間を測定
        db_connect_start = time.time()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        db_connect_time = time.time() - db_connect_start
        print(f"DB接続時間: {db_connect_time:.4f}秒")
        
        try:
            # 統計情報取得時間を測定
            stats_start = time.time()
            cursor.execute('SELECT COUNT(*) FROM images')
            total_images = cursor.fetchone()[0]
            print(f"Total images in database: {total_images}")
            
            cursor.execute('SELECT COUNT(*) FROM tags')
            total_tags = cursor.fetchone()[0]
            print(f"Total tags in database: {total_tags}")
            stats_time = time.time() - stats_start
            print(f"統計情報取得時間: {stats_time:.4f}秒")
            
            # タグ存在確認時間を測定
            tag_check_start = time.time()
            for tag in positive_tags:
                cursor.execute('SELECT COUNT(*) FROM tags WHERE tag_name = ?', (tag,))
                count = cursor.fetchone()[0]
                print(f"Tag '{tag}' found {count} times")
            tag_check_time = time.time() - tag_check_start
            print(f"タグ存在確認時間: {tag_check_time:.4f}秒")
            
            # クエリ構築時間を測定
            query_build_start = time.time()
            positive_placeholders = ','.join(['?' for _ in positive_tags])
            
            query = f'''
            SELECT i.id, i.filepath, i.filename, COUNT(it.tag_id) as match_count
            FROM images i
            JOIN image_tags it ON i.id = it.image_id
            JOIN tags t ON it.tag_id = t.id
            WHERE t.tag_name IN ({positive_placeholders})
            '''
            
            params = positive_tags.copy()
            
            # ネガティブタグがある場合
            if negative_tags:
                negative_placeholders = ','.join(['?' for _ in negative_tags])
                query += f'''
                AND NOT EXISTS (
                    SELECT 1 FROM image_tags it2
                    JOIN tags t2 ON it2.tag_id = t2.id
                    WHERE it2.image_id = i.id
                    AND t2.tag_name IN ({negative_placeholders})
                )
                '''
                params.extend(negative_tags)
            
            query += '''
            GROUP BY i.id, i.filepath, i.filename
            ORDER BY match_count DESC, i.id DESC
            LIMIT ?
            '''
            params.append(limit)
            query_build_time = time.time() - query_build_start
            print(f"クエリ構築時間: {query_build_time:.4f}秒")
            
            print(f"Executing query: {query}")
            print(f"With parameters: {params}")
            
            # SQLクエリ実行時間を測定
            sql_execute_start = time.time()
            cursor.execute(query, params)
            results = cursor.fetchall()
            sql_execute_time = time.time() - sql_execute_start
            
            # 全体の検索時間を計算
            total_search_time = time.time() - search_start_time
            
            print(f"SQLクエリ実行時間: {sql_execute_time:.4f}秒")
            print(f"Search returned {len(results)} results")
            print(f"データベース検索全体時間: {total_search_time:.4f}秒")
            print(f"DB検索時間内訳 - タグ正規化: {tag_normalize_time:.4f}秒, DB接続: {db_connect_time:.4f}秒, 統計取得: {stats_time:.4f}秒, タグ確認: {tag_check_time:.4f}秒, クエリ構築: {query_build_time:.4f}秒, SQL実行: {sql_execute_time:.4f}秒")
            
            for result in results[:3]:  # 最初の3件をログ出力
                print(f"Result: {result}")
            
            return results
            
        except Exception as e:
            print(f"Search error: {e}")
            raise e
        finally:
            conn.close()
    
    def get_all_tags(self):
        """全タグを取得（デバッグ用）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT tag_name, COUNT(it.image_id) FROM tags t LEFT JOIN image_tags it ON t.id = it.tag_id GROUP BY t.tag_name ORDER BY COUNT(it.image_id) DESC')
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_image_tags(self, image_id: int):
        """特定の画像のタグを取得（デバッグ用）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.tag_name
            FROM tags t
            JOIN image_tags it ON t.id = it.tag_id
            WHERE it.image_id = ?
        ''', (image_id,))
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_image_tags_with_confidence(self, image_id: int):
        """特定の画像のタグを信頼度付きで取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.tag_name, it.confidence
            FROM tags t
            JOIN image_tags it ON t.id = it.tag_id
            WHERE it.image_id = ?
            ORDER BY it.confidence DESC
        ''', (image_id,))
        results = [{'tag': row[0], 'confidence': row[1]} for row in cursor.fetchall()]
        conn.close()
        return results