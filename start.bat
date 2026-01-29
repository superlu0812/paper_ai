@echo off
REM Paper AI 一键启动脚本 (Windows)
REM 自动启动后端和前端服务

setlocal enabledelayedexpansion

REM 项目根目录
set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%paper_ai_enhanced"
set "FRONTEND_DIR=%PROJECT_ROOT%paper_ai_frontend"

echo.
echo ==========================================
echo   Paper AI 一键启动脚本
echo ==========================================
echo.

REM 检查参数
if "%1"=="stop" goto :stop_services
if "%1"=="status" goto :show_status

REM 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装，请先安装 Python 3.8 或更高版本
    exit /b 1
)

REM 检查 Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 未安装，请先安装 Node.js 16.0.0 或更高版本
    exit /b 1
)

REM 设置后端环境
echo [INFO] 设置后端环境...
cd /d "%BACKEND_DIR%"

REM 检查虚拟环境
if not exist "venv" (
    echo [WARNING] 虚拟环境不存在，正在创建...
    python -m venv venv
    echo [SUCCESS] 虚拟环境创建成功
)

REM 激活虚拟环境并安装依赖
call venv\Scripts\activate.bat

REM 检查依赖是否已安装
if not exist "venv\.installed" (
    echo [INFO] 安装后端依赖...
    python -m pip install --upgrade pip >nul 2>&1
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] 后端依赖安装失败
        exit /b 1
    )
    type nul > venv\.installed
    echo [SUCCESS] 后端依赖安装完成
) else (
    echo [INFO] 后端依赖已安装，跳过安装步骤
)

REM 检查配置文件
if not exist "config.yaml" (
    echo [WARNING] 配置文件 config.yaml 不存在，请确保已创建配置文件
)

REM 启动后端服务
echo [INFO] 启动后端服务...
start "Paper AI Backend" /min cmd /c "venv\Scripts\activate.bat && uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 /nobreak >nul
echo [SUCCESS] 后端服务已启动 (端口: 8000)

REM 设置前端环境
echo [INFO] 设置前端环境...
cd /d "%FRONTEND_DIR%"

REM 检查 node_modules
if not exist "node_modules" (
    echo [INFO] 安装前端依赖...
    call npm install
    if errorlevel 1 (
        echo [ERROR] 前端依赖安装失败
        exit /b 1
    )
    echo [SUCCESS] 前端依赖安装完成
) else (
    echo [INFO] 前端依赖已安装，跳过安装步骤
)

REM 检查环境变量文件
if not exist ".env.development" (
    echo [WARNING] .env.development 文件不存在，创建默认配置...
    (
        echo # API 基础地址
        echo VITE_API_BASE_URL=http://localhost:8000
        echo.
        echo # 部署路径
        echo VITE_BASE_URL=/
    ) > .env.development
    echo [SUCCESS] 已创建 .env.development 文件
)

REM 启动前端服务
echo [INFO] 启动前端服务...
start "Paper AI Frontend" /min cmd /c "npm run dev"
timeout /t 5 /nobreak >nul
echo [SUCCESS] 前端服务已启动 (端口: 5173)

REM 显示状态
echo.
echo [INFO] 服务状态:
echo.
echo [SUCCESS] 后端服务: 运行中 (http://localhost:8000)
echo [INFO]   - API 文档: http://localhost:8000/ai_paper/docs
echo.
echo [SUCCESS] 前端服务: 运行中 (http://localhost:5173)
echo.

echo ==========================================
echo   所有服务启动完成！
echo ==========================================
echo.
echo 访问地址:
echo   前端界面: http://localhost:5173
echo   后端 API: http://localhost:8000
echo   API 文档: http://localhost:8000/ai_paper/docs
echo.
echo 停止服务: 关闭对应的命令行窗口，或运行 start.bat stop
echo.

goto :end

:stop_services
echo [INFO] 停止所有服务...
taskkill /FI "WINDOWTITLE eq Paper AI Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Paper AI Frontend*" /T /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
echo [SUCCESS] 所有服务已停止
goto :end

:show_status
echo [INFO] 服务状态:
echo.
netstat -an | findstr ":8000" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [ERROR] 后端服务: 未运行
) else (
    echo [SUCCESS] 后端服务: 运行中 (http://localhost:8000)
    echo [INFO]   - API 文档: http://localhost:8000/ai_paper/docs
)
echo.
netstat -an | findstr ":5173" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [ERROR] 前端服务: 未运行
) else (
    echo [SUCCESS] 前端服务: 运行中 (http://localhost:5173)
)
echo.
goto :end

:end
endlocal
