from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
import os
import re
import io
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from utils.image_processor import process_images
from tempfile import NamedTemporaryFile
import difflib
import uuid
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


app = Flask(__name__)

# 允许的图片扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'tif', 'tiff', 'psd', 'eps', 'ai', 'webp'}

# 检查文件扩展名是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB
app.secret_key = os.getenv('SECRET_KEY', 'dev_key')  # 用于 flash 消息
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///prompts.db'

# 确保上传文件夹存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # 生成图片的访问链接
            image_url = url_for('static', filename='uploads/' + filename, _external=True)
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

if __name__ == '__main__':
    # Create required directories if they don't exist
    Path('templates').mkdir(exist_ok=True)
    Path('uploads').mkdir(exist_ok=True)
    app.run(debug=True)


