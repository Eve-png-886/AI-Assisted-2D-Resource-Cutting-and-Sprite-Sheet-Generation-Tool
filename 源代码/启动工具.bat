@echo off
chcp 65001 >nul
echo ========================================
echo  AI游戏2D资源切割工具 启动器
echo ========================================
echo.

cd /d "%~dp0backend"

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

echo [2/3] 安装依赖（如果需要）...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖，请稍候...
    pip install -r requirements.txt -q
    echo 安装完成
)

echo [3/3] 启动服务器...
echo.
echo 访问地址: http://127.0.0.1:5000
echo 默认账号: admin / 123456
echo.
echo 按 Ctrl+C 停止服务器
echo.

python app.py

pause
