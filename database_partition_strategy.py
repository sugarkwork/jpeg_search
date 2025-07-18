#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース分割戦略の詳細提案
解析結果に基づいて具体的な分割方法を提案する
"""

import sqlite3
from collections import defaultdict
from database import ImageDatabase
import json

class PartitionStrategy:
    def __init__(self, db_path="image_search.db"):
        self.db_path = db_path
        self.db = ImageDatabase(db_path)
    
    def analyze_search_patterns(self):
        """検索パターンを分析して最適な分割戦略を提案"""
        print("🔍 検索パターン分析による分割戦略")
        print("="*60)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute('SELECT COUNT(*) FROM images')
        total_images = cursor.fetchone()[0]
        
        # ソロ画像の分析
        cursor.execute('''
            SELECT COUNT(DISTINCT i.id)
            FROM images i
            JOIN image_tags it ON i.id = it.image_id
            JOIN tags t ON it.tag_id = t.id
            WHERE t.tag_name = 'solo'
        ''')
        solo_images = cursor.fetchone()[0]
        
        # 1girl + soloの組み合わせ
        cursor.execute('''
            SELECT COUNT(DISTINCT i.id)
            FROM images i
            JOIN image_tags it1 ON i.id = it1.image_id
            JOIN tags t1 ON it1.tag_id = t1.id
            JOIN image_tags it2 ON i.id = it2.image_id
            JOIN tags t2 ON it2.tag_id = t2.id
            WHERE t1.tag_name = '1girl' AND t2.tag_name = 'solo'
        ''')
        girl_solo_images = cursor.fetchone()[0]
        
        # 1boy + soloの組み合わせ
        cursor.execute('''
            SELECT COUNT(DISTINCT i.id)
            FROM images i
            JOIN image_tags it1 ON i.id = it1.image_id
            JOIN tags t1 ON it1.tag_id = t1.id
            JOIN image_tags it2 ON i.id = it2.image_id
            JOIN tags t2 ON it2.tag_id = t2.id
            WHERE t1.tag_name = '1boy' AND t2.tag_name = 'solo'
        ''')
        boy_solo_images = cursor.fetchone()[0]
        
        # 1boy + 1girlの組み合わせ
        cursor.execute('''
            SELECT COUNT(DISTINCT i.id)
            FROM images i
            JOIN image_tags it1 ON i.id = it1.image_id
            JOIN tags t1 ON it1.tag_id = t1.id
            JOIN image_tags it2 ON i.id = it2.image_id
            JOIN tags t2 ON it2.tag_id = t2.id
            WHERE t1.tag_name = '1boy' AND t2.tag_name = '1girl'
        ''')
        boy_girl_images = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"📊 主要パターン分析:")
        print(f"  - 総画像数: {total_images:,}件")
        print(f"  - ソロ画像: {solo_images:,}件 ({solo_images/total_images*100:.1f}%)")
        print(f"  - 女性ソロ: {girl_solo_images:,}件 ({girl_solo_images/total_images*100:.1f}%)")
        print(f"  - 男性ソロ: {boy_solo_images:,}件 ({boy_solo_images/total_images*100:.1f}%)")
        print(f"  - カップル(1boy+1girl): {boy_girl_images:,}件 ({boy_girl_images/total_images*100:.1f}%)")
        
        return {
            'total_images': total_images,
            'solo_images': solo_images,
            'girl_solo_images': girl_solo_images,
            'boy_solo_images': boy_solo_images,
            'boy_girl_images': boy_girl_images
        }
    
    def propose_partition_strategies(self, stats):
        """具体的な分割戦略を提案"""
        total = stats['total_images']
        
        print(f"\n💡 推奨分割戦略:")
        
        # 戦略1: ソロ vs 複数人
        solo_db_size = stats['solo_images']
        multi_db_size = total - solo_db_size
        
        print(f"\n🎯 戦略1: ソロ・複数人分割")
        print(f"  - ソロDB: {solo_db_size:,}件 ({solo_db_size/total*100:.1f}%)")
        print(f"  - 複数人DB: {multi_db_size:,}件 ({multi_db_size/total*100:.1f}%)")
        print(f"  - 検索時間改善: 最大{total/max(solo_db_size, multi_db_size):.1f}倍")
        
        # 戦略2: 3分割（女性ソロ、男性ソロ、その他）
        girl_solo = stats['girl_solo_images']
        boy_solo = stats['boy_solo_images']
        others = total - girl_solo - boy_solo
        
        print(f"\n🎯 戦略2: 性別ソロ・その他分割")
        print(f"  - 女性ソロDB: {girl_solo:,}件 ({girl_solo/total*100:.1f}%)")
        print(f"  - 男性ソロDB: {boy_solo:,}件 ({boy_solo/total*100:.1f}%)")
        print(f"  - その他DB: {others:,}件 ({others/total*100:.1f}%)")
        print(f"  - 検索時間改善: 最大{total/max(girl_solo, boy_solo, others):.1f}倍")
        
        # 戦略3: 4分割（女性ソロ、男性ソロ、カップル、その他）
        couple = stats['boy_girl_images']
        remaining = total - girl_solo - boy_solo - couple
        
        print(f"\n🎯 戦略3: 詳細分割")
        print(f"  - 女性ソロDB: {girl_solo:,}件 ({girl_solo/total*100:.1f}%)")
        print(f"  - 男性ソロDB: {boy_solo:,}件 ({boy_solo/total*100:.1f}%)")
        print(f"  - カップルDB: {couple:,}件 ({couple/total*100:.1f}%)")
        print(f"  - その他DB: {remaining:,}件 ({remaining/total*100:.1f}%)")
        print(f"  - 検索時間改善: 最大{total/max(girl_solo, boy_solo, couple, remaining):.1f}倍")
        
        return {
            'strategy1': {'solo': solo_db_size, 'multi': multi_db_size},
            'strategy2': {'girl_solo': girl_solo, 'boy_solo': boy_solo, 'others': others},
            'strategy3': {'girl_solo': girl_solo, 'boy_solo': boy_solo, 'couple': couple, 'others': remaining}
        }
    
    def analyze_tag_frequency_distribution(self):
        """タグ頻度分布を分析してインデックス戦略を提案"""
        print(f"\n📈 タグ頻度分布分析:")
        print("="*60)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # タグ使用頻度の分布
        cursor.execute('''
            SELECT t.tag_name, COUNT(it.image_id) as usage_count
            FROM tags t
            LEFT JOIN image_tags it ON t.id = it.tag_id
            GROUP BY t.tag_name
            ORDER BY usage_count DESC
            LIMIT 50
        ''')
        
        top_tags = cursor.fetchall()
        
        # 頻度別カテゴリ分析
        very_high = [tag for tag, count in top_tags if count > 100000]
        high = [tag for tag, count in top_tags if 10000 <= count <= 100000]
        medium = [tag for tag, count in top_tags if 1000 <= count < 10000]
        low = [tag for tag, count in top_tags if count < 1000]
        
        print(f"🏷️  タグ頻度カテゴリ:")
        print(f"  - 超高頻度 (10万件以上): {len(very_high)}個")
        for tag in very_high[:10]:
            print(f"    • {tag}")
        
        print(f"  - 高頻度 (1万-10万件): {len(high)}個")
        for tag in high[:5]:
            print(f"    • {tag}")
        
        print(f"  - 中頻度 (1千-1万件): {len(medium)}個")
        print(f"  - 低頻度 (1千件未満): {len(low)}個")
        
        conn.close()
        
        return {
            'very_high': very_high,
            'high': high,
            'medium': medium,
            'low': low
        }
    
    def generate_implementation_plan(self, partition_strategies, tag_analysis):
        """実装計画を生成"""
        print(f"\n🚀 実装計画:")
        print("="*60)
        
        print(f"📋 推奨実装順序:")
        
        print(f"\n1️⃣  Phase 1: ソロ・複数人分割")
        print(f"   - 最も効果的で実装が簡単")
        print(f"   - 検索クエリに 'solo' タグの有無で振り分け")
        print(f"   - 実装コスト: 低")
        print(f"   - 効果: 中〜高")
        
        print(f"\n2️⃣  Phase 2: インデックス最適化")
        print(f"   - 超高頻度タグ用の専用インデックス作成")
        print(f"   - 複合インデックス (image_id, tag_id) の最適化")
        print(f"   - 実装コスト: 低")
        print(f"   - 効果: 中")
        
        print(f"\n3️⃣  Phase 3: 詳細分割（必要に応じて）")
        print(f"   - 性別・人数による細分化")
        print(f"   - より複雑な振り分けロジック")
        print(f"   - 実装コスト: 高")
        print(f"   - 効果: 高")
        
        print(f"\n🔧 技術的実装方針:")
        print(f"   - データベースファイルの物理分割")
        print(f"   - アプリケーションレベルでの振り分けロジック")
        print(f"   - 検索クエリの前処理による最適DB選択")
        print(f"   - 結果のマージ処理（必要に応じて）")

def main():
    """メイン実行関数"""
    print("🎯 データベース分割戦略詳細分析")
    print("="*80)
    
    try:
        strategy = PartitionStrategy()
        
        # 検索パターン分析
        stats = strategy.analyze_search_patterns()
        
        # 分割戦略提案
        partition_strategies = strategy.propose_partition_strategies(stats)
        
        # タグ頻度分析
        tag_analysis = strategy.analyze_tag_frequency_distribution()
        
        # 実装計画生成
        strategy.generate_implementation_plan(partition_strategies, tag_analysis)
        
        # 結果保存
        result = {
            'stats': stats,
            'partition_strategies': partition_strategies,
            'tag_analysis': tag_analysis
        }
        
        with open('partition_strategy.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 詳細分析結果を partition_strategy.json に保存しました")
        print(f"\n✅ 分割戦略分析完了!")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()