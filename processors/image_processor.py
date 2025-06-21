import os
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from tqdm import tqdm
from pathlib import Path
import logging
from typing import List, Tuple, Dict

from .hash_processor import HashProcessor
from .hist_processor import HistProcessor
# from .deep_processor import DeepProcessor  # 注释掉深度学习处理器

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, input_dir: str = "imgs", output_dir: str = "small_imgs"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 初始化各个处理器
        self.hash_processor = HashProcessor()
        self.hist_processor = HistProcessor()
        # self.deep_processor = DeepProcessor()  # 注释掉深度学习处理器初始化
    
    def create_thumbnails(self, target_size: tuple = (256, 256)) -> None:
        """创建缩略图并保存元数据"""
        logger.info("开始创建缩略图...")
        
        # 准备存储元数据的列表
        metadata = []
        
        # 获取所有图片文件
        image_files = list(self.input_dir.glob("*.jpg")) + list(self.input_dir.glob("*.png"))
        
        for img_path in tqdm(image_files, desc="处理图片"):
            try:
                # 读取原始图片
                img = Image.open(img_path)
                
                # 保存原始尺寸
                original_size = img.size
                
                # 创建缩略图
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # 保存缩略图
                thumbnail_path = self.output_dir / f"thumb_{img_path.name}"
                img.save(thumbnail_path, quality=95)
                
                # 记录元数据
                metadata.append({
                    'original_path': str(img_path.name),
                    'thumbnail_path': str(thumbnail_path.name),
                    'original_size': f"{original_size[0]}x{original_size[1]}",
                    'thumbnail_size': f"{img.size[0]}x{img.size[1]}"
                })
                
            except Exception as e:
                logger.error(f"处理图片 {img_path} 时出错: {str(e)}")
        
        # 保存元数据到CSV
        df = pd.DataFrame(metadata)
        df.to_csv("image_metadata.csv", index=False)
        logger.info(f"缩略图创建完成，共处理 {len(metadata)} 张图片")
    
    def find_similar_pairs(self, image_paths: List[str], method: str = 'hash', threshold: float = 0.95) -> List[Dict]:
        """
        Find similar image pairs using the specified method
        """
        if method == 'deep':
            print("Deep learning method is currently disabled")
            return []
            
        similar_pairs = []
        features = {}
        
        # Extract features for all images
        for path in image_paths:
            if method == 'hash':
                features[path] = self.hash_processor.get_image_features(path)
            elif method == 'hist':
                features[path] = self.hist_processor.get_image_features(path)
            elif method == 'deep':
                # Deep learning is disabled
                continue
        
        # Compare all pairs
        paths = list(features.keys())
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                path1, path2 = paths[i], paths[j]
                
                if method == 'hash':
                    similarity = self.hash_processor.compute_similarity(
                        features[path1], features[path2]
                    )
                elif method == 'hist':
                    similarity = self.hist_processor.compute_similarity(
                        features[path1], features[path2]
                    )
                elif method == 'deep':
                    # Deep learning is disabled
                    continue
                
                if similarity >= threshold:
                    similar_pairs.append({
                        'image1': path1,
                        'image2': path2,
                        'similarity': similarity
                    })
        
        return similar_pairs 