from PIL import Image
import io
import base64
from typing import List, Tuple

def merge_images(images: List[Image.Image], count: int) -> Image.Image:
    """Merge multiple images based on count."""
    print(f"\n=== 合并 {count} 张图片 ===")
    
    if count < 2 or count > 6:
        print(f"错误：图片数量 {count} 超出范围(2-6)")
        return None
    
    # 确保所有图片都是有效的
    for i, img in enumerate(images):
        if not hasattr(img, 'size'):
            print(f"错误：第 {i+1} 个图片对象无效，缺少 size 属性")
            print(f"图片对象类型: {type(img)}")
            return None
        print(f"图片 {i+1} 大小: {img.size}")
    
    if count == 2:
        print("使用左右拼接模式")
        return merge_two_images(images)
    elif count == 3:
        print("使用上下拼接模式")
        return merge_three_images(images)
    elif count == 4:
        print("使用2×2网格模式")
        return merge_four_images(images)
    else:  # 5 或 6 张图片
        print("使用2×3网格模式")
        return merge_grid_images(images, 2, 3)

def merge_two_images(images: List[Image.Image]) -> Image.Image:
    """横向合并两张图片"""
    print("\n=== 合并两张图片 ===")
    # 调整到相同高度
    target_height = max(img.size[1] for img in images)
    print(f"目标高度: {target_height}")
    
    # 计算缩放后的宽度
    ratios = [target_height / img.size[1] for img in images]
    new_widths = [int(img.size[0] * ratio) for img, ratio in zip(images, ratios)]
    print(f"缩放比例: {ratios}")
    print(f"新宽度: {new_widths}")
    
    # 缩放图片
    resized_images = [img.resize((new_width, target_height), Image.Resampling.LANCZOS)
                     for img, new_width in zip(images, new_widths)]
    
    # 创建新图片
    new_width = sum(new_widths)
    return merge_two_images(images)

def merge_two_images(images: List[Image.Image]) -> Image.Image:
    """横向合并两张图片"""
    print("\n=== 合并两张图片 ===")
    # 调整到相同高度
    target_height = max(img.size[1] for img in images)
    print(f"目标高度: {target_height}")
    
    # 计算缩放后的宽度
    ratios = [target_height / img.size[1] for img in images]
    new_widths = [int(img.size[0] * ratio) for img, ratio in zip(images, ratios)]
    print(f"缩放比例: {ratios}")
    print(f"新宽度: {new_widths}")
    
    # 缩放图片
    resized_images = [img.resize((new_width, target_height), Image.Resampling.LANCZOS)
                     for img, new_width in zip(images, new_widths)]
    
    # 创建新图片
    new_width = sum(new_widths)
    print(f"合并后总宽度: {new_width}")
    merged = Image.new('RGBA', (new_width, target_height), (0, 0, 0, 0))
    
    # 粘贴图片
    x_offset = 0
    for i, img in enumerate(resized_images):
        print(f"粘贴第 {i+1} 张图片到位置 x={x_offset}")
        merged.paste(img, (x_offset, 0))
        x_offset += img.size[0]
    
    return merged

def merge_three_images(images: List[Image.Image]) -> Image.Image:
    """纵向合并三张图片"""
    print("\n=== 合并三张图片 ===")
    # 调整到相同宽度
    target_width = max(img.size[0] for img in images)
    print(f"目标宽度: {target_width}")
    
    # 计算缩放后的高度
    ratios = [target_width / img.size[0] for img in images]
    new_heights = [int(img.size[1] * ratio) for img, ratio in zip(images, ratios)]
    print(f"缩放比例: {ratios}")
    print(f"新高度: {new_heights}")
    
    # 缩放图片
    resized_images = [img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                     for img, new_height in zip(images, new_heights)]
    
    # 创建新图片
    new_height = sum(new_heights)
    print(f"合并后总高度: {new_height}")
    merged = Image.new('RGBA', (target_width, new_height), (0, 0, 0, 0))
    
    # 粘贴图片
    y_offset = 0
    for i, img in enumerate(resized_images):
        print(f"粘贴第 {i+1} 张图片到位置 y={y_offset}")
        merged.paste(img, (0, y_offset))
        y_offset += img.size[1]
    
    return merged

def merge_four_images(images: List[Image.Image]) -> Image.Image:
    """Merge four images in a 2x2 grid."""
    return merge_grid_images(images, 2, 2)

def merge_grid_images(images: List[Image.Image], rows: int, cols: int) -> Image.Image:
    """网格布局合并图片"""
    print(f"\n=== 网格合并图片 ({rows}×{cols}) ===")
    
    # 计算目标尺寸
    max_width = max(img.size[0] for img in images)
    max_height = max(img.size[1] for img in images)
    print(f"单个图片最大尺寸: {max_width}×{max_height}")
    
    # 缩放所有图片到相同尺寸
    resized_images = [img.resize((max_width, max_height), Image.Resampling.LANCZOS)
                     for img in images]
    print("已完成图片缩放")
    
    # 创建新图片
    grid_width = max_width * cols
    grid_height = max_height * rows
    print(f"最终尺寸: {grid_width}×{grid_height}")
    merged = Image.new('RGBA', (grid_width, grid_height), (0, 0, 0, 0))
    
    # 粘贴图片
    for i, img in enumerate(resized_images):
        if i >= rows * cols:
            break
        
        row = i // cols
        col = i % cols
        x_offset = col * max_width
        y_offset = row * max_height
        print(f"粘贴第 {i+1} 张图片到位置 ({x_offset}, {y_offset})")
        merged.paste(img, (x_offset, y_offset))
    
    return merged

def process_images(files: List[Tuple[str, any]]) -> str:
    """处理多个图片并返回base64编码的结果"""
    print("\n=== 进入图片处理函数 ===")
    print(f"接收到的文件数量: {len(files)}")
    
    # 打开图片
    images = []
    for filename, file in files:
        print(f"正在处理文件: {filename}")
        img = Image.open(file)
        print(f"图片大小: {img.size}, 模式: {img.mode}")
        images.append(img.convert('RGBA'))
    
    print(f"成功打开 {len(images)} 个图片")
    print("开始合并图片...")
    
    # 合并图片
    merged_image = merge_images(images, len(images))
    
    if merged_image is None:
        print("错误：图片合并失败")
        return None
    
    print("开始转换为JPEG格式...")
    # 转换为RGB用于JPEG
    merged_image = merged_image.convert('RGB')
    
    # 保存到字节流
    print("保存到字节流...")
    img_bytes = io.BytesIO()
    merged_image.save(img_bytes, format='JPEG', quality=95)
    img_bytes.seek(0)
    
    # 转换为base64
    print("转换为base64...")
    result = base64.b64encode(img_bytes.getvalue()).decode()
    print("图片处理完成")
    return result