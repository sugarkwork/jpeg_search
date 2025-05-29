from math import inf

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
    """範囲が重なっていれば True"""
    a1, b1 = r1
    a2, b2 = r2
    return not (b1 < a2 or b2 < a1)

def build_query(pos_tags: str) -> str:
    pos = set([tag.strip() for tag in pos_tags.split(',')])
    neg = set()

    for _, tag_map in GROUPS.items():
        # この軸で許可する人数レンジ (min, max)
        allowed = set()
        for tag, rng in tag_map.items():
            if tag in pos:
                allowed.add(tag)

        if allowed:
            # 許可レンジを集合でまとめる
            allow_ranges = [tag_map[t] for t in allowed]
            # 比較対象は同じ軸の全タグ
            for tag, rng in tag_map.items():
                # 空集合なら除外
                if not any(_overlap(rng, ar) for ar in allow_ranges):
                    neg.add(tag)

    # solo の特別処理（キャラ総数＝1 を排除）
    if {"1girl", "1boy"} & pos != pos:  # 1人だけの検索でない場合
        neg.add("solo")

    # ポジティブと重複した − タグは付けない
    neg_final = [f"{t}" for t in neg if t not in pos]
    return ", ".join(sorted(pos)),  ", ".join(sorted(neg_final))

print(build_query("2girls, 1boy, hands"))
# -> 1boy 2girls -1girl -2boys -multiple_boys -solo
