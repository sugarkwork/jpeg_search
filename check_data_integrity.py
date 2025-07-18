import sqlite3
import os
from collections import Counter

def check_data_integrity(db_path="image_search.db"):
    """データベースの整合性をチェック"""
    print("データベース整合性チェックを開始...")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    issues_found = False
    
    try:
        # 1. 基本統計情報
        print("\n【基本統計情報】")
        cursor.execute("SELECT COUNT(*) FROM images")
        image_count = cursor.fetchone()[0]
        print(f"画像数: {image_count:,}")
        
        cursor.execute("SELECT COUNT(*) FROM tags")
        tag_count = cursor.fetchone()[0]
        print(f"タグ数: {tag_count:,}")
        
        cursor.execute("SELECT COUNT(*) FROM image_tags")
        relation_count = cursor.fetchone()[0]
        print(f"画像-タグ関連数: {relation_count:,}")
        
        # 2. 孤立したタグの確認
        print("\n【孤立したタグの確認】")
        cursor.execute("""
            SELECT COUNT(*) FROM tags t
            WHERE NOT EXISTS (
                SELECT 1 FROM image_tags it
                WHERE it.tag_id = t.id
            )
        """)
        orphan_tags = cursor.fetchone()[0]
        if orphan_tags > 0:
            print(f"WARNING: 孤立したタグ: {orphan_tags}個")
            cursor.execute("""
                SELECT tag_name FROM tags t
                WHERE NOT EXISTS (
                    SELECT 1 FROM image_tags it
                    WHERE it.tag_id = t.id
                )
                LIMIT 10
            """)
            examples = cursor.fetchall()
            print(f"  例: {[row[0] for row in examples]}")
            issues_found = True
        else:
            print("OK: 孤立したタグなし")
        
        # 3. 存在しない画像ファイルの確認
        print("\n【存在しない画像ファイルの確認】")
        cursor.execute("SELECT id, filepath, filename FROM images")
        missing_files = []
        for image_id, filepath, filename in cursor.fetchall():
            if not os.path.exists(filepath):
                missing_files.append((image_id, filepath, filename))
        
        if missing_files:
            print(f"WARNING: 存在しないファイル: {len(missing_files)}個")
            for i, (image_id, filepath, filename) in enumerate(missing_files[:5]):
                print(f"  ID:{image_id} - {filename}")
            if len(missing_files) > 5:
                print(f"  ... 他 {len(missing_files) - 5}個")
            issues_found = True
        else:
            print("OK: すべてのファイルが存在")
        
        # 4. 画像-タグ関連の整合性確認
        print("\n【画像-タグ関連の整合性確認】")
        
        # 存在しない画像IDを参照
        cursor.execute("""
            SELECT COUNT(*) FROM image_tags it
            WHERE NOT EXISTS (
                SELECT 1 FROM images i
                WHERE i.id = it.image_id
            )
        """)
        invalid_image_refs = cursor.fetchone()[0]
        if invalid_image_refs > 0:
            print(f"WARNING: 存在しない画像を参照: {invalid_image_refs}個")
            issues_found = True
        else:
            print("OK: 画像参照OK")
        
        # 存在しないタグIDを参照
        cursor.execute("""
            SELECT COUNT(*) FROM image_tags it
            WHERE NOT EXISTS (
                SELECT 1 FROM tags t
                WHERE t.id = it.tag_id
            )
        """)
        invalid_tag_refs = cursor.fetchone()[0]
        if invalid_tag_refs > 0:
            print(f"WARNING: 存在しないタグを参照: {invalid_tag_refs}個")
            issues_found = True
        else:
            print("OK: タグ参照OK")
        
        # 5. 重複データの確認
        print("\n【重複データの確認】")
        
        # 同じファイルパスの重複
        cursor.execute("""
            SELECT filepath, COUNT(*) as cnt
            FROM images
            GROUP BY filepath
            HAVING cnt > 1
        """)
        duplicate_paths = cursor.fetchall()
        if duplicate_paths:
            print(f"WARNING: 重複したファイルパス: {len(duplicate_paths)}個")
            for filepath, count in duplicate_paths[:5]:
                print(f"  {filepath}: {count}回")
            issues_found = True
        else:
            print("OK: ファイルパスの重複なし")
        
        # 6. タグ使用状況の分析
        print("\n【タグ使用状況】")
        cursor.execute("""
            SELECT COUNT(DISTINCT it.image_id) as image_count, COUNT(*) as tag_count
            FROM image_tags it
            GROUP BY it.tag_id
            ORDER BY image_count DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result:
            max_usage = result[0]
            print(f"最も使用されているタグ: {max_usage:,}枚の画像で使用")
        
        # 画像あたりのタグ数統計
        cursor.execute("""
            SELECT AVG(tag_count), MIN(tag_count), MAX(tag_count)
            FROM (
                SELECT COUNT(*) as tag_count
                FROM image_tags
                GROUP BY image_id
            )
        """)
        avg_tags, min_tags, max_tags = cursor.fetchone()
        if avg_tags:
            print(f"画像あたりのタグ数: 平均{avg_tags:.1f}, 最小{min_tags}, 最大{max_tags}")
        
        # タグのない画像
        cursor.execute("""
            SELECT COUNT(*) FROM images i
            WHERE NOT EXISTS (
                SELECT 1 FROM image_tags it
                WHERE it.image_id = i.id
            )
        """)
        no_tag_images = cursor.fetchone()[0]
        if no_tag_images > 0:
            print(f"WARNING: タグのない画像: {no_tag_images}枚")
            issues_found = True
        else:
            print("OK: すべての画像にタグあり")
        
        # 7. インデックスの確認
        print("\n【インデックスの確認】")
        cursor.execute("""
            SELECT name, tbl_name 
            FROM sqlite_master 
            WHERE type = 'index' AND sql IS NOT NULL
            ORDER BY tbl_name, name
        """)
        indexes = cursor.fetchall()
        for idx_name, table_name in indexes:
            print(f"  {table_name}: {idx_name}")
        
        # 8. データベース整合性チェック
        print("\n【SQLite整合性チェック】")
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        if integrity_result == "ok":
            print("OK: データベース整合性OK")
        else:
            print(f"WARNING: 整合性エラー: {integrity_result}")
            issues_found = True
        
        # 結果サマリー
        print("\n" + "=" * 60)
        if issues_found:
            print("WARNING: いくつかの問題が見つかりました。上記の詳細を確認してください。")
        else:
            print("OK: データベースの整合性に問題は見つかりませんでした。")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    check_data_integrity()