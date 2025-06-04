# Flask Utils Web App

[English](#english) | [中文](#中文)

<a name="english"></a>

# Flask Utils Web App

A collection of practical web utilities built with Flask, featuring image processing, file comparison, and prompt management.

## Features

### 1. Image Processing

- **Image Merging**: Combine two images side by side with optional "Before/After" labels
- **Multi-Image Merging**: Merge up to 6 images with automatic size adjustment
- **Image Upload**: Upload images and get shareable direct links
- Supports common image formats (PNG, JPG, JPEG, GIF, WEBP)

### 2. File Comparison

- Compare two text files and highlight differences
- Side-by-side diff view with syntax highlighting
- Easy file upload with drag & drop support

### 3. Prompt Management

- Store and manage frequently used prompts
- Drag & drop reordering
- Quick copy to clipboard
- Edit and delete functionality

## Technical Stack

- Backend: Flask + SQLAlchemy
- Frontend: Bootstrap 5 + Bootstrap Icons
- Database: SQLite
- Image Processing: Pillow

## Installation

1. Clone the repository

```bash
git clone https://github.com/yourusername/flask-utils.git
cd flask-utils
```

2. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Initialize the database and create required directories

```bash
python init_db.py  # Create the SQLite database
mkdir -p static/uploads  # Create upload directory
```

5. Run the application

```bash
flask run
```

Visit http://127.0.0.1:5000 in your browser.

## Project Structure

```
flask_utils/
├── app.py              # Main application file
├── init_db.py         # Database initialization script
├── requirements.txt    # Project dependencies
├── static/            # Static files
│   └── uploads/       # Uploaded images (auto-created)
├── templates/         # HTML templates
│   ├── base.html     # Base template with common layout
│   ├── merge.html    # Image merging interface
│   ├── file_diff.html # File comparison interface
│   └── prompts.html  # Prompt management interface
└── utils/            # Utility functions
    └── image_processor.py  # Image processing functions
```

## Contributing

Feel free to open issues or submit pull requests.

## License

MIT License

---

<a name="中文"></a>

# Flask 工具集网页应用

一个基于 Flask 构建的实用工具集，包含图片处理、文件对比和提示词管理等功能。

## 功能特点

### 1. 图片处理

- **双图拼接**：将两张图片并排拼接，可选择添加"修改前/后"标记
- **多图拼接**：最多支持 6 张图片合并，自动调整大小
- **图片上传**：上传图片并获取可分享的直接链接
- 支持常见图片格式（PNG、JPG、JPEG、GIF、WEBP）

### 2. 文件对比

- 对比两个文本文件并高亮显示差异
- 并排展示差异内容，支持语法高亮
- 便捷的文件上传功能，支持拖拽

### 3. 提示词管理

- 存储和管理常用提示词
- 支持拖拽排序
- 一键复制到剪贴板
- 编辑和删除功能

## 技术栈

- 后端：Flask + SQLAlchemy
- 前端：Bootstrap 5 + Bootstrap Icons
- 数据库：SQLite
- 图片处理：Pillow

## 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/yourusername/flask-utils.git
cd flask-utils
```

2. 创建并激活虚拟环境

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 运行应用

```bash
flask run
```

在浏览器中访问 http://127.0.0.1:5000

## 项目结构

```
flask_utils/
├── app.py              # 主应用文件
├── requirements.txt    # 项目依赖
├── static/            # 静态文件
│   └── uploads/       # 上传的图片
├── templates/         # HTML模板
└── utils/            # 工具函数
```

## 贡献

欢迎提出问题或提交 pull requests。

## 许可证

MIT 许可证
