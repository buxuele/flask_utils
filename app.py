from flask import Flask, render_template, request, flash
import os
import re
import io
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from utils.image_processor import process_images

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SECRET_KEY'] = 'your-secret-key'  # 用于flash消息
app.config['UPLOAD_FOLDER'] = 'uploads'  # 文件上传目录

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

@app.route('/')
def index():
    return render_template('merge.html')

@app.route('/merge', methods=['POST'])
def merge_images():
    files = request.files.getlist('image1')
    if len(files) != 2:
        flash('请选择两张图片', 'error')
        return render_template('merge.html')
    
    # Check file types
    for file in files:
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            flash('只支持图片文件 (PNG, JPG, JPEG, GIF, WEBP)', 'error')
            return render_template('merge.html')
    
    file1 = files[0]
    file2 = files[1]
    
    # Sort files by name
    files = [(file1.filename, file1), (file2.filename, file2)]
    files.sort(key=lambda x: natural_sort_key(x[0]))
    
    # Open images
    try:
        img1 = Image.open(files[0][1]).convert('RGBA')
        img2 = Image.open(files[1][1]).convert('RGBA')
        
        # Resize images to same height
        target_height = max(img1.size[1], img2.size[1])
        ratio1 = target_height / img1.size[1]
        ratio2 = target_height / img2.size[1]
        
        new_width1 = int(img1.size[0] * ratio1)
        new_width2 = int(img2.size[0] * ratio2)
        
        img1 = img1.resize((new_width1, target_height), Image.Resampling.LANCZOS)
        img2 = img2.resize((new_width2, target_height), Image.Resampling.LANCZOS)
        
        # Create new image
        new_width = new_width1 + new_width2
        merged_image = Image.new('RGBA', (new_width, target_height), (0, 0, 0, 0))
        
        # Paste images
        merged_image.paste(img1, (0, 0))
        merged_image.paste(img2, (new_width1, 0))
        
        # Add text
        draw = ImageDraw.Draw(merged_image)
        text_size = int(target_height * 0.05)  # 5% of image height
          # Add text if requested
        if 'add_text' in request.form:
            add_text_to_image(draw, "修改前", (20, 20), text_size)
            add_text_to_image(draw, "修改后", (new_width1 + 20, 20), text_size)
        
        # Convert to RGB for JPEG
        merged_image = merged_image.convert('RGB')
        
        # Save to bytes
        img_bytes = io.BytesIO()
        merged_image.save(img_bytes, format='JPEG', quality=95)
        img_bytes.seek(0)
        
        # Convert to base64 for display
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode()
        
        flash('图片拼接成功！', 'success')
        return render_template('merge.html', merged_image=img_base64)
        
    except Exception as e:
        flash(f'处理图片时出错：{str(e)}', 'error')
        return render_template('merge.html')

@app.route('/multi_merge')
def multi_merge():
    """多图拼接页面"""
    return render_template('multi_merge.html')

@app.route('/multi_merge_process', methods=['POST'])
def multi_merge_process():
    """多图拼接处理"""
    files = request.files.getlist('images')
    
    # Validate file count
    if not (2 <= len(files) <= 6):
        flash('请选择2-6张图片', 'error')
        return render_template('multi_merge.html')
    
    # Validate file types
    for file in files:
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            flash('只支持图片文件 (PNG, JPG, JPEG, GIF, WEBP)', 'error')
            return render_template('multi_merge.html')
    
    try:
        files_with_names = [(f.filename, f) for f in files]
        merged_base64 = process_images(files_with_names)
        flash('图片拼接成功！', 'success')
        return render_template('multi_merge.html', merged_image=merged_base64)
        
    except Exception as e:
        flash(f'处理图片时出错：{str(e)}', 'error')
        return render_template('multi_merge.html')

@app.route('/file_diff')
def file_diff():
    """文件对比页面"""
    return render_template('file_diff.html')

@app.route('/upload')
def upload():
    """图片上传页面"""
    return render_template('upload.html')

@app.route('/my_files')
def my_files():
    """用户文件管理页面"""
    return render_template('my_files.html')

if __name__ == '__main__':
    # Create required directories if they don't exist
    Path('templates').mkdir(exist_ok=True)
    Path('uploads').mkdir(exist_ok=True)
    app.run(debug=True)


