import os
import re
import io
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import shutil
import json
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

def natural_sort_key(s):
    """Sort strings containing numbers in natural order."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def add_text_to_image(draw, text, position, size):
    """向图片添加文字，使用合适的中文字体"""
    # Windows 系统常见中文字体列表
    chinese_fonts = [
        "msyh.ttc",  # 微软雅黑
        "simhei.ttf",  # 黑体
        "simsun.ttc",  # 宋体
        "simkai.ttf",  # 楷体
        "C:/Windows/Fonts/msyh.ttc",  # 完整路径尝试
        "C:/Windows/Fonts/simhei.ttf"
    ]
    
    # 尝试加载中文字体
    font = None
    for font_path in chinese_fonts:
        try:
            font = ImageFont.truetype(font_path, size)
            break
        except:
            continue
    
    # 如果没有找到任何中文字体，使用默认字体
    if font is None:
        font = ImageFont.load_default()
    
    # Get text size
    bbox = draw.textbbox(position, text, font=font)
    # Draw semi-transparent white background with black border
    padding = 10
    background_bbox = (
        bbox[0] - padding,
        bbox[1] - padding,
        bbox[2] + padding,
        bbox[3] + padding
    )
    
    # Draw white background with slight transparency
    draw.rectangle(background_bbox, fill=(255, 255, 255, 230))
    # Draw black border
    draw.rectangle(background_bbox, outline=(0, 0, 0, 255))
    
    # Draw black text
    draw.text(position, text, fill="black", font=font)

def process_similar_pairs(similar_pairs: List[Dict]) -> List[List[str]]:
    """处理相似图片对，将它们分组"""
    groups = []
    used_images = set()
    
    for pair in similar_pairs:
        if pair['image1'] in used_images or pair['image2'] in used_images:
            continue
            
        group = [pair['image1'], pair['image2']]
        used_images.add(pair['image1'])
        used_images.add(pair['image2'])
        
        # 查找与当前组中图片相似的其他图片
        for other_pair in similar_pairs:
            if other_pair['image1'] in group and other_pair['image2'] not in used_images:
                group.append(other_pair['image2'])
                used_images.add(other_pair['image2'])
            elif other_pair['image2'] in group and other_pair['image1'] not in used_images:
                group.append(other_pair['image1'])
                used_images.add(other_pair['image1'])
        
        groups.append(group)
    
    return groups

def move_duplicate_images(similar_pairs: List[Dict], source_dir: Path, target_dir: Path) -> int:
    """移动重复图片到目标目录"""
    target_dir.mkdir(exist_ok=True)
    moved_count = 0
    
    # 将相似图片对分组
    groups = process_similar_pairs(similar_pairs)
    
    for group in groups:
        # 保留第一张图片，移动其他图片
        for img in group[1:]:
            src_path = source_dir / img
            dst_path = target_dir / img
            if src_path.exists():
                shutil.move(str(src_path), str(dst_path))
                moved_count += 1
    
    return moved_count

def save_similar_pairs(similar_pairs: List[Dict], output_file: str = 'similar_pairs.json'):
    """保存相似图片对到JSON文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(similar_pairs, f, ensure_ascii=False, indent=2)

def load_similar_pairs(input_file: str = 'similar_pairs.json') -> List[Dict]:
    """从JSON文件加载相似图片对"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return [] 