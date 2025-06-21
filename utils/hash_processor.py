import imagehash
from PIL import Image
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class HashProcessor:
    def extract_features(self, image_path: str) -> Dict:
        """提取哈希特征"""
        try:
            img = Image.open(image_path)
            
            # 计算多种哈希值
            phash = str(imagehash.phash(img))
            ahash = str(imagehash.average_hash(img))
            dhash = str(imagehash.dhash(img))
            
            return {
                'phash': phash,
                'ahash': ahash,
                'dhash': dhash
            }
        except Exception as e:
            logger.error(f"提取哈希特征时出错 {image_path}: {str(e)}")
            return None
    
    def calculate_similarity(self, feat1: Dict, feat2: Dict) -> float:
        """计算两张图片的哈希相似度"""
        if feat1 is None or feat2 is None:
            return 0.0
            
        # 计算哈希值的汉明距离
        phash_sim = 1 - (sum(c1 != c2 for c1, c2 in zip(feat1['phash'], feat2['phash'])) / 64)
        ahash_sim = 1 - (sum(c1 != c2 for c1, c2 in zip(feat1['ahash'], feat2['ahash'])) / 64)
        dhash_sim = 1 - (sum(c1 != c2 for c1, c2 in zip(feat1['dhash'], feat2['dhash'])) / 64)
        
        # 综合相似度
        weights = {'phash': 0.4, 'ahash': 0.3, 'dhash': 0.3}
        similarity = (
            weights['phash'] * phash_sim +
            weights['ahash'] * ahash_sim +
            weights['dhash'] * dhash_sim
        )
        
        return float(similarity) 