# 画像タグ検索システム (Image Tag Search System)

TensorRTを使用したAI画像タグ付けと高速検索を行うWebアプリケーションです。

## 概要

このシステムは以下の機能を提供します：

- **AI自動タグ付け**: TensorRTとWD-EVA02-Large-Tagger-v3モデルを使用した高速画像タグ付け
- **高度な検索機能**: ポジティブ・ネガティブタグによる柔軟な画像検索
- **Webインターフェース**: 直感的な画像検索・閲覧UI
- **バッチ処理**: 複数画像の効率的な一括処理

## 主要機能

### 🏷️ 自動タグ付け
- TensorRTによる高速推論
- キャラクター・一般タグの自動分類
- 信頼度スコア付きタグ生成

### 🔍 高度な検索
- ポジティブタグ（含む）・ネガティブタグ（除く）による検索
- 人数指定の自動クエリ構築（1girl, 2girls, multiple_girls等）
- タグ自動補完機能

### 🖼️ Webインターフェース
- レスポンシブデザイン
- 画像拡大表示モーダル
- リアルタイムタグ候補表示
- デバッグ情報表示

## システム構成

```
├── app.py              # Flask Webアプリケーション
├── main.py             # 画像処理メインスクリプト
├── trtagger.py         # TensorRT推論エンジン
├── image_processor.py  # 画像バッチ処理
├── database.py         # SQLiteデータベース管理
├── tags.py             # タグ処理ユーティリティ
├── templates/
│   └── index.html      # Webインターフェース
├── models/             # AIモデル格納ディレクトリ
└── downloaded/         # 処理対象画像ディレクトリ
```

## 必要な環境

### システム要件
- **OS**: Windows 11 (CUDA対応)
- **GPU**: NVIDIA GPU (TensorRT対応)
- **Python**: 3.8+

### 必要なソフトウェア
- NVIDIA CUDA Toolkit
- TensorRT 10.9.0.34+
- Python依存パッケージ（下記参照）

### Python依存パッケージ
```bash
pip install flask
pip install tensorrt
pip install pycuda
pip install pillow
pip install numpy
pip install requests
```

## セットアップ

### 1. 環境変数設定
```powershell
$env:PATH = "C:\Program Files\NVIDIA GPU Computing Toolkit\TensorRT-10.9.0.34\bin" + ";" + "C:\Program Files\NVIDIA GPU Computing Toolkit\TensorRT-10.9.0.34\lib" + ";" + $env:PATH
```

### 2. モデルダウンロード
初回実行時に自動的にWD-EVA02-Large-Tagger-v3モデルがダウンロードされます。

### 3. 画像の準備
処理したい画像を[`downloaded/`](downloaded/)ディレクトリに配置してください。

## 使用方法

### 1. 画像の処理（タグ付け）
```bash
python main.py
```
- [`downloaded/`](downloaded/)ディレクトリ内の画像を自動処理
- AIタグ付けとデータベース登録を実行

### 2. Webアプリケーション起動
```bash
python app.py
```
- ブラウザで http://localhost:5000 にアクセス
- 画像検索インターフェースが利用可能

### 3. 画像検索
- **ポジティブタグ**: 含めたいタグをカンマ区切りで入力
- **ネガティブタグ**: 除外したいタグをカンマ区切りで入力
- 例：`1girl, smile` で笑顔の女の子の画像を検索

## API エンドポイント

### 検索API
- **POST** [`/api/search`](app.py:86) - 画像検索
- **GET** [`/api/image/<id>`](app.py:133) - 画像配信
- **GET** [`/api/image/<id>/tags`](app.py:158) - 画像タグ取得

### 補助API
- **GET** [`/api/tags/suggestions`](app.py:168) - タグ候補取得
- **GET** [`/api/debug/stats`](app.py:196) - データベース統計
- **GET** [`/api/debug/images`](app.py:236) - 画像一覧（デバッグ用）

## 技術詳細

### TensorRT推論
- **モデル**: WD-EVA02-Large-Tagger-v3
- **バッチサイズ**: 1-8枚（動的）
- **入力サイズ**: 448x448x3
- **推論精度**: FP16最適化

### データベース設計
- **images**: 画像メタデータ
- **tags**: タグマスター
- **image_tags**: 画像-タグ関連（信頼度付き）

### 検索アルゴリズム
- ポジティブタグのAND検索
- ネガティブタグの除外フィルタ
- 人数タグの自動競合解決

## トラブルシューティング

### TensorRTエラー
```bash
# エンジンバージョン確認
trtexec --getPlanVersionOnly --loadEngine=models/wd-eva02-large-tagger-v3.trt
```

### CUDA/GPU問題
- NVIDIA ドライバーの更新
- CUDA Toolkitの再インストール
- GPU メモリ不足の確認

### データベース問題
- [`image_search.db`](database.py:7)ファイルの権限確認
- SQLiteブラウザでのデータ確認

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 使用モデル

- **WD-EVA02-Large-Tagger-v3**: SmilingWolf/wd-eva02-large-tagger-v3
- Hugging Face Hub経由で自動ダウンロード

## 貢献

プルリクエストやイシューの報告を歓迎します。

## 更新履歴

- **v1.0**: 初期リリース
  - TensorRT推論エンジン
  - Flask Webアプリケーション
  - SQLiteデータベース
  - 基本的な検索機能