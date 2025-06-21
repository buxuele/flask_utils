from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, send_from_directory
import os
import re
import io
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# from processors.image_processor import ImageProcessor
from tempfile import NamedTemporaryFile
import difflib
import uuid
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from utils.clean_images import convert_image_to_jpg
from utils.image_utils import save_similar_pairs, load_similar_pairs, move_duplicate_images
from utils.image_processor import process_images, ImageProcessor
import json
import shutil
from config import Config


app = Flask(__name__)

# Apply configurations from Config class
app.config.from_object(Config)

# 允许的图片扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'tif', 'tiff', 'psd', 'eps', 'ai', 'webp'}

# 检查文件扩展名是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



db = SQLAlchemy(app)

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Prompt {self.id}>'

with app.app_context():
    db.create_all()

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

# 创建图片处理器实例
image_processor = ImageProcessor()

# Ensure all necessary directories exist
os.makedirs(Config.USER_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.IMG_DUP_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.THUMBNAIL_FOLDER, exist_ok=True)
os.makedirs(Config.DUPLICATES_FOLDER, exist_ok=True)
os.makedirs(Config.REMOVE_DUP_FOLDER, exist_ok=True)

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
    files_with_names.sort(key=lambda x: natural_sort_key(x[0]))
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

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """图片上传页面"""
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('没有选择文件', 'error')
            return redirect(url_for('upload'))

        file = request.files['image']
        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('upload'))

        if file and allowed_file(file.filename):
            # 生成唯一的文件名
            filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
            file.save(os.path.join(Config.USER_UPLOAD_FOLDER, filename))

            # 生成图片的访问链接
            image_url = url_for('static', filename='user_uploads/' + filename, _external=True)
            flash(f'图片上传成功！链接: {image_url}', 'success')
            return redirect(url_for('upload'))

        flash('不支持的文件类型', 'error')
        return redirect(url_for('upload'))

    return render_template('upload.html')

@app.route('/my_files')
def my_files():
    """删除my_files路由"""
    return redirect(url_for('index'))

@app.route('/prompts')
def prompts():
    """提示词列表页面"""
    prompts_list = Prompt.query.order_by(Prompt.order, Prompt.created_at.desc()).all()
    return render_template('prompts.html', prompts=prompts_list)

@app.route('/prompts', methods=['POST'])
def add_prompt():
    """添加新提示词"""
    content = request.form.get('content')
    if content:
        # 获取最大的order值
        max_order = db.session.query(db.func.max(Prompt.order)).scalar() or 0
        prompt = Prompt(content=content, order=max_order + 1)
        db.session.add(prompt)
        db.session.commit()
    return redirect(url_for('prompts'))

@app.route('/prompts/<int:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """更新提示词"""
    prompt = Prompt.query.get_or_404(prompt_id)
    data = request.get_json()
    if 'content' in data:
        prompt.content = data['content']
        db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/prompts/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """删除提示词"""
    prompt = Prompt.query.get_or_404(prompt_id)
    db.session.delete(prompt)
    db.session.commit()
    return '', 204

@app.route('/prompts/reorder', methods=['POST'])
def reorder_prompts():
    """重新排序提示词"""
    data = request.get_json()
    prompt_id = data.get('prompt_id')
    new_index = data.get('new_index')
    
    if prompt_id is None or new_index is None:
        return jsonify({'error': 'Missing parameters'}), 400
        
    prompt = Prompt.query.get_or_404(prompt_id)
    prompts = Prompt.query.order_by(Prompt.order).all()
    
    # 更新顺序
    old_index = prompts.index(prompt)
    prompts.insert(new_index, prompts.pop(old_index))
    
    for i, p in enumerate(prompts):
        p.order = i
    
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/clean_images', methods=['GET', 'POST'])
def clean_images():
    """图片清理页面"""
    if request.method == 'POST':
        folder_path = request.form.get('folder_path', '').strip()
        files = request.files.getlist('images')
        
        # 检查是否至少有一种方式提供了输入
        if not folder_path and len(files) == 0:
            flash('请至少选择一种方式：输入文件夹路径或上传图片文件', 'error')
            return render_template('clean_images.html')
        
        try:
            if folder_path:
                # 方法1：处理文件夹
                # 验证文件夹是否存在
                if not os.path.exists(folder_path):
                    flash('指定的文件夹不存在', 'error')
                    return render_template('clean_images.html')
                
                # 验证是否为文件夹
                if not os.path.isdir(folder_path):
                    flash('指定的路径不是文件夹', 'error')
                    return render_template('clean_images.html')
                
                # 调用图片处理函数
                output_dir = convert_image_to_jpg(folder_path)
            else:
                # 方法2：处理上传的文件
                # 创建临时目录
                temp_dir = os.path.join(Config.USER_UPLOAD_FOLDER, f'temp_{uuid.uuid4().hex[:8]}')
                os.makedirs(temp_dir, exist_ok=True)
                
                # 保存上传的文件
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(temp_dir, filename))
                
                # 调用图片处理函数
                output_dir = convert_image_to_jpg(temp_dir)
                
                # 清理临时目录
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            
            flash('图片处理成功！', 'success')
            return render_template('clean_images.html', output_dir=output_dir)
            
        except Exception as e:
            flash(f'处理图片时出错：{str(e)}', 'error')
            return render_template('clean_images.html')
    
    return render_template('clean_images.html')

@app.route('/image_diff')
def image_diff():
    """图片去重页面"""
    return render_template('image_diff.html')

@app.route('/image_diff/process', methods=['POST'])
def process_image_diff():
    """处理图片相似度比较"""
    try:
        # 获取参数
        threshold = float(request.form.get('threshold', 95)) / 100
        method = request.form.get('method', 'hash')
        
        # 验证方法
        if method not in ['hash', 'hist', 'deep']:
            raise ValueError(f"不支持的方法: {method}")
        
        # 保存上传的文件
        files = request.files.getlist('images')
        if not files:
            raise ValueError("请选择要处理的图片文件")
        
        saved_files = image_processor.save_uploaded_files(files)
        if not saved_files:
            raise ValueError("没有成功保存任何图片文件")
        
        # 创建缩略图
        image_processor.create_thumbnails()
        
        # 查找相似图片
        similar_pairs = image_processor.find_similar_images(
            similarity_threshold=threshold,
            method=method
        )
        
        # 将结果保存到JSON文件
        with open('similar_pairs.json', 'w', encoding='utf-8') as f:
            json.dump(similar_pairs, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'status': 'success',
            'message': f'找到 {len(similar_pairs)} 对相似图片'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/image_diff/results')
def show_image_diff_results():
    """显示相似图片结果"""
    try:
        with open('similar_pairs.json', 'r', encoding='utf-8') as f:
            similar_pairs = json.load(f)
    except FileNotFoundError:
        similar_pairs = []
    
    # 将相似图片对分组
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
    
    return render_template('image_diff_results.html', groups=groups)

@app.route('/image_diff/remove_duplicates', methods=['POST'])
def remove_duplicate_images():
    """移除重复图片"""
    try:
        # 读取相似图片对
        with open('similar_pairs.json', 'r', encoding='utf-8') as f:
            similar_pairs = json.load(f)
        
        # 移除重复图片
        moved_count = image_processor.remove_duplicates(similar_pairs)
        
        flash(f'成功移动 {moved_count} 张重复图片到 duplicates 目录', 'success')
        return redirect(url_for('image_diff'))
        
    except Exception as e:
        flash(f'移除重复图片时出错: {str(e)}', 'error')
        return redirect(url_for('image_diff'))

@app.route('/image_diff/img/<path:filename>')
def serve_image(filename):
    """提供图片文件服务"""
    return send_from_directory('static/uploads/image_diff', filename)

@app.route('/image_diff/thumb/<path:filename>')
def serve_thumbnail(filename):
    """提供缩略图服务"""
    return send_from_directory('static/uploads/image_diff/thumbnails', filename)

@app.route('/img_duplicate')
def img_duplicate():
    """图片去重主页"""
    return render_template('image_dedup.html')

@app.route('/img_duplicate/file_count')
def img_duplicate_file_count():
    """获取当前图片数量"""
    count = len(list(Path(Config.IMG_DUP_UPLOAD_FOLDER).glob('*.[jp][pn][g]')))
    return jsonify({'count': count})

@app.route('/img_duplicate/upload', methods=['POST'])
def img_duplicate_upload():
    """上传图片或文件夹"""
    if 'images' not in request.files and 'folder' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    uploaded_files = []
    
    # Handle single file upload
    if 'images' in request.files:
        files = request.files.getlist('images')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(Config.IMG_DUP_UPLOAD_FOLDER, filename)
                file.save(file_path)
                uploaded_files.append(filename)
    
    # Handle folder upload
    if 'folder' in request.files:
        folder = request.files['folder']
        if folder and folder.filename:
            # Create temporary directory to extract folder
            temp_dir = os.path.join(Config.IMG_DUP_UPLOAD_FOLDER, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Save uploaded folder
            folder_path = os.path.join(temp_dir, secure_filename(folder.filename))
            folder.save(folder_path)
            
            # Extract folder (if zip format)
            if folder_path.endswith('.zip'):
                import zipfile
                with zipfile.ZipFile(folder_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            
            # Move all image files to upload directory
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(Config.IMG_DUP_UPLOAD_FOLDER, secure_filename(file))
                        shutil.move(src_path, dst_path)
                        uploaded_files.append(secure_filename(file))
            
            # Clean temporary directory
            shutil.rmtree(temp_dir)
    
    return jsonify({
        'message': f'成功上传 {len(uploaded_files)} 个文件',
        'files': uploaded_files
    })

@app.route('/img_duplicate/process', methods=['POST'])
def img_duplicate_process():
    """处理图片相似度"""
    data = request.get_json()
    method = data.get('method', 'hash')
    threshold = float(data.get('threshold', 0.95))
    
    # 获取所有图片文件
    image_files = [f for f in os.listdir(Config.IMG_DUP_UPLOAD_FOLDER)
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        return jsonify({'error': '没有找到图片文件'}), 400
    
    # 根据选择的方法处理图片
    processor = ImageProcessor()
    similar_pairs = processor.find_similar_pairs(
        [os.path.join(Config.IMG_DUP_UPLOAD_FOLDER, f) for f in image_files],
        method=method,
        threshold=threshold
    )
    
    # Save results
    save_similar_pairs(similar_pairs)
    
    # Redirect to results page
    return redirect(url_for('img_duplicate_results'))

@app.route('/img_duplicate/results')
def img_duplicate_results():
    """显示相似图片结果"""
    similar_pairs = load_similar_pairs()
    return render_template('image_dedup_results.html', similar_pairs=similar_pairs)

@app.route('/img_duplicate/remove_duplicates', methods=['POST'])
def img_duplicate_remove():
    """移除重复图片"""
    similar_pairs = load_similar_pairs()
    if not similar_pairs:
        return jsonify({'error': '没有找到相似图片对'}), 400
    
    # 创建重复图片目录
    duplicates_dir = os.path.join(Config.DUPLICATES_FOLDER)
    os.makedirs(duplicates_dir, exist_ok=True)
    
    # 移动重复图片
    moved_count = move_duplicate_images(
        similar_pairs,
        Path(Config.IMG_DUP_UPLOAD_FOLDER),
        Path(duplicates_dir)
    )
    
    return jsonify({
        'message': f'成功移动 {moved_count} 个重复图片到 {duplicates_dir}'
    })

@app.route('/img_duplicate/img/<filename>')
def img_duplicate_image(filename):
    """获取原始图片"""
    return send_from_directory(Config.IMG_DUP_UPLOAD_FOLDER, filename)

@app.route('/img_duplicate/thumb/<filename>')
def img_duplicate_thumbnail(filename):
    """获取缩略图"""
    return send_from_directory(Config.THUMBNAIL_FOLDER, filename)

if __name__ == '__main__':
    # Create required directories if they don't exist
    Path('templates').mkdir(exist_ok=True)
    Path('uploads').mkdir(exist_ok=True)
    app.run(host='0.0.0.0', port=5080, debug=True)
    print('Server running on http://localhost:5080/')
