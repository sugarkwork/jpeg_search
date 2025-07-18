#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース解析ツール
GROUPS変数の被写体の数と組み合わせごとに画像数をカウントする
"""

import sqlite3
from collections import defaultdict, Counter
from math import inf
import json
from database import ImageDatabase

# app.pyのGROUPS変数を再定義
GROUPS = {
    "girls": {
        "1girl": (1, 1),
        "2girls": (2, 2),
        "3girls": (3, 3),
        "4girls": (4, 4),
        "5girls": (5, 5),
        "6girls": (6, 6),
        "multiple_girls": (2, inf),
    },
    "boys": {
        "1boy": (1, 1),
        "2boys": (2, 2),
        "3boys": (3, 3),
        "4boys": (4, 4),
        "5boys": (5, 5),
        "6boys": (6, 6),
        "multiple_boys": (2, inf),
    },
    "solo": {
        "solo": (1, 1),           # 総キャラ数 = 1 のシグナル
    },
}

class DatabaseAnalyzer:
    def __init__(self, db_path="image_search.db"):
        self.db_path = db_path
        self.db = ImageDatabase(db_path)
    
    def get_all_group_tags(self):
        """GROUPS変数に含まれる全てのタグを取得"""
        all_tags = set()
        for group_name, tag_dict in GROUPS.items():
            all_tags.update(tag_dict.keys())
        return all_tags
    
    def analyze_tag_combinations(self):
        """被写体の数と組み合わせごとに画像数をカウント"""
        print("データベース解析を開始します...")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # 全画像数を取得
        cursor.execute('SELECT COUNT(*) FROM images')
        total_images = cursor.fetchone()[0]
        print(f"総画像数: {total_images:,}件")
        
        # GROUPS変数に含まれるタグの使用状況を取得
        group_tags = self.get_all_group_tags()
        tag_placeholders = ','.join(['?' for _ in group_tags])
        
        cursor.execute(f'''
            SELECT t.tag_name, COUNT(it.image_id) as usage_count
            FROM tags t
            LEFT JOIN image_tags it ON t.id = it.tag_id
            WHERE t.tag_name IN ({tag_placeholders})
            GROUP BY t.tag_name
            ORDER BY usage_count DESC
        ''', list(group_tags))
        
        tag_usage = dict(cursor.fetchall())
        print(f"\nGROUPS変数に含まれるタグの使用状況:")
        for tag, count in tag_usage.items():
            print(f"  {tag}: {count:,}件")
        
        # 各画像がどのGROUPSタグを持っているかを取得
        cursor.execute(f'''
            SELECT i.id, GROUP_CONCAT(t.tag_name) as tags
            FROM images i
            LEFT JOIN image_tags it ON i.id = it.image_id
            LEFT JOIN tags t ON it.tag_id = t.id AND t.tag_name IN ({tag_placeholders})
            GROUP BY i.id
        ''', list(group_tags))
        
        image_tags = cursor.fetchall()
        conn.close()
        
        # 組み合わせ別の統計を作成
        combination_stats = defaultdict(int)
        tag_combination_counter = Counter()
        
        # 各グループ別の統計
        group_stats = {group_name: defaultdict(int) for group_name in GROUPS.keys()}
        
        print(f"\n画像のタグ組み合わせを解析中... ({len(image_tags):,}件)")
        
        for image_id, tags_str in image_tags:
            if tags_str:
                image_tags_set = set(tags_str.split(','))
            else:
                image_tags_set = set()
            
            # 各グループでのタグ存在をチェック
            group_presence = {}
            for group_name, tag_dict in GROUPS.items():
                present_tags = image_tags_set.intersection(set(tag_dict.keys()))
                group_presence[group_name] = present_tags
            
            # 組み合わせパターンを記録
            combination_key = []
            for group_name in sorted(GROUPS.keys()):
                if group_presence[group_name]:
                    tags_in_group = sorted(list(group_presence[group_name]))
                    combination_key.append(f"{group_name}:{'+'.join(tags_in_group)}")
                else:
                    combination_key.append(f"{group_name}:none")
            
            combination_str = " | ".join(combination_key)
            combination_stats[combination_str] += 1
            
            # 個別タグの組み合わせもカウント
            if image_tags_set:
                sorted_tags = tuple(sorted(image_tags_set))
                tag_combination_counter[sorted_tags] += 1
            
            # 各グループ別の統計
            for group_name, present_tags in group_presence.items():
                if present_tags:
                    for tag in present_tags:
                        group_stats[group_name][tag] += 1
                else:
                    group_stats[group_name]["none"] += 1
        
        return {
            'total_images': total_images,
            'tag_usage': tag_usage,
            'combination_stats': dict(combination_stats),
            'tag_combination_counter': dict(tag_combination_counter),
            'group_stats': {k: dict(v) for k, v in group_stats.items()}
        }
    
    def print_analysis_results(self, results):
        """解析結果を見やすく表示"""
        print("\n" + "="*80)
        print("データベース解析結果")
        print("="*80)
        
        print(f"\n📊 基本統計:")
        print(f"  総画像数: {results['total_images']:,}件")
        
        print(f"\n🏷️  GROUPSタグ使用状況:")
        for tag, count in sorted(results['tag_usage'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / results['total_images']) * 100
            print(f"  {tag:15}: {count:8,}件 ({percentage:5.1f}%)")
        
        print(f"\n👥 グループ別統計:")
        for group_name, stats in results['group_stats'].items():
            print(f"\n  【{group_name.upper()}】")
            total_in_group = sum(count for tag, count in stats.items() if tag != "none")
            none_count = stats.get("none", 0)
            
            for tag, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                if tag == "none":
                    percentage = (count / results['total_images']) * 100
                    print(f"    {tag:15}: {count:8,}件 ({percentage:5.1f}%) - タグなし")
                else:
                    percentage = (count / results['total_images']) * 100
                    print(f"    {tag:15}: {count:8,}件 ({percentage:5.1f}%)")
        
        print(f"\n🔄 組み合わせパターン統計 (上位20位):")
        sorted_combinations = sorted(results['combination_stats'].items(), 
                                   key=lambda x: x[1], reverse=True)
        
        for i, (combination, count) in enumerate(sorted_combinations[:20], 1):
            percentage = (count / results['total_images']) * 100
            print(f"  {i:2d}. {count:8,}件 ({percentage:5.1f}%) - {combination}")
        
        print(f"\n📈 よく使われるタグ組み合わせ (上位10位):")
        sorted_tag_combinations = sorted(results['tag_combination_counter'].items(),
                                       key=lambda x: x[1], reverse=True)
        
        for i, (tags, count) in enumerate(sorted_tag_combinations[:10], 1):
            percentage = (count / results['total_images']) * 100
            tags_str = " + ".join(tags)
            print(f"  {i:2d}. {count:8,}件 ({percentage:5.1f}%) - {tags_str}")
    
    def suggest_database_partitioning(self, results):
        """データベース分割の提案"""
        print(f"\n" + "="*80)
        print("データベース分割提案")
        print("="*80)
        
        total_images = results['total_images']
        
        # 主要な分割軸を特定
        print(f"\n💡 分割提案:")
        
        # 1. 人数による分割
        print(f"\n1️⃣  人数による分割:")
        girls_stats = results['group_stats']['girls']
        boys_stats = results['group_stats']['boys']
        solo_stats = results['group_stats']['solo']
        
        # ソロ画像（1人のみ）
        solo_only = solo_stats.get('solo', 0)
        
        # 2人の画像
        two_girls = girls_stats.get('2girls', 0)
        two_boys = boys_stats.get('2boys', 0)
        
        # 複数人の画像（3人以上）
        multiple_girls = girls_stats.get('multiple_girls', 0)
        multiple_boys = boys_stats.get('multiple_boys', 0)
        three_plus_girls = girls_stats.get('3girls', 0) + girls_stats.get('4girls', 0) + girls_stats.get('5girls', 0)
        three_plus_boys = boys_stats.get('3boys', 0) + boys_stats.get('4boys', 0) + boys_stats.get('5boys', 0)
        
        print(f"  - 1人（ソロ）: {solo_only:,}件 ({solo_only/total_images*100:.1f}%)")
        print(f"  - 2人: {two_girls + two_boys:,}件 ({(two_girls + two_boys)/total_images*100:.1f}%)")
        print(f"  - 3人以上: {three_plus_girls + three_plus_boys:,}件 ({(three_plus_girls + three_plus_boys)/total_images*100:.1f}%)")
        print(f"  - 複数人（multiple_*）: {multiple_girls + multiple_boys:,}件 ({(multiple_girls + multiple_boys)/total_images*100:.1f}%)")
        
        # 2. 性別による分割
        print(f"\n2️⃣  性別による分割:")
        girls_only = girls_stats.get('none', 0)  # 女性タグなし
        boys_only = boys_stats.get('none', 0)    # 男性タグなし
        
        # 女性キャラクターを含む画像
        girls_images = total_images - girls_only
        # 男性キャラクターを含む画像
        boys_images = total_images - boys_only
        # 両方を含む画像
        both_images = girls_images + boys_images - total_images
        # 女性のみ
        girls_only_images = girls_images - both_images
        # 男性のみ
        boys_only_images = boys_images - both_images
        # どちらも含まない
        neither_images = total_images - girls_images - boys_images + both_images
        
        print(f"  - 女性キャラクターのみ: {girls_only_images:,}件 ({girls_only_images/total_images*100:.1f}%)")
        print(f"  - 男性キャラクターのみ: {boys_only_images:,}件 ({boys_only_images/total_images*100:.1f}%)")
        print(f"  - 両方含む: {both_images:,}件 ({both_images/total_images*100:.1f}%)")
        print(f"  - どちらも含まない: {neither_images:,}件 ({neither_images/total_images*100:.1f}%)")
        
        # 3. 推奨分割戦略
        print(f"\n3️⃣  推奨分割戦略:")
        
        # ソロ vs 複数人での分割
        multi_person_images = total_images - solo_only
        if solo_only > total_images * 0.3:
            print(f"  🎯 「ソロ」vs「複数人」での分割が効果的")
            print(f"     - ソロデータベース: {solo_only:,}件")
            print(f"     - 複数人データベース: {multi_person_images:,}件")
        
        # 性別による分割
        if girls_only_images > total_images * 0.2 and boys_only_images > total_images * 0.1:
            print(f"  🎯 「女性のみ」vs「男性のみ」vs「混合」での分割も有効")
            print(f"     - 女性のみデータベース: {girls_only_images:,}件")
            print(f"     - 男性のみデータベース: {boys_only_images:,}件")
            print(f"     - 混合データベース: {both_images + neither_images:,}件")
        
        # 4. 検索パフォーマンス予測
        print(f"\n4️⃣  検索パフォーマンス予測:")
        current_avg_search = total_images / 2  # 平均的な検索対象数
        
        # ソロ vs 複数人での分割効果
        if solo_only > total_images * 0.3:
            solo_db_avg = solo_only / 2
            multi_db_avg = multi_person_images / 2
            max_db_size = max(solo_db_avg, multi_db_avg)
            improvement = current_avg_search / max_db_size
            print(f"  - 現在の平均検索対象: {current_avg_search:,.0f}件")
            print(f"  - ソロ分割後の平均検索対象: {solo_db_avg:,.0f}件")
            print(f"  - 複数人分割後の平均検索対象: {multi_db_avg:,.0f}件")
            print(f"  - 予想パフォーマンス向上: {improvement:.1f}倍")
        
        # 最適な分割パターンの提案
        print(f"\n5️⃣  最適分割パターン:")
        print(f"  📊 現在の検索時間が30秒の場合:")
        if solo_only > total_images * 0.3:
            solo_time = 30 * (solo_db_avg / current_avg_search)
            multi_time = 30 * (multi_db_avg / current_avg_search)
            print(f"     - ソロDB検索時間: {solo_time:.1f}秒")
            print(f"     - 複数人DB検索時間: {multi_time:.1f}秒")
    
    def save_results_to_file(self, results, filename="database_analysis.json"):
        """結果をJSONファイルに保存"""
        # tag_combination_counterのtupleキーを文字列に変換
        results_copy = results.copy()
        results_copy['tag_combination_counter'] = {
            " + ".join(tags): count 
            for tags, count in results['tag_combination_counter'].items()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_copy, f, ensure_ascii=False, indent=2)
        print(f"\n💾 解析結果を {filename} に保存しました")

def main():
    """メイン実行関数"""
    print("🔍 画像データベース解析ツール")
    print("GROUPS変数の被写体数・組み合わせ別統計を作成します\n")
    
    try:
        analyzer = DatabaseAnalyzer()
        results = analyzer.analyze_tag_combinations()
        
        analyzer.print_analysis_results(results)
        analyzer.suggest_database_partitioning(results)
        analyzer.save_results_to_file(results)
        
        print(f"\n✅ 解析完了!")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()