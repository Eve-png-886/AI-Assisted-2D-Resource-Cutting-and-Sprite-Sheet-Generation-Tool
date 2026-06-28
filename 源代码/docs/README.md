# AI游戏2D资源智能切割与精灵图生成工具

## 项目信息

- **项目名称**：AI Game 2D Resource Intelligent Cutting and Sprite Sheet Generation Tool
- **版本**：1.0
- **作者**：做熙婷
- **学号**：2408090601008
- **完成时间**：2026年6月

---

## 项目简介

本工具是一个基于Web的AI游戏2D资源处理系统，旨在为游戏开发者提供便捷的2D素材处理解决方案。用户可以通过浏览器上传游戏素材图片，系统会自动识别并切割出精灵图，生成九宫格切割和精灵图集，并支持导出多种主流游戏引擎的配置文件。

### 核心功能

1. **智能精灵图检测**
   - 支持手动调节检测阈值
   - AI自动优化参数，找到最佳检测效果
   - 可视化预览检测结果

2. **切割框编辑**
   - 拖拽移动切割框
   - 控制点缩放大小
   - 右键删除单个框
   - 手动添加新框

3. **九宫格切割**
   - 拖拽调整分割线位置
   - 实时预览拉伸效果
   - 支持水平、垂直、双向拉伸
   - 可设置边距大小

4. **精灵图集生成**
   - 自动打包成精灵图集
   - 生成JSON格式配置文件
   - 支持自定义间距和尺寸

5. **多引擎配置导出**
   - Unity配置（SpriteAtlas + .meta + Prefab）
   - Cocos2d-x配置（plist + json）
   - Unreal Engine配置（JSON + INI）

6. **AI动画生成**
   - 10种预设动画效果（弹跳、呼吸、抖动、旋转等）
   - AI智能推荐适合的动画类型
   - 支持本地变换和API生成两种模式
   - 可调节动画参数

7. **用户系统**
   - 用户注册与登录
   - 操作历史记录
   - AI API配置管理

---

## 技术架构

### 后端技术栈

| 技术 | 用途 |
|------|------|
| **Flask** | Web框架，处理HTTP请求和路由 |
| **Flask-CORS** | 跨域资源共享支持 |
| **OpenCV** | 图像处理和计算机视觉 |
| **NumPy** | 数值计算和矩阵运算 |
| **PIL (Pillow)** | 图像格式转换和处理 |
| **SQLite3** | 轻量级数据库存储 |

### 前端技术栈

| 技术 | 用途 |
|------|------|
| **HTML5** | 页面结构 |
| **CSS3** | 样式和动画效果 |
| **原生JavaScript** | 用户交互和API调用 |

### 设计模式

- **MVC模式**：Flask处理路由和业务逻辑（Controller），前端负责视图（View）
- **RESTful API**：统一的数据交互接口
- **状态管理**：使用全局变量+数据库组合管理会话状态

---

## 目录结构

```
AI-Game-Tool/
│
├── backend/                    # 后端代码
│   ├── app.py                  # 主应用程序（Flask服务器）
│   └── requirements.txt        # Python依赖列表
│
├── frontend/                    # 前端代码
│   ├── index.html              # 主工作台页面
│   ├── ai-slicing.html         # AI切割页面
│   ├── spritesheet.html         # 精灵图生成页面
│   ├── nine-patch.html         # 九宫格页面
│   ├── export.html             # 导出配置页面
│   ├── animation.html          # 动画生成页面
│   └── mobile.html             # 移动端适配页面
│
└── docs/                       # 文档目录（本文件）
```

### 运行时目录

程序运行时会自动创建以下目录：

```
uploads/       # 用户上传的原始图片
outputs/       # 处理后的输出文件（切割图、精灵图、配置文件）
database/      # SQLite数据库文件（users.db, 操作历史记录）
```

---

## 快速开始

### 环境要求

- Python 3.7 或更高版本
- 操作系统：Windows / macOS / Linux

### 安装步骤

#### 1. 克隆或下载项目

```bash
git clone <repository-url>
cd AI-Game-Tool/backend
```

#### 2. 安装依赖

使用pip安装Python依赖：

```bash
pip install -r requirements.txt
```

**依赖说明**：
- `flask`：Web框架
- `flask-cors`：跨域支持
- `opencv-python`：图像处理
- `numpy`：数值计算
- `Pillow`：图像处理辅助库

#### 3. 运行服务器

```bash
python app.py
```

服务器启动后显示：
```
* Running on http://127.0.0.1:5000
* Default user: admin / 123456
```

#### 4. 访问应用

打开浏览器，访问：`http://127.0.0.1:5000`

使用默认账号登录：
- 用户名：`admin`
- 密码：`123456`

---

## 使用指南

### 基本工作流程

#### 1. 上传图片

- 点击上传区域或拖拽图片文件
- 支持格式：PNG、JPG、JPEG、BMP等
- 上传后自动显示图片信息和尺寸

#### 2. 智能检测精灵图

**手动检测**：
- 调节"最小面积"滑块控制检测灵敏度
- 选择检测模式（外部轮廓/层级轮廓）
- 点击"检测"按钮执行

**AI自动检测**：
- 点击"AI自动检测"按钮
- 系统自动尝试多种参数组合
- 选择最优检测结果

#### 3. 编辑切割框

- **选中框**：点击切割框
- **移动**：拖拽选中的框
- **缩放**：拖拽控制点
- **删除**：右键点击框，选择"删除"
- **添加**：在空白区域双击添加新框

#### 4. 预览九宫格效果

- 切换到九宫格标签页
- 拖拽分割线调整位置
- 实时预览拉伸效果
- 设置边距参数

#### 5. 生成精灵图

- 点击"生成精灵图"按钮
- 设置间距和尺寸参数
- 自动打包并生成配置文件

#### 6. 导出配置

- 切换到导出页面
- 选择要导出的文件类型
- 选择目标游戏引擎
- 点击"导出选中文件"下载

### AI动画生成

#### 使用预设动画

1. 在动画页面选择精灵图
2. 从动画类型列表中选择：
   - 弹跳（bounce）
   - 呼吸（breath）
   - 抖动（shake）
   - 旋转（rotate）
   - 闪烁（flash）
   - 摇摆（sway）
   - 走路（walk）
   - 脉冲（zoom）
   - 漂浮（float）
   - 挤压（squash）
3. 调节动画参数（帧数、幅度等）
4. 点击"本地生成"预览

#### 使用AI API生成

1. 先在设置中配置AI API Key
2. 输入提示词描述动画
3. 点击"AI生成"按钮
4. 等待AI生成完成

---

## API接口文档

### 图片处理API

#### POST `/upload`
上传图片文件

**请求**：
```
Content-Type: multipart/form-data
file: <图片文件>
```

**响应**：
```json
{
  "path": "uploads/xxx.png",
  "width": 1024,
  "height": 768,
  "filename": "xxx.png",
  "has_alpha": true
}
```

#### POST `/detect`
手动检测精灵图

**请求**：
```json
{
  "min_area": 50,
  "mode": "external"
}
```

**响应**：
```json
{
  "boxes": [...],
  "count": 12,
  "method": "手动检测"
}
```

#### POST `/auto-detect`
AI自动检测精灵图

**响应**：
```json
{
  "boxes": [...],
  "count": 12,
  "method": "AI自动检测",
  "params": {"mode": "external", "min_area": 50}
}
```

#### POST `/cut`
执行精灵图切割

#### POST `/export-selected`
选择性导出文件

### 引擎配置API

#### POST `/export-engine-config`
导出游戏引擎配置文件

**请求**：
```json
{
  "engine": "unity"
}
```

**支持引擎**：
- `unity`：Unity SpriteAtlas
- `cocos`：Cocos2d-x plist/json
- `unreal`：Unreal Engine JSON/INI

### 动画API

#### POST `/api/analyze-sprite`
AI分析精灵图，推荐动画类型

#### POST `/api/generate-animation`
本地生成序列帧动画

#### POST `/api/ai-generate-animation`
使用AI API生成序列帧动画

### 用户API

#### POST `/api/register`
用户注册

#### POST `/api/login`
用户登录

#### POST `/api/logout`
用户登出

#### GET `/api/history`
获取操作历史

#### DELETE `/api/history/<id>`
删除历史记录

---

## 核心算法说明

### 1. 精灵图检测算法

使用OpenCV的轮廓检测功能：

1. **掩码生成**：根据Alpha通道或颜色阈值生成内容掩码
2. **轮廓查找**：使用`findContours`查找连通域
3. **包围盒计算**：使用`boundingRect`获取最小矩形
4. **过滤筛选**：根据面积阈值去除噪声

### 2. AI自动优化算法

采用网格搜索策略：

1. 定义参数空间：面积阈值 [10-200]，模式 [external/hierarchical]
2. 遍历所有参数组合
3. 评分函数：`score = count × 0.7 + (1 - CV) × 0.3`
4. 选择评分最高的参数

### 3. 精灵图打包算法

采用贪心算法：

1. 按高度降序排列所有精灵图
2. 从左到右、从上到下依次放置
3. 超过宽度时换行
4. 预留间距（padding）

---

## 配置说明

### AI API配置

支持多种AI图像生成API：

#### SiliconFlow（推荐）
- Base URL: `https://api.siliconflow.cn/v1`
- 模型: `black-forest-labs/FLUX.1-schnell`

#### OpenAI Compatible
- Base URL: `https://api.openai.com/v1`
- 模型: `dall-e-3` 等

### 九宫格默认参数

```python
nine_patch = {
    'left': 20,
    'top': 20,
    'right': 20,
    'bottom': 20
}
```

### 精灵图打包参数

```python
padding = 2          # 精灵图间距（像素）
sheet_width = 1024    # 单张精灵图最大宽度
```

---

## 开发说明

### 添加新的检测模式

在`detect_sprites`函数中添加新的模式处理逻辑：

```python
def detect_sprites(img, min_area, mode='external'):
    if mode == 'new_mode':
        # 实现新的检测逻辑
        ...
```

### 添加新的导出格式

在`generate_*_config`函数中添加新的配置生成函数：

```python
def generate_new_engine_config(spritesheet_path):
    # 生成新引擎的配置
    ...
```

### 扩展前端页面

在`templates/`目录创建新的HTML文件，添加路由：

```python
@app.route('/new-page')
def new_page():
    return render_template('new-page.html')
```

---

## 常见问题

### Q: 上传图片后显示"无法读取图片"？

**A**: 请确保图片格式受支持（PNG、JPG、BMP等），且文件未损坏。

### Q: 检测结果不理想？

**A**: 
- 尝试调节最小面积阈值
- 切换检测模式
- 使用AI自动检测
- 手动编辑切割框

### Q: 透明背景变成白色？

**A**: 这是OpenCV保存PNG时的正常行为，Alpha通道仍然保留。如需完全透明，请使用PIL库保存。

### Q: AI动画生成失败？

**A**: 
- 检查API Key是否配置正确
- 确认网络连接正常
- 查看错误信息，参考提示修复

### Q: 如何重置密码？

**A**: 在数据库中手动更新密码哈希：
```python
import hashlib
new_hash = hashlib.sha256('newpassword'.encode()).hexdigest()
```

---

## 项目亮点

1. **AI智能优化**：自动寻找最佳检测参数，降低用户学习成本
2. **可视化操作**：实时预览所有操作结果，提升用户体验
3. **多引擎支持**：一键导出多种主流游戏引擎配置
4. **灵活的扩展性**：模块化设计，易于添加新功能
5. **完善的注释**：代码包含详细的中文注释，便于学习和二次开发

---

## 未来改进方向

1. **批量处理**：支持一次处理多张图片
2. **高级AI**：引入更先进的计算机视觉算法
3. **实时协作**：多人同时编辑同一项目
4. **云端存储**：支持云端保存项目
5. **插件系统**：支持第三方扩展

---

## 致谢

感谢所有开源项目的贡献者，特别是：
- Flask团队
- OpenCV社区
- NumPy/SciPy团队

---

## 许可证

本项目仅供学习和教育用途。

---

**学号**：2408090601008
**作者**：做熙婷
**完成时间**：2026年6月
