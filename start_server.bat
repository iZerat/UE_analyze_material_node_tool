@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 正在启动本地服务器...
echo 请稍候，浏览器将自动打开...
echo.

:: 检查 Python 是否可用
python -c "import http.server" >nul 2>&1
if %errorlevel% == 0 (
    start "" "http://localhost:8080/UE_extract_material_node_params.html"
    python -m http.server 8080
    goto :end
)

:: 检查 Python3
python3 -c "import http.server" >nul 2>&1
if %errorlevel% == 0 (
    start "" "http://localhost:8080/UE_extract_material_node_params.html"
    python3 -m http.server 8080
    goto :end
)

echo [错误] 未找到 Python，请安装 Python 3 后重试。
pause

:end