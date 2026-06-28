"""
================================================================================
AI游戏2D资源智能切割与精灵图生成工具 - 后端服务器
================================================================================

项目名称：AI Game 2D Resource Intelligent Cutting and Sprite Sheet Generation Tool
版本：1.0
作者：做熙婷
学号：2408090601008

项目简介：
    本工具是一个基于Web的AI游戏2D资源处理系统，支持智能检测游戏素材中的
    精灵图（Sprite），自动生成九宫格切割、精灵图集，并导出多种主流游戏
    引擎（Unity、Cocos2d-x、Unreal Engine）的配置文件。

技术栈：
    - 后端框架：Flask + Flask-CORS
    - 图像处理：OpenCV + NumPy + PIL
    - 数据库：SQLite3
    - 编程语言：Python 3.x

主要功能：
    1. 图片上传与预处理
    2. AI智能检测精灵图（手动阈值调节 + 自动优化）
    3. 切割框编辑（拖拽、缩放、删除、添加）
    4. 九宫格切割与预览
    5. 精灵图集生成与配置导出
    6. 多游戏引擎配置导出（Unity/Cocos/Unreal）
    7. AI动画序列帧生成
    8. 用户认证与历史记录

目录结构：
    uploads/          - 用户上传的原始图片
    outputs/          - 切割后的输出文件
    database/         - SQLite数据库文件

使用说明：
    1. 安装依赖：pip install -r requirements.txt
    2. 运行服务器：python app.py
    3. 访问地址：http://127.0.0.1:5000
    4. 默认登录：admin / 123456

================================================================================
"""

# ================================================================================
# 导入必要的库
# ================================================================================

from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
import cv2                      # OpenCV - 计算机视觉库，用于图像处理
import numpy as np              # NumPy - 数值计算库，处理矩阵运算
import os                       # 操作系统接口，文件和目录操作
import uuid                     # UUID生成器，用于生成唯一标识符
import json                     # JSON数据处理
import sqlite3                  # SQLite数据库接口
import hashlib                  # 哈希算法，用于密码加密
import datetime                 # 日期时间处理
import urllib.request           # URL请求库，用于API调用
import urllib.error             # URL错误处理
import base64                   # Base64编码/解码
from io import BytesIO          # 内存中的二进制流
from PIL import Image           # PIL图像库，提供高级图像处理

# ================================================================================
# 应用配置与全局变量
# ================================================================================

app = Flask(__name__)
app.secret_key = 'game-tool-secret-key-2026'  # Flask会话加密密钥
CORS(app, origins="*", supports_credentials=True)  # 允许跨域请求

# ------------------------------------------------------------------------------
# 路径配置
# ------------------------------------------------------------------------------
UPLOAD_FOLDER = 'uploads'     # 用户上传图片的存储目录
OUTPUT_FOLDER = 'outputs'     # 切割/处理后文件的输出目录
DB_FOLDER = 'database'        # 数据库文件存储目录

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(DB_FOLDER, exist_ok=True)

# 数据库完整路径
DATABASE = os.path.join(DB_FOLDER, 'game_tool.db')

# ------------------------------------------------------------------------------
# 全局状态变量（用于存储当前会话的图像处理状态）
# 注意：在生产环境中应使用数据库或Redis来管理状态
# ------------------------------------------------------------------------------
current_image = None          # 当前上传的图片信息（路径、尺寸、透明度等）
cut_boxes = []                # 当前检测到的切割框列表
nine_patch = {                # 九宫格切割的边距配置
    'left': 20,               # 左边距（像素）
    'top': 20,                # 上边距（像素）
    'right': 20,              # 右边距（像素）
    'bottom': 20              # 下边距（像素）
}

# ================================================================================
# 数据库操作函数
# ================================================================================

def init_db():
    """
    初始化数据库，创建必要的表
    
    功能说明：
        - 创建用户表（users）：存储用户账号信息
        - 创建历史记录表（history）：存储用户的操作历史
    
    表结构：
        users: id, username, password(加密), email, created_at
        history: id, user_id, filename, file_size, boxes_count, nine_patch配置, exported_files, created_at
    """
    conn = sqlite3.connect(DATABASE)  # 连接数据库（自动创建如果不存在）
    c = conn.cursor()
    
    # ------------------------------------------------------------------------------
    # 创建用户表
    # ------------------------------------------------------------------------------
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ------------------------------------------------------------------------------
    # 创建历史记录表
    # ------------------------------------------------------------------------------
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_size INTEGER,
            boxes_count INTEGER DEFAULT 0,
            nine_patch TEXT,
            exported_files TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()  # 提交事务
    conn.close()   # 关闭连接

# 初始化数据库
init_db()

# ------------------------------------------------------------------------------
# 用户认证相关函数
# ------------------------------------------------------------------------------

def hash_password(password):
    """
    密码哈希加密函数
    
    Args:
        password (str): 明文密码
    
    Returns:
        str: SHA256哈希后的密码（十六进制字符串）
    
    说明：使用SHA256算法进行单向哈希加密，安全性高于MD5
    """
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(username):
    """
    根据用户名查询用户信息
    
    Args:
        username (str): 用户名
    
    Returns:
        tuple/None: 用户记录元组，格式为 (id, username, password, email, created_at)
                    如果用户不存在则返回None
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(username, password, email=None):
    """
    添加新用户
    
    Args:
        username (str): 用户名
        password (str): 明文密码（将被自动加密）
        email (str, optional): 电子邮箱
    
    Returns:
        bool: 添加成功返回True，用户名已存在返回False
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        # 密码使用SHA256加密存储
        c.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                  (username, hash_password(password), email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # 用户名已存在，违反唯一约束
        return False
    finally:
        conn.close()

# ------------------------------------------------------------------------------
# 创建默认管理员账户
# ------------------------------------------------------------------------------

default_user = get_user('admin')
if not default_user:
    add_user('admin', '123456', 'admin@example.com')
    print('已创建默认用户：admin / 123456')

# ------------------------------------------------------------------------------
# 历史记录管理函数
# ------------------------------------------------------------------------------

def add_history(user_id, filename, file_size, boxes_count=0, nine_patch=None, exported_files=None):
    """
    添加历史记录
    
    Args:
        user_id (int): 用户ID
        filename (str): 处理的文件名
        file_size (int): 文件大小（字节）
        boxes_count (int, optional): 检测到的切割框数量
        nine_patch (dict, optional): 九宫格配置
        exported_files (list, optional): 导出的文件列表
    
    Returns:
        None
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('INSERT INTO history (user_id, filename, file_size, boxes_count, nine_patch, exported_files) VALUES (?, ?, ?, ?, ?, ?)',
              (user_id, filename, file_size, boxes_count, json.dumps(nine_patch) if nine_patch else None, json.dumps(exported_files) if exported_files else None))
    conn.commit()
    conn.close()

def get_history(user_id, limit=20):
    """
    获取用户的历史记录
    
    Args:
        user_id (int): 用户ID
        limit (int, optional): 返回记录数量限制，默认20条
    
    Returns:
        list: 历史记录列表，每条记录为字典格式
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT * FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?', (user_id, limit))
    rows = c.fetchall()
    conn.close()
    history = []
    for row in rows:
        history.append({
            'id': row[0],
            'user_id': row[1],
            'filename': row[2],
            'file_size': row[3],
            'boxes_count': row[4],
            'nine_patch': json.loads(row[5]) if row[5] else None,
            'exported_files': json.loads(row[6]) if row[6] else None,
            'created_at': row[7]
        })
    return history

def delete_history(history_id, user_id):
    """
    删除指定的历史记录
    
    Args:
        history_id (int): 历史记录ID
        user_id (int): 用户ID（用于权限验证）
    
    Returns:
        bool: 删除成功返回True，记录不存在返回False
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('DELETE FROM history WHERE id = ? AND user_id = ?', (history_id, user_id))
    conn.commit()
    conn.close()
    return c.rowcount > 0

# ================================================================================
# Flask路由 - 页面渲染
# ================================================================================

@app.route('/')
def index():
    """
    首页路由 - 渲染主工作台页面
    
    Returns:
        HTML: index.html模板
    """
    return render_template('index.html')

@app.route('/mobile')
def mobile():
    """移动端页面路由"""
    return render_template('mobile.html')

@app.route('/ai-slicing')
def ai_slicing():
    """AI智能切割页面路由"""
    return render_template('ai-slicing.html')

@app.route('/spritesheet')
def spritesheet_page():
    """精灵图生成页面路由"""
    return render_template('spritesheet.html')

@app.route('/nine-patch')
def nine_patch_page():
    """九宫格切割页面路由"""
    return render_template('nine-patch.html')

@app.route('/export')
def export_page():
    """导出配置页面路由"""
    return render_template('export.html')

@app.route('/animation')
def animation_page():
    """AI动画生成页面路由"""
    return render_template('animation.html')

# ================================================================================
# Flask路由 - 图片上传与预处理
# ================================================================================

@app.route('/upload', methods=['POST'])
def upload():
    """
    图片上传接口
    
    功能：
        1. 接收前端上传的图片文件
        2. 保存到服务器uploads目录
        3. 使用OpenCV读取图片，获取尺寸和透明度信息
        4. 返回图片信息供前端展示
    
    请求格式：
        multipart/form-data: file (图片文件)
    
    返回值：
        JSON: {
            'path': 文件路径,
            'width': 图片宽度,
            'height': 图片高度,
            'filename': 文件名,
            'has_alpha': 是否有Alpha通道(透明度)
        }
    
    错误处理：
        - 400: 未上传文件
        - 400: 无法读取图片
    """
    global current_image
    
    # ------------------------------------------------------------------------------
    # 检查文件是否上传
    # ------------------------------------------------------------------------------
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # ------------------------------------------------------------------------------
    # 保存文件到服务器
    # ------------------------------------------------------------------------------
    filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]  # 使用UUID生成唯一文件名
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # ------------------------------------------------------------------------------
    # 使用OpenCV读取图片并获取信息
    # ------------------------------------------------------------------------------
    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)  # IMREAD_UNCHANGED保持Alpha通道
    if img is None:
        return jsonify({'error': 'Cannot read image file'}), 400

    height, width = img.shape[:2]
    has_alpha = len(img.shape) == 3 and img.shape[2] == 4  # 检查是否有4通道(RGBA)

    # ------------------------------------------------------------------------------
    # 更新全局状态
    # ------------------------------------------------------------------------------
    current_image = {
        'path': filepath,
        'width': width,
        'height': height,
        'filename': filename,
        'has_alpha': has_alpha
    }

    return jsonify(current_image)

# ================================================================================
# 图像处理核心函数
# ================================================================================

def get_content_mask(img):
    """
    生成内容掩码 - 识别图像中的有效内容区域
    
    算法说明：
        对于带透明通道的PNG图片：使用Alpha通道生成掩码
        对于普通图片（无Alpha通道）：检测接近白色的区域作为背景并反转
    
    Args:
        img (numpy.ndarray): 输入图像（BGR或BGRA格式）
    
    Returns:
        numpy.ndarray: 二值掩码图像（255=内容，0=背景）
    
    处理步骤：
        1. 形态学闭运算去除小孔洞
        2. 阈值分割分离前景和背景
        3. 连通域分析确保掩码连续性
    """
    if len(img.shape) == 3 and img.shape[2] == 4:
        # ------------------------------------------------------------------------------
        # PNG图片：使用Alpha通道
        # ------------------------------------------------------------------------------
        alpha = img[:, :, 3]  # 获取Alpha通道
        _, mask = cv2.threshold(alpha, 0, 255, cv2.THRESH_BINARY)  # 阈值分割
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # 闭运算填补小孔洞
        return mask
    else:
        # ------------------------------------------------------------------------------
        # 普通图片：检测白色背景
        # ------------------------------------------------------------------------------
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # 转换为灰度图
        _, mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)  # 阈值245以上视为白色背景
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # 闭运算
        return mask

def detect_sprites(img, min_area, mode='external'):
    """
    精灵图检测函数 - 使用OpenCV轮廓检测识别精灵图
    
    算法说明：
        1. 生成内容掩码（区分前景和背景）
        2. 使用findContours查找连通域
        3. 根据面积过滤，去除噪声
        4. 返回所有检测到的精灵图位置信息
    
    Args:
        img (numpy.ndarray): 输入图像
        min_area (int): 最小面积阈值，小于此面积的轮廓会被忽略
        mode (str): 轮廓检索模式
            - 'external': 仅外部轮廓（默认，适合分离的精灵图）
            - 'hierarchical': 所有轮廓（适合嵌套结构）
    
    Returns:
        list: 检测到的精灵图列表，每个元素包含：
            - x, y: 左上角坐标
            - width, height: 宽高
            - area: 轮廓面积
    
    排序规则：
        按从上到下、从左到右的顺序排列（先比较y坐标，再比较x坐标）
    """
    # ------------------------------------------------------------------------------
    # Step 1: 生成掩码
    # ------------------------------------------------------------------------------
    mask = get_content_mask(img)
    
    # ------------------------------------------------------------------------------
    # Step 2: 查找轮廓
    # ------------------------------------------------------------------------------
    if mode == 'hierarchical':
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    else:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # ------------------------------------------------------------------------------
    # Step 3: 过滤并提取包围盒
    # ------------------------------------------------------------------------------
    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)  # 计算轮廓面积
        if area > min_area:  # 面积阈值过滤
            x, y, w, h = cv2.boundingRect(cnt)  # 获取最小包围矩形
            boxes.append({
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'area': int(area)
            })

    # ------------------------------------------------------------------------------
    # Step 4: 按位置排序（从上到下，从左到右）
    # ------------------------------------------------------------------------------
    boxes.sort(key=lambda b: (b['y'], b['x']))
    return boxes

# ================================================================================
# Flask路由 - 精灵图检测
# ================================================================================

@app.route('/detect', methods=['POST'])
def detect():
    """
    手动检测接口 - 用户手动设置参数进行精灵图检测
    
    功能：
        接收用户设置的参数（最小面积、检测模式），执行精灵图检测
    
    请求格式：
        JSON: {
            'min_area': 最小面积阈值,
            'mode': 'external'或'hierarchical'
        }
    
    返回值：
        JSON: {
            'boxes': 检测到的切割框列表,
            'count': 数量,
            'mode': 使用的检测模式,
            'min_area': 使用的最小面积,
            'method': '手动检测'
        }
    """
    global current_image, cut_boxes
    
    if not current_image:
        return jsonify({'error': 'No image uploaded'}), 400

    try:
        data = request.json
        min_area = data.get('min_area', 50)
        mode = data.get('mode', 'external')

        img = cv2.imread(current_image['path'], cv2.IMREAD_UNCHANGED)
        cut_boxes = detect_sprites(img, min_area, mode)

        return jsonify({
            'boxes': cut_boxes,
            'count': len(cut_boxes),
            'mode': mode,
            'min_area': min_area,
            'method': '手动检测'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auto-detect', methods=['POST'])
def auto_detect():
    """
    AI自动检测接口 - 自动优化参数进行精灵图检测
    
    算法说明：
        使用网格搜索尝试不同的参数组合，选择最优参数
        评分函数：数量得分（70%）+ 均匀度得分（30%）
        目标：检测到数量适中、大小均匀的精灵图
    
    请求格式：
        无需参数
    
    返回值：
        JSON: {
            'boxes': 检测到的切割框列表,
            'count': 数量,
            'method': 'AI自动检测',
            'params': 使用的最优参数,
            'optimized': True
        }
    
    参数搜索空间：
        - 最小面积: [10, 20, 30, 50, 80, 100, 150, 200]
        - 检测模式: ['external', 'hierarchical']
    
    优化策略：
        1. 遍历所有参数组合
        2. 计算每个组合的评分
        3. 选择评分最高的参数组合
        4. 评分 = 精灵图数量×0.7 + 均匀度系数×0.3
    """
    global current_image, cut_boxes
    if not current_image:
        return jsonify({'error': 'No image uploaded'}), 400

    try:
        img = cv2.imread(current_image['path'], cv2.IMREAD_UNCHANGED)

        best_boxes = []
        best_score = 0
        best_params = {}

        # ------------------------------------------------------------------------------
        # Step 1: 定义参数搜索空间
        # ------------------------------------------------------------------------------
        min_areas = [10, 20, 30, 50, 80, 100, 150, 200]
        modes = ['external', 'hierarchical']

        # ------------------------------------------------------------------------------
        # Step 2: 网格搜索最优参数
        # ------------------------------------------------------------------------------
        for mode in modes:
            for min_area in min_areas:
                boxes = detect_sprites(img, min_area, mode)
                count = len(boxes)

                # 计算精灵图大小的方差
                area_variance = np.var([b['area'] for b in boxes]) if boxes else 0
                avg_area = np.mean([b['area'] for b in boxes]) if boxes else 0

                # 计算变异系数（CV = 标准差/平均值），CV越小表示大小越均匀
                if avg_area > 0:
                    cv = np.sqrt(area_variance) / avg_area
                else:
                    cv = 0

                # ------------------------------------------------------------------------------
                # Step 3: 计算评分函数
                # ------------------------------------------------------------------------------
                # 评分 = 数量得分（精灵图数量不能太多也不能太少）+ 均匀度得分
                # 数量得分：数量越多得分越高，但上限500个
                # 均匀度得分：(1 - CV)，CV越小越均匀，得分越高
                score = count * 0.7 + (1 - min(cv, 1)) * 0.3

                # 选择评分最高且数量合理的参数组合
                if score > best_score and count <= 500 and count > 0:
                    best_score = score
                    best_boxes = boxes
                    best_params = {'mode': mode, 'min_area': min_area}

        # ------------------------------------------------------------------------------
        # Step 4: Fallback处理
        # ------------------------------------------------------------------------------
        if not best_boxes:
            best_boxes = detect_sprites(img, 50, 'external')
            best_params = {'mode': 'external', 'min_area': 50}

        cut_boxes = best_boxes

        return jsonify({
            'boxes': cut_boxes,
            'count': len(cut_boxes),
            'method': 'AI自动检测',
            'params': best_params,
            'optimized': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update-ninepatch', methods=['POST'])
def update_ninepatch():
    global nine_patch
    try:
        data = request.json
        nine_patch = {
            'left': data.get('left', 20),
            'top': data.get('top', 20),
            'right': data.get('right', 20),
            'bottom': data.get('bottom', 20)
        }
        return jsonify(nine_patch)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_transparent_sprite(img, box):
    x, y, w, h = box['x'], box['y'], box['width'], box['height']
    crop = img[y:y+h, x:x+w].copy()

    if len(crop.shape) == 2:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGRA)

    if len(crop.shape) == 3:
        if crop.shape[2] == 3:
            crop = cv2.cvtColor(crop, cv2.COLOR_BGR2BGRA)

        gray = cv2.cvtColor(crop[:, :, :3], cv2.COLOR_BGR2GRAY)
        _, background_mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)
        
        lower_white = np.array([240, 240, 240])
        upper_white = np.array([255, 255, 255])
        white_mask = cv2.inRange(crop[:, :, :3], lower_white, upper_white)
        
        combined_mask = cv2.bitwise_or(background_mask, white_mask)
        crop[:, :, 3] = cv2.bitwise_not(combined_mask)

    return crop

@app.route('/cut', methods=['POST'])
def cut():
    global current_image, cut_boxes
    if not current_image or not cut_boxes:
        return jsonify({'error': 'No data to process'}), 400

    try:
        img = cv2.imread(current_image['path'], cv2.IMREAD_UNCHANGED)
        output_files = []

        for i, box in enumerate(cut_boxes):
            sprite = create_transparent_sprite(img, box)
            output_name = f'sprite_{i:03d}.png'
            output_path = os.path.join(OUTPUT_FOLDER, output_name)
            cv2.imwrite(output_path, sprite, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            output_files.append(output_name)

        config = {
            'source': current_image['filename'],
            'width': current_image['width'],
            'height': current_image['height'],
            'nine_patch': nine_patch,
            'sprites': cut_boxes,
            'output_files': output_files,
            'output_dir': OUTPUT_FOLDER,
            'transparent': True
        }

        config_path = os.path.join(OUTPUT_FOLDER, 'spritesheet.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'count': len(output_files),
            'output_dir': OUTPUT_FOLDER,
            'config': config
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export-selected', methods=['POST'])
def export_selected():
    global current_image, cut_boxes
    if not current_image or not cut_boxes:
        return jsonify({'error': 'No data to process'}), 400

    try:
        data = request.json
        cut_images = data.get('cut_images', False)
        nine_patch = data.get('nine_patch', False)
        spritesheet = data.get('spritesheet', False)
        config = data.get('config', False)
        nine_patch_params = data.get('nine_patch_params', {'left': 20, 'right': 20, 'top': 20, 'bottom': 20})

        img = cv2.imread(current_image['path'], cv2.IMREAD_UNCHANGED)
        output_files = []
        spritesheet_data = None

        if cut_images:
            for i, box in enumerate(cut_boxes):
                sprite = create_transparent_sprite(img, box)
                output_name = f'sprite_{i:03d}.png'
                output_path = os.path.join(OUTPUT_FOLDER, output_name)
                cv2.imwrite(output_path, sprite, [cv2.IMWRITE_PNG_COMPRESSION, 9])
                output_files.append(output_name)

        if nine_patch:
            left = nine_patch_params.get('left', 20)
            right = nine_patch_params.get('right', 20)
            top = nine_patch_params.get('top', 20)
            bottom = nine_patch_params.get('bottom', 20)

            if len(img.shape) == 3 and img.shape[2] == 3:
                img_bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            else:
                img_bgra = img

            h, w = img_bgra.shape[:2]
            regions = [
                {'name': 'tl', 'x': 0, 'y': 0, 'w': left, 'h': top},
                {'name': 't', 'x': left, 'y': 0, 'w': w - left - right, 'h': top},
                {'name': 'tr', 'x': w - right, 'y': 0, 'w': right, 'h': top},
                {'name': 'l', 'x': 0, 'y': top, 'w': left, 'h': h - top - bottom},
                {'name': 'c', 'x': left, 'y': top, 'w': w - left - right, 'h': h - top - bottom},
                {'name': 'r', 'x': w - right, 'y': top, 'w': right, 'h': h - top - bottom},
                {'name': 'bl', 'x': 0, 'y': h - bottom, 'w': left, 'h': bottom},
                {'name': 'b', 'x': left, 'y': h - bottom, 'w': w - left - right, 'h': bottom},
                {'name': 'br', 'x': w - right, 'y': h - bottom, 'w': right, 'h': bottom}
            ]

            for region in regions:
                rx, ry, rw, rh = region['x'], region['y'], region['w'], region['h']
                if rw > 0 and rh > 0:
                    crop = img_bgra[ry:ry+rh, rx:rx+rw].copy()
                    output_name = f'ninepatch_{region["name"]}.png'
                    output_path = os.path.join(OUTPUT_FOLDER, output_name)
                    cv2.imwrite(output_path, crop, [cv2.IMWRITE_PNG_COMPRESSION, 9])
                    output_files.append(output_name)

        if spritesheet:
            padding = 2
            sheet_width = 1024

            sorted_boxes = sorted(cut_boxes, key=lambda b: (-b['height'], -b['width']))
            total_width = sum(b['width'] for b in sorted_boxes) + padding * (len(sorted_boxes) + 1)
            rows = max(1, (total_width + sheet_width - 1) // sheet_width)
            max_height = max(b['height'] for b in sorted_boxes) if sorted_boxes else 1
            sheet_height = rows * (max_height + padding) + padding

            spritesheet_img = np.zeros((sheet_height, sheet_width, 4), dtype=np.uint8)
            sprite_data = []
            current_x, current_y = padding, padding

            for i, box in enumerate(sorted_boxes):
                if current_x + box['width'] > sheet_width:
                    current_x = padding
                    current_y += max_height + padding

                sprite = create_transparent_sprite(img, box)
                h_sprite, w_sprite = sprite.shape[:2]

                y_end = min(current_y + h_sprite, sheet_height)
                x_end = min(current_x + w_sprite, sheet_width)
                actual_h = y_end - current_y
                actual_w = x_end - current_x

                spritesheet_img[current_y:y_end, current_x:x_end] = sprite[:actual_h, :actual_w]

                sprite_data.append({
                    'name': f'sprite_{i:03d}',
                    'x': current_x,
                    'y': current_y,
                    'width': actual_w,
                    'height': actual_h
                })

                current_x += w_sprite + padding

            sheet_path = os.path.join(OUTPUT_FOLDER, 'spritesheet.png')
            cv2.imwrite(sheet_path, spritesheet_img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            output_files.append('spritesheet.png')

            spritesheet_data = {
                'filename': 'spritesheet.png',
                'spriteCount': len(sprite_data),
                'width': sheet_width,
                'height': sheet_height,
                'padding': padding
            }

        if config:
            if cut_images or nine_patch:
                config_data = {
                    'source': current_image['filename'],
                    'width': current_image['width'],
                    'height': current_image['height'],
                    'nine_patch': nine_patch_params,
                    'sprites': cut_boxes,
                    'output_files': output_files,
                    'output_dir': OUTPUT_FOLDER,
                    'transparent': True
                }
                config_path = os.path.join(OUTPUT_FOLDER, 'spritesheet.json')
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                output_files.append('spritesheet.json')

            if spritesheet_data:
                atlas_config = {
                    'image': 'spritesheet.png',
                    'width': spritesheet_data['width'],
                    'height': spritesheet_data['height'],
                    'padding': spritesheet_data['padding'],
                    'sprites': sprite_data,
                    'transparent': True
                }
                atlas_path = os.path.join(OUTPUT_FOLDER, 'spritesheet_atlas.json')
                with open(atlas_path, 'w', encoding='utf-8') as f:
                    json.dump(atlas_config, f, ensure_ascii=False, indent=2)
                output_files.append('spritesheet_atlas.json')

        return jsonify({
            'success': True,
            'output_files': output_files,
            'spritesheet_data': spritesheet_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate-spritesheet', methods=['POST'])
def generate_spritesheet():
    global current_image, cut_boxes
    if not current_image or not cut_boxes:
        return jsonify({'error': 'No data to process'}), 400

    try:
        data = request.json
        padding = data.get('padding', 2)
        sheet_width = data.get('width', 1024)

        img = cv2.imread(current_image['path'], cv2.IMREAD_UNCHANGED)

        sorted_boxes = sorted(cut_boxes, key=lambda b: (-b['height'], -b['width']))

        total_width = sum(b['width'] for b in sorted_boxes) + padding * (len(sorted_boxes) + 1)
        rows = max(1, (total_width + sheet_width - 1) // sheet_width)

        max_height = max(b['height'] for b in sorted_boxes) if sorted_boxes else 1
        sheet_height = rows * (max_height + padding) + padding

        spritesheet = np.zeros((sheet_height, sheet_width, 4), dtype=np.uint8)
        sprite_data = []

        current_x, current_y = padding, padding

        for i, box in enumerate(sorted_boxes):
            if current_x + box['width'] > sheet_width:
                current_x = padding
                current_y += max_height + padding

            sprite = create_transparent_sprite(img, box)
            h, w = sprite.shape[:2]

            y_end = min(current_y + h, sheet_height)
            x_end = min(current_x + w, sheet_width)
            actual_h = y_end - current_y
            actual_w = x_end - current_x

            spritesheet[current_y:y_end, current_x:x_end] = sprite[:actual_h, :actual_w]

            sprite_data.append({
                'name': f'sprite_{i:03d}',
                'x': current_x,
                'y': current_y,
                'width': actual_w,
                'height': actual_h,
                'source_box': box
            })

            current_x += w + padding

        sheet_path = os.path.join(OUTPUT_FOLDER, 'spritesheet.png')
        cv2.imwrite(sheet_path, spritesheet, [cv2.IMWRITE_PNG_COMPRESSION, 9])

        config = {
            'image': 'spritesheet.png',
            'width': sheet_width,
            'height': sheet_height,
            'padding': padding,
            'sprites': sprite_data,
            'transparent': True
        }

        config_path = os.path.join(OUTPUT_FOLDER, 'spritesheet_atlas.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'spritesheet': 'spritesheet.png',
            'sprite_count': len(sprite_data),
            'config': config
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ninepatch-export', methods=['POST'])
def ninepatch_export():
    global current_image, nine_patch
    if not current_image:
        return jsonify({'error': 'No image uploaded'}), 400

    try:
        data = request.json
        left = data.get('left', 20)
        right = data.get('right', 20)
        top = data.get('top', 20)
        bottom = data.get('bottom', 20)
        sprite = data.get('sprite', None)

        img = cv2.imread(current_image['path'], cv2.IMREAD_UNCHANGED)

        if len(img.shape) == 3 and img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

        if sprite:
            sx, sy, sw, sh = sprite['x'], sprite['y'], sprite['width'], sprite['height']
            sprite_img = img[sy:sy+sh, sx:sx+sw].copy()
            h, w = sh, sw
        else:
            sprite_img = img
            h, w = img.shape[:2]

        regions = [
            {'name': 'tl', 'x': 0, 'y': 0, 'w': left, 'h': top},
            {'name': 't', 'x': left, 'y': 0, 'w': w - left - right, 'h': top},
            {'name': 'tr', 'x': w - right, 'y': 0, 'w': right, 'h': top},
            {'name': 'l', 'x': 0, 'y': top, 'w': left, 'h': h - top - bottom},
            {'name': 'c', 'x': left, 'y': top, 'w': w - left - right, 'h': h - top - bottom},
            {'name': 'r', 'x': w - right, 'y': top, 'w': right, 'h': h - top - bottom},
            {'name': 'bl', 'x': 0, 'y': h - bottom, 'w': left, 'h': bottom},
            {'name': 'b', 'x': left, 'y': h - bottom, 'w': w - left - right, 'h': bottom},
            {'name': 'br', 'x': w - right, 'y': h - bottom, 'w': right, 'h': bottom}
        ]

        output_files = []
        for region in regions:
            rx, ry, rw, rh = region['x'], region['y'], region['w'], region['h']
            if rw > 0 and rh > 0:
                crop = sprite_img[ry:ry+rh, rx:rx+rw].copy()
                sprite_index = sprite.get('index', '') if sprite else ''
                suffix = f'_sprite{sprite_index}' if sprite_index else ''
                output_name = f'ninepatch_{region["name"]}{suffix}.png'
                output_path = os.path.join(OUTPUT_FOLDER, output_name)
                cv2.imwrite(output_path, crop, [cv2.IMWRITE_PNG_COMPRESSION, 9])
                output_files.append(output_name)

        config = {
            'source': current_image['filename'],
            'sprite': sprite,
            'nine_patch': {'left': left, 'top': top, 'right': right, 'bottom': bottom},
            'regions': regions,
            'output_files': output_files,
            'transparent': True
        }

        config_path = os.path.join(OUTPUT_FOLDER, 'ninepatch_config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'output_files': output_files,
            'nine_patch': {'left': left, 'top': top, 'right': right, 'bottom': bottom},
            'config': config
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/preview/<filename>')
def preview(filename):
    try:
        if filename == 'folder':
            import subprocess
            subprocess.Popen(['explorer', os.path.abspath(OUTPUT_FOLDER)])
            return jsonify({'success': True, 'message': '已打开输出文件夹'})
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            filepath = os.path.join(OUTPUT_FOLDER, filename)
        return send_file(filepath, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/get-outputs')
def get_outputs():
    try:
        files = []
        for f in os.listdir(OUTPUT_FOLDER):
            if f.endswith('.png') or f.endswith('.json') or f.endswith('.plist') or f.endswith('.ini') or f.endswith('.meta') or f.endswith('.prefab'):
                files.append(f)
        return jsonify({'files': files, 'count': len(files)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-output-path')
def get_output_path():
    try:
        abs_path = os.path.abspath(OUTPUT_FOLDER)
        return jsonify({'path': abs_path, 'folder': OUTPUT_FOLDER})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_unity_spriteatlas_config(spritesheet_path, sprites, padding=4):
    with open(spritesheet_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    atlas_name = 'SpriteAtlas'
    atlas_config = {
        'm_Name': atlas_name,
        'm_SpritePackerMode': 1,
        'm_TextureSettings': {
            'm_TextureCompression': 0,
            'm_FilterMode': 1,
            'm_Aniso': 1,
            'm_MipmapEnabled': False,
            'm_WrapMode': 1,
            'm_ExtrudeEdges': 1,
            'm_SpriteMeshType': 1,
            'm_GenerateFallbackPhysicsShape': True
        },
        'm_PackingSettings': {
            'm_Padding': padding,
            'm_InnerPadding': padding,
            'm_AllowRotation': True,
            'm_TightPacking': True,
            'm_EnableTightPacking': True,
            'm_UseAlphaTest': False,
            'm_IsRectPacking': True
        },
        'm_AtlasSettings': {
            'm_IncludeInBuild': True,
            'm_IsVariant': False,
            'm_VariantParent': None,
            'm_VariantParentEditorOnly': False,
            'm_PreviewSprite': None,
            'm_Tag': '',
            'm_EditorData': {
                'm_Labels': [],
                'm_TextureImporterOverride': {}
            }
        },
        'm_ManagedTextures': [],
        'm_Objects': []
    }
    
    for sprite in data['sprites']:
        atlas_config['m_Objects'].append({
            'm_Object': {
                'name': sprite['name'],
                'x': sprite['x'],
                'y': sprite['y'],
                'width': sprite['width'],
                'height': sprite['height'],
                'pivot_x': 0.5,
                'pivot_y': 0.5,
                'border': [0, 0, 0, 0]
            }
        })
    
    return atlas_config

def generate_unity_meta_file(filename, guid):
    meta = {
        'guid': guid,
        'fileFormatVersion': 2,
        'TextImporter': {
            'externalObjects': {},
            'userData': '',
            'assetBundleName': '',
            'assetBundleVariant': '',
            'textureType': 8,
            'textureShape': 1,
            'mipmap': {'enable': False},
            'linearTexture': False,
            'srgbTexture': True,
            'alphaIsTransparency': True,
            'generateMipMaps': False,
            'enableMipMapStreaming': False,
            'textureCompression': 0,
            'compressionQuality': 50,
            'maxTextureSize': 4096,
            'resizeAlgorithm': 1,
            'filterMode': 1,
            'aniso': 1,
            'wrapMode': 1,
            'secondaryTextures': {},
            'platformSettings': [],
            'spriteMode': 2,
            'spriteExtrude': 1,
            'spriteMeshType': 1,
            'alignment': 0,
            'pivot': [0.5, 0.5],
            'border': [0, 0, 0, 0],
            'pixelsPerUnit': 100,
            'generateFallbackPhysicsShape': True,
            'spriteEditorData': {
                'spriteSheet': {
                    'settings': {
                        'border': [0, 0, 0, 0],
                        'pivot': [0.5, 0.5],
                        'extrude': 1,
                        'tessellationDetail': 1,
                        'spriteMeshType': 1,
                        'generateFallbackShape': True
                    },
                    'sprites': []
                }
            },
            'textureFormat': -1,
            'colorSpace': 1,
            'flipbook': {}
        }
    }
    return meta

def generate_cocos_plist(spritesheet_path, spritesheet_png):
    with open(spritesheet_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    plist = {
        'frames': {}
    }
    
    for sprite in data['sprites']:
        plist['frames'][sprite['name'] + '.png'] = {
            'frame': {
                'x': sprite['x'],
                'y': sprite['y'],
                'w': sprite['width'],
                'h': sprite['height']
            },
            'offset': {
                'x': 0,
                'y': 0
            },
            'rotated': False,
            'sourceSize': {
                'w': sprite['width'],
                'h': sprite['height']
            },
            'trimmed': False,
            'spriteOffset': {
                'x': sprite['width'] / 2,
                'y': sprite['height'] / 2
            },
            'spriteSize': {
                'w': sprite['width'],
                'h': sprite['height']
            },
            'spriteSourceSize': {
                'x': 0,
                'y': 0,
                'w': sprite['width'],
                'h': sprite['height']
            }
        }
    
    plist['metadata'] = {
        'format': 3,
        'textureFileName': spritesheet_png,
        'size': {
            'w': data['width'],
            'h': data['height']
        },
        'realTextureFileName': spritesheet_png,
        'smartUpdateHash': '0'
    }
    
    return plist

def generate_cocos_json(spritesheet_path, spritesheet_png):
    with open(spritesheet_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cocos_data = {
        'texture': spritesheet_png,
        'width': data['width'],
        'height': data['height'],
        'frames': []
    }
    
    for sprite in data['sprites']:
        cocos_data['frames'].append({
            'name': sprite['name'],
            'frame': {
                'x': sprite['x'],
                'y': sprite['y'],
                'width': sprite['width'],
                'height': sprite['height']
            },
            'offset': [0, 0],
            'rotated': False,
            'sourceSize': [sprite['width'], sprite['height']],
            'trimmed': False,
            'spriteOffset': [sprite['width'] / 2, sprite['height'] / 2],
            'spriteSize': [sprite['width'], sprite['height']],
            'spriteSourceSize': [0, 0, sprite['width'], sprite['height']]
        })
    
    return cocos_data

def dict_to_plist(data, indent=0):
    spaces = '    ' * indent
    result = ''
    
    if isinstance(data, dict):
        result += spaces + '<dict>\n'
        for key, value in sorted(data.items()):
            result += spaces + '    <key>' + str(key) + '</key>\n'
            result += dict_to_plist(value, indent + 1)
        result += spaces + '</dict>\n'
    elif isinstance(data, list):
        result += spaces + '<array>\n'
        for item in data:
            result += dict_to_plist(item, indent + 1)
        result += spaces + '</array>\n'
    elif isinstance(data, bool):
        result += spaces + '<' + ('true' if data else 'false') + '/>\n'
    elif isinstance(data, (int, float)):
        result += spaces + '<integer>' + str(int(data)) + '</integer>\n'
    else:
        result += spaces + '<string>' + str(data) + '</string>\n'
    
    return result

def generate_plist_xml(data):
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
    xml += '<plist version="1.0">\n'
    xml += dict_to_plist(data)
    xml += '</plist>'
    return xml

def generate_unreal_texture2d_config(sprite_name, width, height):
    config = {
        'asset': {
            'name': sprite_name,
            'class': 'Texture2D',
            'properties': {
                'CompressionSettings': 'TC_Default',
                'Filter': 'TF_Default',
                'MipGenSettings': 'TMGS_Simple',
                'SRGB': True,
                'MaxTextureSize': max(width, height),
                'LODGroup': 'TEXTUREGROUP_UI',
                'NumCinematicMipLevels': 0,
                'bUseAsyncMipTexture': False,
                'bNoTiling': True,
                'AddressX': 'TA_Clamp',
                'AddressY': 'TA_Clamp',
                'bFlipGreenChannel': False,
                'bUseLegacyGamma': False
            }
        }
    }
    return config

def generate_unreal_config(spritesheet_path):
    with open(spritesheet_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    unreal_config = {
        'spritesheet': {
            'texture': {
                'name': 'Spritesheet_Texture',
                'width': data['width'],
                'height': data['height'],
                'compression_settings': 'TC_Default',
                'lod_group': 'TEXTUREGROUP_UI',
                'srgb': True,
                'max_texture_size': max(data['width'], data['height'])
            },
            'sprites': []
        }
    }
    
    for sprite in data['sprites']:
        unreal_config['spritesheet']['sprites'].append({
            'name': sprite['name'],
            'x': sprite['x'],
            'y': data['height'] - sprite['y'] - sprite['height'],
            'width': sprite['width'],
            'height': sprite['height'],
            'pivot': [0.5, 0.5]
        })
    
    return unreal_config

@app.route('/export-engine-config', methods=['POST'])
def export_engine_config():
    global current_image, cut_boxes
    
    try:
        data = request.json
        engine = data.get('engine', 'unity')
        
        spritesheet_path = os.path.join(OUTPUT_FOLDER, 'spritesheet_atlas.json')
        if not os.path.exists(spritesheet_path):
            return jsonify({'error': '请先生成精灵图'}), 400
        
        output_files = []
        
        if engine == 'unity':
            atlas_config = generate_unity_spriteatlas_config(spritesheet_path, cut_boxes)
            atlas_path = os.path.join(OUTPUT_FOLDER, 'spritesheet_atlas_unity.json')
            with open(atlas_path, 'w', encoding='utf-8') as f:
                json.dump(atlas_config, f, ensure_ascii=False, indent=2)
            output_files.append('spritesheet_atlas_unity.json')
            
            meta_guid = str(uuid.uuid4()).replace('-', '')
            meta_data = generate_unity_meta_file('spritesheet.png', meta_guid)
            meta_path = os.path.join(OUTPUT_FOLDER, 'spritesheet.png.meta')
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)
            output_files.append('spritesheet.png.meta')
            
            unity_prefab = {
                'prefab': {
                    'name': 'SpriteAtlas',
                    'sprites': [],
                    'texture': 'spritesheet.png',
                    'texture_guid': meta_guid
                }
            }
            
            with open(spritesheet_path, 'r', encoding='utf-8') as f:
                sheet_data = json.load(f)
            
            for sprite in sheet_data['sprites']:
                unity_prefab['prefab']['sprites'].append({
                    'name': sprite['name'],
                    'rect': [sprite['x'], sprite['y'], sprite['width'], sprite['height']],
                    'pivot': [0.5, 0.5]
                })
            
            prefab_path = os.path.join(OUTPUT_FOLDER, 'sprite_atlas.prefab')
            with open(prefab_path, 'w', encoding='utf-8') as f:
                json.dump(unity_prefab, f, ensure_ascii=False, indent=2)
            output_files.append('sprite_atlas.prefab')
            
            return jsonify({
                'success': True,
                'engine': 'Unity',
                'files': output_files,
                'message': 'Unity配置导出成功，包含SpriteAtlas配置、.meta文件和Prefab配置'
            })
        
        elif engine == 'cocos':
            plist_data = generate_cocos_plist(spritesheet_path, 'spritesheet.png')
            plist_xml = generate_plist_xml(plist_data)
            plist_path = os.path.join(OUTPUT_FOLDER, 'spritesheet.plist')
            with open(plist_path, 'w', encoding='utf-8') as f:
                f.write(plist_xml)
            output_files.append('spritesheet.plist')
            
            cocos_json_data = generate_cocos_json(spritesheet_path, 'spritesheet.png')
            cocos_json_path = os.path.join(OUTPUT_FOLDER, 'spritesheet_cocos.json')
            with open(cocos_json_path, 'w', encoding='utf-8') as f:
                json.dump(cocos_json_data, f, ensure_ascii=False, indent=2)
            output_files.append('spritesheet_cocos.json')
            
            return jsonify({
                'success': True,
                'engine': 'Cocos2d-x',
                'files': output_files,
                'message': 'Cocos2d-x配置导出成功，包含plist和json两种格式'
            })
        
        elif engine == 'unreal':
            unreal_data = generate_unreal_config(spritesheet_path)
            unreal_path = os.path.join(OUTPUT_FOLDER, 'spritesheet_unreal.json')
            with open(unreal_path, 'w', encoding='utf-8') as f:
                json.dump(unreal_data, f, ensure_ascii=False, indent=2)
            output_files.append('spritesheet_unreal.json')
            
            unreal_ini = f"""; Unreal Engine Texture2D Import Settings
[Texture2D]
CompressionSettings=TC_Default
Filter=TF_Default
MipGenSettings=TMGS_Simple
SRGB=True
MaxTextureSize={max(unreal_data['spritesheet']['texture']['width'], unreal_data['spritesheet']['texture']['height'])}
LODGroup=TEXTUREGROUP_UI
NumCinematicMipLevels=0
bUseAsyncMipTexture=False
bNoTiling=True
AddressX=TA_Clamp
AddressY=TA_Clamp
bFlipGreenChannel=False
"""
            ini_path = os.path.join(OUTPUT_FOLDER, 'spritesheet.uasset.ini')
            with open(ini_path, 'w', encoding='utf-8') as f:
                f.write(unreal_ini)
            output_files.append('spritesheet.uasset.ini')
            
            return jsonify({
                'success': True,
                'engine': 'Unreal Engine',
                'files': output_files,
                'message': 'Unreal Engine配置导出成功，包含纹理配置和精灵数据'
            })
        
        else:
            return jsonify({'error': '不支持的游戏引擎'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')
        
        if not username or not password:
            return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
        
        if len(username) < 3 or len(username) > 20:
            return jsonify({'success': False, 'message': '用户名长度需在3-20个字符之间'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': '密码长度需至少6个字符'}), 400
        
        if add_user(username, password, email):
            return jsonify({'success': True, 'message': '注册成功，请登录'})
        else:
            return jsonify({'success': False, 'message': '用户名已存在'}), 409
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        user = get_user(username)
        if user and user[2] == hash_password(password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return jsonify({
                'success': True,
                'message': '登录成功',
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'email': user[3]
                }
            })
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logout')
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': '已退出登录'})

@app.route('/api/user')
def api_user():
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user': {
                'id': session['user_id'],
                'username': session['username']
            }
        })
    return jsonify({'logged_in': False})

@app.route('/api/history', methods=['GET'])
def api_get_history():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        limit = int(request.args.get('limit', 20))
        history = get_history(session['user_id'], limit)
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/history', methods=['POST'])
def api_add_history():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        data = request.json
        filename = data.get('filename')
        file_size = data.get('file_size', 0)
        boxes_count = data.get('boxes_count', 0)
        nine_patch_data = data.get('nine_patch')
        exported_files = data.get('exported_files')
        
        if not filename:
            return jsonify({'success': False, 'message': '文件名不能为空'}), 400
        
        add_history(session['user_id'], filename, file_size, boxes_count, nine_patch_data, exported_files)
        return jsonify({'success': True, 'message': '历史记录已保存'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/history/<int:history_id>', methods=['DELETE'])
def api_delete_history(history_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        if delete_history(history_id, session['user_id']):
            return jsonify({'success': True, 'message': '历史记录已删除'})
        else:
            return jsonify({'success': False, 'message': '记录不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== AI序列帧动画生成 ====================

ANIMATION_TYPES = {
    'bounce': {'name': '弹跳', 'description': '上下弹跳效果，适合活泼的角色'},
    'breath': {'name': '呼吸', 'description': '缓慢缩放，适合待机状态'},
    'shake': {'name': '抖动', 'description': '左右摇晃，适合受击或紧张状态'},
    'rotate': {'name': '旋转', 'description': '旋转效果，适合道具或硬币'},
    'flash': {'name': '闪烁', 'description': '透明度变化，适合提示或无敌状态'},
    'sway': {'name': '摇摆', 'description': '左右摆动，适合植物或悬挂物'},
    'walk': {'name': '走路', 'description': '模拟走路摆动，适合角色'},
    'zoom': {'name': '脉冲', 'description': '放大缩小脉冲效果，适合按钮或强调'},
    'float': {'name': '漂浮', 'description': '上下漂浮，适合幽灵或飞行物'},
    'squash': {'name': '挤压', 'description': '挤压拉伸，适合卡通弹跳'},
}

@app.route('/api/analyze-sprite', methods=['POST'])
def analyze_sprite():
    """AI分析精灵图，推荐适合的动画类型"""
    try:
        data = request.json
        filename = data.get('filename', '')
        
        if not filename:
            return jsonify({'error': '请提供图片文件名'}), 400
        
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.exists(filepath):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '图片不存在'}), 404
        
        img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
        if img is None:
            return jsonify({'error': '无法读取图片'}), 400
        
        h, w = img.shape[:2]
        
        # 分析图像特征
        has_alpha = len(img.shape) == 3 and img.shape[2] == 4
        aspect_ratio = w / h if h > 0 else 1
        
        # 计算透明度分布
        alpha_ratio = 0.5
        if has_alpha:
            alpha = img[:, :, 3]
            non_transparent = np.count_nonzero(alpha > 10)
            total_pixels = alpha.size
            alpha_ratio = non_transparent / total_pixels if total_pixels > 0 else 0.5
        
        # 计算宽高比特征
        is_tall = aspect_ratio < 0.8
        is_wide = aspect_ratio > 1.2
        is_square = 0.8 <= aspect_ratio <= 1.2
        
        # 基于特征推荐动画
        recommendations = []
        
        # 基础推荐
        recommendations.append({'type': 'breath', 'confidence': 0.9, 'reason': '待机呼吸效果是通用动画'})
        
        if is_square:
            recommendations.append({'type': 'rotate', 'confidence': 0.7, 'reason': '方形图片适合旋转效果'})
            recommendations.append({'type': 'bounce', 'confidence': 0.6, 'reason': '适合弹跳动画'})
        
        if is_tall:
            recommendations.append({'type': 'walk', 'confidence': 0.8, 'reason': '高比例图片可能是角色，适合走路动画'})
            recommendations.append({'type': 'sway', 'confidence': 0.6, 'reason': '适合摇摆效果'})
        
        if is_wide:
            recommendations.append({'type': 'shake', 'confidence': 0.6, 'reason': '宽图适合左右抖动'})
            recommendations.append({'type': 'squash', 'confidence': 0.5, 'reason': '适合挤压拉伸'})
        
        if alpha_ratio < 0.3:
            recommendations.append({'type': 'flash', 'confidence': 0.7, 'reason': '主体突出，适合闪烁强调'})
            recommendations.append({'type': 'zoom', 'confidence': 0.6, 'reason': '适合脉冲放大效果'})
        
        recommendations.append({'type': 'float', 'confidence': 0.5, 'reason': '漂浮效果'})
        
        # 按置信度排序
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        
        return jsonify({
            'success': True,
            'analysis': {
                'width': w,
                'height': h,
                'aspect_ratio': round(aspect_ratio, 2),
                'has_alpha': has_alpha,
                'alpha_ratio': round(alpha_ratio, 2)
            },
            'recommendations': recommendations[:6],
            'all_types': ANIMATION_TYPES
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-animation', methods=['POST'])
def generate_animation():
    """生成序列帧动画"""
    try:
        data = request.json
        filename = data.get('filename', '')
        animation_type = data.get('type', 'breath')
        frame_count = int(data.get('frames', 8))
        params = data.get('params', {})
        
        if not filename:
            return jsonify({'error': '请提供图片文件名'}), 400
        
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.exists(filepath):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '图片不存在'}), 404
        
        img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
        if img is None:
            return jsonify({'error': '无法读取图片'}), 400
        
        h, w = img.shape[:2]
        has_alpha = len(img.shape) == 3 and img.shape[2] == 4
        
        # 确保有alpha通道
        if not has_alpha:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        
        frames = []
        padding = int(max(w, h) * 0.3)
        canvas_w = w + padding * 2
        canvas_h = h + padding * 2
        
        for i in range(frame_count):
            t = i / frame_count
            angle = t * 2 * np.pi
            
            # 创建画布
            canvas = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
            
            # 根据动画类型计算变换
            dx, dy, scale, rot_angle, alpha = 0, 0, 1.0, 0, 1.0
            
            if animation_type == 'bounce':
                bounce_height = params.get('height', 0.2)
                dy = -np.sin(angle) * h * bounce_height
                scale = 1.0 + np.sin(angle) * 0.05
            
            elif animation_type == 'breath':
                breath_scale = params.get('scale', 0.08)
                scale = 1.0 + np.sin(angle) * breath_scale
            
            elif animation_type == 'shake':
                shake_amount = params.get('amount', 0.05)
                dx = np.sin(angle * 3) * w * shake_amount
            
            elif animation_type == 'rotate':
                rot_angle = t * 360
            
            elif animation_type == 'flash':
                flash_min = params.get('min_alpha', 0.3)
                alpha = flash_min + (1 - flash_min) * (0.5 + 0.5 * np.sin(angle * 2))
            
            elif animation_type == 'sway':
                sway_angle = params.get('angle', 10)
                rot_angle = np.sin(angle) * sway_angle
            
            elif animation_type == 'walk':
                walk_bounce = params.get('bounce', 0.08)
                walk_sway = params.get('sway', 3)
                dy = -abs(np.sin(angle)) * h * walk_bounce
                rot_angle = np.sin(angle * 2) * walk_sway
            
            elif animation_type == 'zoom':
                zoom_amount = params.get('amount', 0.15)
                scale = 1.0 + (0.5 + 0.5 * np.sin(angle)) * zoom_amount
            
            elif animation_type == 'float':
                float_height = params.get('height', 0.1)
                dy = np.sin(angle) * h * float_height
                dx = np.cos(angle * 0.5) * w * 0.03
            
            elif animation_type == 'squash':
                squash_amount = params.get('amount', 0.15)
                t_squash = 0.5 + 0.5 * np.sin(angle)
                scale_x = 1.0 + t_squash * squash_amount
                scale_y = 1.0 - t_squash * squash_amount * 0.5
                scale = (scale_x, scale_y)
            
            # 应用变换
            center_x = canvas_w / 2 + dx
            center_y = canvas_h / 2 + dy
            
            if isinstance(scale, tuple):
                sx, sy = scale
            else:
                sx = sy = scale
            
            # 变换矩阵
            M = cv2.getRotationMatrix2D((w/2, h/2), rot_angle, 1.0)
            rotated = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_TRANSPARENT)
            
            # 缩放
            new_w = int(w * sx)
            new_h = int(h * sy)
            if new_w > 0 and new_h > 0:
                scaled = cv2.resize(rotated, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            else:
                scaled = rotated
            
            # 放置到画布
            sh, sw = scaled.shape[:2]
            x = int(center_x - sw / 2)
            y = int(center_y - sh / 2)
            
            x = max(0, min(x, canvas_w - sw))
            y = max(0, min(y, canvas_h - sh))
            
            # 透明度调整
            if alpha < 1.0:
                scaled = scaled.copy()
                scaled[:, :, 3] = (scaled[:, :, 3] * alpha).astype(np.uint8)
            
            # 混合
            if 0 <= y < canvas_h and 0 <= x < canvas_w:
                roi = canvas[y:y+sh, x:x+sw]
                if roi.shape[0] == sh and roi.shape[1] == sw:
                    alpha_s = scaled[:, :, 3] / 255.0
                    alpha_d = roi[:, :, 3] / 255.0
                    for c in range(3):
                        roi[:, :, c] = (scaled[:, :, c] * alpha_s + roi[:, :, c] * alpha_d * (1 - alpha_s)).astype(np.uint8)
                    roi[:, :, 3] = ((alpha_s + alpha_d * (1 - alpha_s)) * 255).astype(np.uint8)
                    canvas[y:y+sh, x:x+sw] = roi
            
            # 裁剪到内容区域
            frames.append(canvas)
        
        # 保存帧
        output_frames = []
        anim_id = str(uuid.uuid4())[:8]
        
        for i, frame in enumerate(frames):
            frame_name = f'anim_{anim_id}_{i:03d}.png'
            frame_path = os.path.join(OUTPUT_FOLDER, frame_name)
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            output_frames.append(frame_name)
        
        # 生成精灵图
        sheet_cols = min(frame_count, 4)
        sheet_rows = (frame_count + sheet_cols - 1) // sheet_cols
        sheet_w = canvas_w * sheet_cols
        sheet_h = canvas_h * sheet_rows
        
        spritesheet = np.zeros((sheet_h, sheet_w, 4), dtype=np.uint8)
        
        for i, frame in enumerate(frames):
            col = i % sheet_cols
            row = i // sheet_cols
            x = col * canvas_w
            y = row * canvas_h
            spritesheet[y:y+canvas_h, x:x+canvas_w] = frame
        
        sheet_name = f'anim_{anim_id}_sheet.png'
        sheet_path = os.path.join(OUTPUT_FOLDER, sheet_name)
        cv2.imwrite(sheet_path, spritesheet, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        
        # 生成JSON配置
        sheet_json = {
            'animation': animation_type,
            'frames': frame_count,
            'width': canvas_w,
            'height': canvas_h,
            'cols': sheet_cols,
            'rows': sheet_rows,
            'spritesheet': sheet_name,
            'frames_list': output_frames
        }
        
        json_name = f'anim_{anim_id}_config.json'
        json_path = os.path.join(OUTPUT_FOLDER, json_name)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(sheet_json, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'animation_id': anim_id,
            'type': animation_type,
            'frames': output_frames,
            'spritesheet': sheet_name,
            'config': json_name,
            'frame_count': frame_count,
            'frame_width': canvas_w,
            'frame_height': canvas_h
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== AI 图像生成（真实API） ====================

DEFAULT_AI_CONFIG = {
    'provider': 'siliconflow',
    'base_url': 'https://api.siliconflow.cn/v1',
    'api_key': '',
    'model': 'black-forest-labs/FLUX.1-schnell',
    'image_model': 'black-forest-labs/FLUX.1-schnell'
}

def get_ai_config():
    """获取AI配置，优先从session中获取用户配置"""
    config = DEFAULT_AI_CONFIG.copy()
    user_config = session.get('ai_config')
    if user_config:
        config.update(user_config)
    return config

def image_to_base64(filepath):
    """将图片文件转换为base64"""
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def base64_to_cv2(b64_str):
    """将base64图片转换为OpenCV格式"""
    if b64_str.startswith('data:image'):
        b64_str = b64_str.split(',')[1]
    img_data = base64.b64decode(b64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    return img

def call_ai_image_generation(prompt, reference_image_path=None, size='512x512', num_images=1):
    """调用AI图像生成API（OpenAI兼容格式）
    
    Args:
        prompt: 提示词
        reference_image_path: 参考图片路径（图生图用）
        size: 图片尺寸，如 '512x512'
        num_images: 生成数量
    
    Returns:
        list: base64格式的图片列表
    """
    config = get_ai_config()
    
    if not config.get('api_key'):
        return None, '未配置API Key，请先在设置中配置'
    
    base_url = config.get('base_url', '').rstrip('/')
    api_key = config.get('api_key', '')
    model = config.get('image_model', config.get('model', ''))
    
    url = f'{base_url}/images/generations'
    
    payload = {
        'model': model,
        'prompt': prompt,
        'n': num_images,
        'size': size,
        'response_format': 'b64_json'
    }
    
    # 如果有参考图片，使用图生图
    if reference_image_path and os.path.exists(reference_image_path):
        pass
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Authorization', f'Bearer {api_key}')
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        images = []
        if 'data' in result:
            for item in result['data']:
                if 'b64_json' in item:
                    images.append(item['b64_json'])
                elif 'url' in item:
                    img_req = urllib.request.Request(item['url'])
                    with urllib.request.urlopen(img_req, timeout=30) as img_resp:
                        img_data = img_resp.read()
                        b64 = base64.b64encode(img_data).decode('utf-8')
                        images.append(b64)
        
        return images, None
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8', errors='ignore') if e.fp else str(e)
        return None, f'API请求失败 (HTTP {e.code}): {error_msg[:200]}'
    except urllib.error.URLError as e:
        return None, f'API连接失败: {str(e)}'
    except Exception as e:
        return None, f'生成失败: {str(e)}'

@app.route('/api/ai-generate-animation', methods=['POST'])
def ai_generate_animation():
    """使用真实AI生成序列帧动画"""
    try:
        data = request.json
        filename = data.get('filename', '')
        prompt = data.get('prompt', '')
        frame_count = int(data.get('frames', 8))
        animation_type = data.get('type', 'custom')
        params = data.get('params', {})
        use_reference = data.get('use_reference', True)
        
        if not filename:
            return jsonify({'error': '请提供图片文件名'}), 400
        
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.exists(filepath):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '图片不存在'}), 404
        
        # 读取参考图获取尺寸
        ref_img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
        if ref_img is None:
            return jsonify({'error': '无法读取参考图片'}), 400
        
        h, w = ref_img.shape[:2]
        
        # 计算生成尺寸（限制在合理范围）
        max_size = 1024
        scale = min(max_size / w, max_size / h, 1)
        gen_w = int(w * scale)
        gen_h = int(h * scale)
        # 调整为64的倍数
        gen_w = (gen_w // 64) * 64
        gen_h = (gen_h // 64) * 64
        size_str = f'{gen_w}x{gen_h}'
        
        # 构建提示词
        base_prompt = prompt if prompt else '2d game sprite, pixel art style'
        
        # 如果选择了预设动画类型，添加到提示词中
        type_prompts = {
            'bounce': 'bouncing animation, jumping up and down',
            'breath': 'breathing animation, gently expanding and contracting',
            'shake': 'shaking animation, trembling left and right',
            'rotate': 'spinning animation, rotating 360 degrees',
            'flash': 'flashing animation, blinking in and out',
            'sway': 'swaying animation, swinging back and forth',
            'walk': 'walking animation, character walking cycle',
            'zoom': 'pulsing animation, zooming in and out',
            'float': 'floating animation, hovering up and down',
            'squash': 'squash and stretch animation, cartoon style'
        }
        
        if animation_type in type_prompts:
            full_prompt = f'{base_prompt}, {type_prompts[animation_type]}, sprite sheet, {frame_count} frames animation sequence'
        else:
            full_prompt = f'{base_prompt}, {frame_count} frames animation sequence, sprite sheet'
        
        # 尝试调用AI生成
        ref_path = filepath if use_reference else None
        images, error = call_ai_image_generation(
            prompt=full_prompt,
            reference_image_path=ref_path,
            size=size_str,
            num_images=frame_count
        )
        
        if error:
            # AI生成失败，fallback到本地变换模式
            return jsonify({
                'success': False,
                'error': error,
                'fallback_available': True
            }), 500
        
        if not images or len(images) == 0:
            return jsonify({
                'success': False,
                'error': 'AI未返回图片',
                'fallback_available': True
            }), 500
        
        # 保存生成的帧
        output_frames = []
        anim_id = str(uuid.uuid4())[:8]
        
        for i, b64_img in enumerate(images[:frame_count]):
            frame_name = f'anim_{anim_id}_{i:03d}.png'
            frame_path = os.path.join(OUTPUT_FOLDER, frame_name)
            
            # 转换并保存
            img = base64_to_cv2(b64_img)
            if img is not None:
                # 调整尺寸为参考图尺寸
                if img.shape[0] != h or img.shape[1] != w:
                    img = cv2.resize(img, (w, h), interpolation=cv2.INTER_LANCZOS4)
                cv2.imwrite(frame_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
                output_frames.append(frame_name)
        
        if len(output_frames) == 0:
            return jsonify({
                'success': False,
                'error': '生成的图片无法解析',
                'fallback_available': True
            }), 500
        
        # 生成精灵图
        actual_frames = len(output_frames)
        sheet_cols = min(actual_frames, 4)
        sheet_rows = (actual_frames + sheet_cols - 1) // sheet_cols
        sheet_w = w * sheet_cols
        sheet_h = h * sheet_rows
        
        spritesheet = np.zeros((sheet_h, sheet_w, 4), dtype=np.uint8)
        
        for i, frame_name in enumerate(output_frames):
            frame_path = os.path.join(OUTPUT_FOLDER, frame_name)
            frame = cv2.imread(frame_path, cv2.IMREAD_UNCHANGED)
            if frame is not None:
                # 确保有alpha通道
                if len(frame.shape) == 2 or frame.shape[2] == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
                
                col = i % sheet_cols
                row = i // sheet_cols
                x = col * w
                y = row * h
                
                # 调整尺寸
                if frame.shape[0] != h or frame.shape[1] != w:
                    frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LANCZOS4)
                
                spritesheet[y:y+h, x:x+w] = frame
        
        sheet_name = f'anim_{anim_id}_sheet.png'
        sheet_path = os.path.join(OUTPUT_FOLDER, sheet_name)
        cv2.imwrite(sheet_path, spritesheet, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        
        # 生成JSON配置
        sheet_json = {
            'animation': animation_type,
            'mode': 'ai',
            'frames': actual_frames,
            'width': w,
            'height': h,
            'cols': sheet_cols,
            'rows': sheet_rows,
            'spritesheet': sheet_name,
            'frames_list': output_frames,
            'prompt': full_prompt
        }
        
        json_name = f'anim_{anim_id}_config.json'
        json_path = os.path.join(OUTPUT_FOLDER, json_name)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(sheet_json, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'animation_id': anim_id,
            'type': animation_type,
            'mode': 'ai',
            'frames': output_frames,
            'spritesheet': sheet_name,
            'config': json_name,
            'frame_count': actual_frames,
            'frame_width': w,
            'frame_height': h,
            'prompt': full_prompt
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'fallback_available': True}), 500

@app.route('/api/save-ai-config', methods=['POST'])
def save_ai_config():
    """保存AI配置到session"""
    try:
        data = request.json
        config = {
            'provider': data.get('provider', 'siliconflow'),
            'base_url': data.get('base_url', ''),
            'api_key': data.get('api_key', ''),
            'model': data.get('model', ''),
            'image_model': data.get('image_model', '')
        }
        session['ai_config'] = config
        return jsonify({'success': True, 'message': '配置已保存'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-ai-config', methods=['GET'])
def get_ai_config_api():
    """获取当前AI配置（不含key）"""
    try:
        config = get_ai_config()
        # 不返回完整的api_key
        if config.get('api_key'):
            config['api_key'] = config['api_key'][:8] + '...' if len(config['api_key']) > 8 else '***'
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-ai-connection', methods=['POST'])
def test_ai_connection():
    """测试AI API连接"""
    try:
        data = request.json
        # 临时使用传入的配置测试
        test_config = {
            'base_url': data.get('base_url', ''),
            'api_key': data.get('api_key', ''),
            'model': data.get('model', data.get('image_model', '')),
            'image_model': data.get('image_model', data.get('model', ''))
        }
        
        if not test_config['api_key']:
            return jsonify({'success': False, 'error': '请输入API Key'})
        
        # 保存到session供后续使用
        session['ai_config'] = {
            'provider': data.get('provider', 'custom'),
            'base_url': test_config['base_url'],
            'api_key': test_config['api_key'],
            'model': test_config['model'],
            'image_model': test_config['image_model']
        }
        
        # 简单测试：调用模型列表接口
        base_url = test_config['base_url'].rstrip('/')
        url = f'{base_url}/models'
        
        try:
            req = urllib.request.Request(url, method='GET')
            req.add_header('Authorization', f'Bearer {test_config["api_key"]}')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    return jsonify({'success': True, 'message': '连接成功'})
                else:
                    return jsonify({'success': False, 'error': f'连接失败: HTTP {response.status}'})
        except urllib.error.HTTPError as e:
            # 401表示key不对，也算连接成功但鉴权失败
            if e.code == 401:
                return jsonify({'success': False, 'error': 'API Key无效'})
            else:
                return jsonify({'success': False, 'error': f'连接失败: HTTP {e.code}'})
        except urllib.error.URLError as e:
            return jsonify({'success': False, 'error': f'连接失败: {str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete-files', methods=['POST'])
def delete_files():
    """删除指定文件"""
    try:
        data = request.json
        files_to_delete = data.get('files', [])
        
        deleted = []
        failed = []
        
        for filename in files_to_delete:
            filepath = os.path.join(OUTPUT_FOLDER, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    deleted.append(filename)
                except Exception as e:
                    failed.append(f'{filename}: {str(e)}')
        
        return jsonify({
            'success': True,
            'deleted': deleted,
            'failed': failed,
            'message': f'成功删除 {len(deleted)} 个文件'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)