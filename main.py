# main.py
from image_processor import ImageProcessor
from database import ImageDatabase

def main():
    from trtagger import TensorRTTagger
    
    tagger = TensorRTTagger(model="wd-eva02-large-tagger-v3")

    # データベース初期化
    db = ImageDatabase()
    
    # 画像プロセッサー初期化
    processor = ImageProcessor(tagger.infer_batch, db)
    
    # 画像ディレクトリを処理
    image_directory = "downloaded"  # 実際のパスに変更
    processor.process_directory(image_directory)

if __name__ == "__main__":
    main()