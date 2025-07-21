from flask import Flask, render_template, request, flash, redirect, url_for
import os
import re
import io
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from tempfile import NamedTemporaryFile
import difflib
from utils.image_processor import process_images
from config import Config

app = Flask(__name__)

# Apply configurations from Config class
app.config.from_object(Config)

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
    files.sort(key=lambda x: x[0])
    
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
            draw.text((20, 20), "修改前", fill="black", font=ImageFont.load_default())
            draw.text((new_width1 + 20, 20), "修改后", fill="black", font=ImageFont.load_default())
        
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
    print("\n=== 开始处理多图拼接 ===")
    files = request.files.getlist('images')
    print(f"收到的文件数量: {len(files)}")
    print(f"文件名列表: {[f.filename for f in files]}")
    
    # 验证文件数量
    if not (2 <= len(files) <= 6):
        print(f"错误：文件数量不正确({len(files)})")
        flash('请选择2-6张图片', 'error')
        return render_template('multi_merge.html')
    
    # 验证文件类型
    for file in files:
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            print(f"错误：文件类型不支持({file.filename})")
            flash('只支持图片文件 (PNG, JPG, JPEG, GIF, WEBP)', 'error')
            return render_template('multi_merge.html')
    
    # 处理图片
    print("开始进行图片合并...")
    files_with_names = [(f.filename, f) for f in files]
    print(f"排序前的文件顺序: {[f[0] for f in files_with_names]}")
    files_with_names.sort(key=lambda x: x[0])
    print(f"排序后的文件顺序: {[f[0] for f in files_with_names]}")
    
    # 调用处理函数
    print("调用 process_images 函数")
    merged_base64 = process_images(files_with_names)
    
    if merged_base64:
        print("图片合并成功")
        flash('图片拼接成功！', 'success')
        return render_template('multi_merge.html', merged_image=merged_base64)
    else:
        print("图片合并失败")
        flash('处理图片时出错', 'error')
        return render_template('multi_merge.html')

@app.route('/icon_maker')
def icon_maker():
    """Icon 制作页面"""
    return render_template('icon_maker.html')

@app.route('/icon_maker_process', methods=['POST'])
def icon_maker_process():
    """处理 Icon 制作请求"""
    try:
        # 获取上传的图片
        if 'image' not in request.files:
            return 'No image file', 400
        
        file = request.files['image']
        if file.filename == '':
            return 'No image file', 400
        
        # 检查文件类型
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            return 'Unsupported file format', 400
        
        # 获取裁剪参数
        crop_x = int(request.form.get('crop_x', 0))
        crop_y = int(request.form.get('crop_y', 0))
        crop_size = int(request.form.get('crop_size', 100))
        scale = float(request.form.get('scale', 1.0))
        
        # 打开图片
        img = Image.open(file).convert('RGBA')
        
        # 应用缩放
        if scale != 1.0:
            new_width = int(img.size[0] * scale)
            new_height = int(img.size[1] * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 裁剪正方形区域
        crop_box = (crop_x, crop_y, crop_x + crop_size, crop_y + crop_size)
        cropped_img = img.crop(crop_box)
        
        # 生成PNG文件
        png_bytes = io.BytesIO()
        cropped_img.save(png_bytes, format='PNG', optimize=True)
        png_base64 = base64.b64encode(png_bytes.getvalue()).decode()
        
        # 生成ICO文件 - 固定为128x128尺寸
        ico_bytes = io.BytesIO()
        # 将裁剪后的图片调整为128x128
        ico_image = cropped_img.resize((128, 128), Image.Resampling.LANCZOS)
        
        # 保存为ICO格式，明确指定尺寸
        ico_image.save(ico_bytes, format='ICO', sizes=[(128, 128)])
        ico_base64 = base64.b64encode(ico_bytes.getvalue()).decode()
        
        # 返回JSON响应，包含两个文件的base64数据
        from flask import jsonify
        return jsonify({
            'success': True,
            'png_data': png_base64,
            'ico_data': ico_base64,
            'png_filename': 'cropped_image.png',
            'ico_filename': 'cropped_image.ico'
        })
        
    except Exception as e:
        from flask import jsonify
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/file_diff', methods=['GET', 'POST'])
def file_diff():
    """文件对比页面"""
    if request.method == 'POST':
        files = request.files.getlist('files')
        if len(files) != 2:
            return 'Please select exactly two files', 400
        
        # Create temp files and save uploads
        temp_files = []
        try:
            for file in files:
                temp = NamedTemporaryFile(delete=False)
                file.save(temp.name)
                temp_files.append(temp)
            
            # Read file contents
            fromlines = open(temp_files[0].name, encoding='utf-8').readlines()
            tolines = open(temp_files[1].name, encoding='utf-8').readlines()
            
            # Generate HTML diff
            diff = difflib.HtmlDiff().make_file(
                fromlines, 
                tolines,
                files[0].filename,
                files[1].filename,
                context=True
            )
            
            return render_template('file_diff.html', diff_content=diff)
            
        finally:
            # Clean up temp files
            for temp in temp_files:
                try:
                    os.unlink(temp.name)
                except:
                    pass
                    
    return render_template('file_diff.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5083, debug=True)
    # 临时测试的端口是 5083 
    # 开机默认运行的端口是 5080
    print('Server running on http://localhost:5083/')
