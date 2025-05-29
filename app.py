# app.py (修正版)
from flask import Flask, render_template, request, jsonify, send_file
import os
from database import ImageDatabase
import traceback

from math import inf


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# データベース初期化
db = ImageDatabase()

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

def _overlap(r1, r2):
    a1, b1 = r1;  a2, b2 = r2
    return not (b1 < a2 or b2 < a1)

def build_query(pos_tags: str):
    if isinstance(pos_tags, str):
        pos_tags = pos_tags.split(',')
    if isinstance(pos_tags, list):
        pos_tags = [tag.strip() for tag in pos_tags if tag.strip()]
    pos = set(pos_tags)
    neg = set()

    for group, tag_map in GROUPS.items():
        # ---- ① その軸で許可レンジを求める ----
        chosen = {t for t in tag_map if t in pos}
        if chosen:
            allow = [tag_map[t] for t in chosen]
        else:
            # 軸が未指定 → “0人” レンジ = 空集合とみなす
            allow = []

        # ---- ② 衝突するタグを − で付与 ----
        for tag, rng in tag_map.items():
            # 未指定軸なら必ず除外
            if not chosen:
                neg.add(tag)
            # 指定済み軸なら、レンジが重ならないものだけ除外
            elif not any(_overlap(rng, ar) for ar in allow):
                neg.add(tag)

    # ---- ③ solo の扱い ----
    # girl か boy どちらか一方のみ指定 → solo を許容
    # 両方／複数人数指定 → solo を除外
    #if not (pos == {"1girl"} or pos == {"1boy"}):
    #    neg.add("solo")


    # ポジティブと重複した − タグは付けない
    neg_final = [f"{t}" for t in neg if t not in pos]
    return list(pos), list(neg_final)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_images():
    try:
        data = request.json
        print(f"Received search request: {data}")

        positive_tag_build, negative_tag_build = build_query(data.get('positive_tags', []))
        
        positive_tags = list(set([tag.strip().lower() for tag in data.get('positive_tags', []) if tag.strip()] + positive_tag_build))
        negative_tags = list(set([tag.strip().lower() for tag in data.get('negative_tags', []) if tag.strip()] + negative_tag_build))
        limit = data.get('limit', 50)
        
        print(f"Processed tags - Positive: {positive_tags}, Negative: {negative_tags}")
        
        if not positive_tags:
            return jsonify({'error': 'At least one positive tag is required'}), 400
        
        results = db.search_images(positive_tags, negative_tags, limit)
        
        response_data = []
        for image_id, filepath, filename, match_count in results:
            # ファイルの存在確認
            file_exists = os.path.exists(filepath)
            response_data.append({
                'id': image_id,
                'filepath': filepath,
                'filename': filename,
                'match_count': match_count,
                'file_exists': file_exists
            })
        
        print(f"Returning {len(response_data)} results")
        
        return jsonify({
            'results': response_data,
            'total_count': len(response_data),
            'query': {
                'positive_tags': positive_tags,
                'negative_tags': negative_tags
            }
        })
        
    except Exception as e:
        print(f"Search error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/<int:image_id>')
def serve_image(image_id):
    """画像ファイルを配信"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT filepath FROM images WHERE id = ?', (image_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            print(f"Image ID {image_id} not found in database")
            return "Image not found", 404
        
        filepath = result[0]
        if not os.path.exists(filepath):
            print(f"Image file not found: {filepath}")
            return "Image file not found", 404
        
        return send_file(filepath)
        
    except Exception as e:
        print(f"Error serving image {image_id}: {e}")
        return "Error serving image", 500

@app.route('/api/image/<int:image_id>/tags')
def get_image_tags(image_id):
    """特定の画像のタグ情報を取得"""
    try:
        tags = db.get_image_tags_with_confidence(image_id)
        return jsonify({'tags': tags})
    except Exception as e:
        print(f"Error getting tags for image {image_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tags/suggestions')
def get_tag_suggestions():
    """タグの候補を取得"""
    try:
        query = request.args.get('q', '').lower()
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tag_name, COUNT(it.image_id) as usage_count
            FROM tags t
            LEFT JOIN image_tags it ON t.id = it.tag_id
            WHERE t.tag_name LIKE ?
            GROUP BY t.tag_name
            ORDER BY usage_count DESC, t.tag_name
            LIMIT 20
        ''', (f'%{query}%',))
        
        suggestions = [{'tag': row[0], 'count': row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(suggestions)
        
    except Exception as e:
        print(f"Error getting tag suggestions: {e}")
        return jsonify([])

# デバッグ用エンドポイント
@app.route('/api/debug/stats')
def debug_stats():
    """データベースの統計情報"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute('SELECT COUNT(*) FROM images')
        image_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tags')
        tag_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM image_tags')
        relation_count = cursor.fetchone()[0]
        
        # よく使われるタグ
        cursor.execute('''
            SELECT t.tag_name, COUNT(it.image_id) as count
            FROM tags t
            LEFT JOIN image_tags it ON t.id = it.tag_id
            GROUP BY t.tag_name
            ORDER BY count DESC
            LIMIT 20
        ''')
        popular_tags = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'image_count': image_count,
            'tag_count': tag_count,
            'relation_count': relation_count,
            'popular_tags': [{'tag': tag, 'count': count} for tag, count in popular_tags]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/debug/images')
def debug_images():
    """画像一覧（デバッグ用）"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, filename, filepath FROM images LIMIT 10')
        images = cursor.fetchall()
        conn.close()
        
        result = []
        for img_id, filename, filepath in images:
            tags = db.get_image_tags(img_id)
            result.append({
                'id': img_id,
                'filename': filename,
                'filepath': filepath,
                'tags': tags,
                'file_exists': os.path.exists(filepath)
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)