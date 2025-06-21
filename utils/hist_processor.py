import cv2
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class HistProcessor:
    def extract_features(self, image_path: str) -> Dict:
        """提取直方图特征"""
        try:
            img = cv2.imread(str(image_path))
            hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            return {
                'histogram': hist
            }
        except Exception as e:
            logger.error(f"提取直方图特征时出错 {image_path}: {str(e)}")
            return None
    
    def calculate_similarity(self, feat1: Dict, feat2: Dict) -> float:
        """计算两张图片的直方图相似度"""
        if feat1 is None or feat2 is None:
            return 0.0
            
        # 计算直方图相似度
        similarity = cv2.compareHist(feat1['histogram'], feat2['histogram'], cv2.HISTCMP_CORREL)
        return float(similarity) 