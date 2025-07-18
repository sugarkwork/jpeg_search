# image_processor.py
import os
import glob
from typing import List
from database import ImageDatabase

class ImageProcessor:
    def __init__(self, tag_method, db: ImageDatabase):
        """
        tag_method: 既存のタグ化メソッド（最大4枚の画像パスのリストを受け取り、タグのリストのリストを返す）
        """
        self.tag_method = tag_method
        self.db = db
    
    def process_directory(self, directory_path: str, extensions: List[str] = None):
        """ディレクトリ内の全画像を処理"""
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']
        
        # 画像ファイルを取得
        image_files = []
        for ext in extensions:
            pattern = os.path.join(directory_path, f"**/*{ext}")
            image_files.extend(glob.glob(pattern, recursive=True))
            pattern = os.path.join(directory_path, f"**/*{ext.upper()}")
            image_files.extend(glob.glob(pattern, recursive=True))
        
        image_files = list(set(image_files))
        print(f"Found {len(image_files)} images to process")

        db_images = []
        for image in self.db.get_all_image_filenames():
            db_img_path = os.path.join(directory_path, image)
            db_images.append(db_img_path)
        
        print(f"Database contains {len(db_images)} images")
        
        # 重複を除去
        image_files = list(set(image_files) - set(db_images))
        
        print(f"Found {len(image_files)} unique images to process")
        
        # 4枚ずつバッチ処理
        batch_size = 4
        processed_count = 0
        
        for i in range(0, len(image_files), batch_size):
            batch = image_files[i:i + batch_size]
            
            try:
                percent = int(i / len(image_files) * 100)

                # タグ化実行
                print(f"Processing batch {i//batch_size + 1}/{(len(image_files) + batch_size - 1)//batch_size} ({percent}%)")
                tags_list = self.tag_method(batch)

                print("tags_list", tags_list)
                
                # データベースに保存
                for filepath, tags in zip(batch, tags_list):
                    tags = [tag.strip() for tag in tags[1].split(",")]
                    print("filepath", filepath, "tags", tags)
                    try:
                        self.db.add_image_with_tags(filepath, tags)
                        processed_count += 1
                        print(f"✓ Processed: {os.path.basename(filepath)} - Tags: {', '.join(tags[:5])}...")
                    except Exception as e:
                        print(f"✗ Error processing {filepath}: {e}")
                        
            except Exception as e:
                print(f"✗ Error processing batch: {e}")
                continue
        
        print(f"Processing complete! {processed_count}/{len(image_files)} images processed successfully.")