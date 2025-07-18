#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース分割実装サンプル
解析結果に基づいて実際にデータベースを分割するためのコード
"""

import sqlite3
import os
import shutil
from database import ImageDatabase
from tqdm import tqdm

class DatabaseSplitter:
    def __init__(self, source_db="image_search.db"):
        self.source_db = source_db
        self.db = ImageDatabase(source_db)
    
    def create_split_databases(self, strategy="solo_multi"):
        """分割戦略に基づいてデータベースを作成"""
        print(f"🔄 データベース分割を開始します (戦略: {strategy})")
        
        if strategy == "solo_multi":
            self._split_solo_multi()
        elif strategy == "detailed":
            self._split_detailed()
        else:
            raise ValueError(f"未対応の戦略: {strategy}")
    
    def _split_solo_multi(self):
        """ソロ・複数人での2分割"""
        print("📊 ソロ・複数人分割を実行中...")
        
        # 分割用データベースを作成
        solo_db_path = "image_search_solo.db"
        multi_db_path = "image_search_multi.db"
        
        # 既存ファイルを削除
        for db_path in [solo_db_path, multi_db_path]:
            if os.path.exists(db_path):
                os.remove(db_path)
        
        # 新しいデータベースを初期化
        solo_db = ImageDatabase(solo_db_path)
        multi_db = ImageDatabase(multi_db_path)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # ソロ画像を取得
        print("🔍 ソロ画像を抽出中...")
        cursor.execute('''
            SELECT DISTINCT i.id, i.filepath, i.filename
            FROM images i
            JOIN image_tags it ON i.id = it.image_id
            JOIN tags t ON it.tag_id = t.id
            WHERE t.tag_name = 'solo'
        ''')
        solo_images = cursor.fetchall()
        
        # 全画像を取得
        cursor.execute('SELECT id, filepath, filename FROM images')
        all_images = cursor.fetchall()
        
        # ソロ画像のIDセットを作成
        solo_image_ids = {img[0] for img in solo_images}
        
        # 複数人画像を特定
        multi_images = [img for img in all_images if img[0] not in solo_image_ids]
        
        print(f"📈 分割統計:")
        print(f"  - ソロ画像: {len(solo_images):,}件")
        print(f"  - 複数人画像: {len(multi_images):,}件")
        
        # ソロ画像とタグをコピー
        print("💾 ソロデータベースを作成中...")
        self._copy_images_with_tags(solo_images, solo_db, conn)
        
        # 複数人画像とタグをコピー
        print("💾 複数人データベースを作成中...")
        self._copy_images_with_tags(multi_images, multi_db, conn)
        
        conn.close()
        
        print(f"✅ 分割完了!")
        print(f"  - ソロDB: {solo_db_path}")
        print(f"  - 複数人DB: {multi_db_path}")
    
    def _split_detailed(self):
        """詳細分割（女性ソロ、男性ソロ、カップル、その他）"""
        print("📊 詳細分割を実行中...")
        
        # 分割用データベースを作成
        db_paths = {
            'girl_solo': "image_search_girl_solo.db",
            'boy_solo': "image_search_boy_solo.db", 
            'couple': "image_search_couple.db",
            'others': "image_search_others.db"
        }
        
        # 既存ファイルを削除
        for db_path in db_paths.values():
            if os.path.exists(db_path):
                os.remove(db_path)
        
        # 新しいデータベースを初期化
        databases = {
            key: ImageDatabase(path) for key, path in db_paths.items()
        }
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # 各カテゴリの画像を取得
        categories = {}
        
        # 女性ソロ
        cursor.execute('''
            SELECT DISTINCT i.id, i.filepath, i.filename
            FROM images i
            JOIN image_tags it1 ON i.id = it1.image_id
            JOIN tags t1 ON it1.tag_id = t1.id
            JOIN image_tags it2 ON i.id = it2.image_id
            JOIN tags t2 ON it2.tag_id = t2.id
            WHERE t1.tag_name = '1girl' AND t2.tag_name = 'solo'
        ''')
        categories['girl_solo'] = cursor.fetchall()
        
        # 男性ソロ
        cursor.execute('''
            SELECT DISTINCT i.id, i.filepath, i.filename
            FROM images i
            JOIN image_tags it1 ON i.id = it1.image_id
            JOIN tags t1 ON it1.tag_id = t1.id
            JOIN image_tags it2 ON i.id = it2.image_id
            JOIN tags t2 ON it2.tag_id = t2.id
            WHERE t1.tag_name = '1boy' AND t2.tag_name = 'solo'
        ''')
        categories['boy_solo'] = cursor.fetchall()
        
        # カップル
        cursor.execute('''
            SELECT DISTINCT i.id, i.filepath, i.filename
            FROM images i
            JOIN image_tags it1 ON i.id = it1.image_id
            JOIN tags t1 ON it1.tag_id = t1.id
            JOIN image_tags it2 ON i.id = it2.image_id
            JOIN tags t2 ON it2.tag_id = t2.id
            WHERE t1.tag_name = '1boy' AND t2.tag_name = '1girl'
        ''')
        categories['couple'] = cursor.fetchall()
        
        # 全画像を取得
        cursor.execute('SELECT id, filepath, filename FROM images')
        all_images = cursor.fetchall()
        
        # 既に分類された画像のIDセット
        classified_ids = set()
        for images in categories.values():
            classified_ids.update(img[0] for img in images)
        
        # その他の画像
        categories['others'] = [img for img in all_images if img[0] not in classified_ids]
        
        print(f"📈 詳細分割統計:")
        for category, images in categories.items():
            print(f"  - {category}: {len(images):,}件")
        
        # 各カテゴリのデータベースを作成
        for category, images in categories.items():
            print(f"💾 {category}データベースを作成中...")
            self._copy_images_with_tags(images, databases[category], conn)
        
        conn.close()
        
        print(f"✅ 詳細分割完了!")
        for category, path in db_paths.items():
            print(f"  - {category}DB: {path}")
    
    def _copy_images_with_tags(self, images, target_db, source_conn):
        """画像とそのタグを対象データベースにコピー"""
        source_cursor = source_conn.cursor()
        
        for image_id, filepath, filename in tqdm(images, desc="画像をコピー中"):
            # 画像のタグを取得
            source_cursor.execute('''
                SELECT t.tag_name
                FROM tags t
                JOIN image_tags it ON t.id = it.tag_id
                WHERE it.image_id = ?
            ''', (image_id,))
            
            tags = [row[0] for row in source_cursor.fetchall()]
            
            # 対象データベースに追加
            try:
                target_db.add_image_with_tags(filepath, tags)
            except Exception as e:
                print(f"⚠️  画像追加エラー {filepath}: {e}")
    
    def create_router_logic(self):
        """分割されたデータベースを使用するためのルーターロジックを生成"""
        router_code = '''
# database_router.py
"""
分割されたデータベースへのルーティングロジック
"""

from database import ImageDatabase

class DatabaseRouter:
    def __init__(self):
        self.solo_db = ImageDatabase("image_search_solo.db")
        self.multi_db = ImageDatabase("image_search_multi.db")
    
    def search_images(self, positive_tags, negative_tags=None, limit=50):
        """適切なデータベースを選択して検索"""
        positive_tags_set = set(tag.lower() for tag in positive_tags)
        
        # ソロタグが含まれている場合
        if 'solo' in positive_tags_set:
            print("🎯 ソロデータベースで検索")
            return self.solo_db.search_images(positive_tags, negative_tags, limit)
        
        # 複数人を示すタグが含まれている場合
        multi_tags = {'2girls', '3girls', '4girls', '5girls', 'multiple_girls',
                     '2boys', '3boys', '4boys', '5boys', 'multiple_boys'}
        
        if positive_tags_set.intersection(multi_tags):
            print("🎯 複数人データベースで検索")
            return self.multi_db.search_images(positive_tags, negative_tags, limit)
        
        # 判断できない場合は両方を検索してマージ
        print("🎯 両方のデータベースで検索")
        solo_results = self.solo_db.search_images(positive_tags, negative_tags, limit//2)
        multi_results = self.multi_db.search_images(positive_tags, negative_tags, limit//2)
        
        # 結果をマージしてソート
        all_results = list(solo_results) + list(multi_results)
        all_results.sort(key=lambda x: x[3], reverse=True)  # match_countでソート
        
        return all_results[:limit]

# 使用例
if __name__ == "__main__":
    router = DatabaseRouter()
    
    # ソロ検索
    results = router.search_images(['1girl', 'solo'])
    print(f"ソロ検索結果: {len(results)}件")
    
    # 複数人検索
    results = router.search_images(['2girls'])
    print(f"複数人検索結果: {len(results)}件")
'''
        
        with open('database_router.py', 'w', encoding='utf-8') as f:
            f.write(router_code)
        
        print("📝 database_router.py を作成しました")

def main():
    """メイン実行関数"""
    print("🔧 データベース分割ツール")
    print("="*50)
    
    try:
        splitter = DatabaseSplitter()
        
        print("分割戦略を選択してください:")
        print("1. ソロ・複数人分割 (推奨)")
        print("2. 詳細分割 (女性ソロ、男性ソロ、カップル、その他)")
        print("3. ルーターロジックのみ生成")
        
        choice = input("選択 (1-3): ").strip()
        
        if choice == "1":
            splitter.create_split_databases("solo_multi")
            splitter.create_router_logic()
        elif choice == "2":
            splitter.create_split_databases("detailed")
        elif choice == "3":
            splitter.create_router_logic()
        else:
            print("❌ 無効な選択です")
            return
        
        print("\n✅ 処理完了!")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()