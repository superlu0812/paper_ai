#!/bin/bash

# Paper AI 一键启动脚本
# 自动启动后端和前端服务

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/paper_ai_enhanced"
FRONTEND_DIR="$PROJECT_ROOT/paper_ai_frontend"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        exit 1
    fi
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # 端口被占用
    else
        return 1  # 端口可用
    fi
}

# 设置后端环境
setup_backend() {
    print_info "设置后端环境..."
    
    cd "$BACKEND_DIR"
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未安装，请先安装 Python 3.8 或更高版本"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_warning "虚拟环境不存在，正在创建..."
        python3 -m venv venv
        print_success "虚拟环境创建成功"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 检查并安装依赖
    if [ ! -f "venv/.installed" ] || [ "requirements.txt" -nt "venv/.installed" ]; then
        print_info "安装后端依赖..."
        pip install --upgrade pip > /dev/null 2>&1
        pip install -r requirements.txt
        touch venv/.installed
        print_success "后端依赖安装完成"
    else
        print_info "后端依赖已安装，跳过安装步骤"
    fi
    
    # 检查配置文件
    if [ ! -f "config.yaml" ]; then
        print_warning "配置文件 config.yaml 不存在，请确保已创建配置文件"
    fi
}

# 启动后端服务
start_backend() {
    print_info "启动后端服务..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # 检查端口
    if check_port 8000; then
        print_warning "端口 8000 已被占用，尝试使用现有服务"
    else
        # 在后台启动服务器
        nohup uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/paper_ai_backend.log 2>&1 &
        BACKEND_PID=$!
        echo $BACKEND_PID > /tmp/paper_ai_backend.pid
        
        # 等待服务启动
        print_info "等待后端服务启动..."
        sleep 3
        
        # 检查服务是否启动成功
        if check_port 8000; then
            print_success "后端服务已启动 (PID: $BACKEND_PID, 端口: 8000)"
            print_info "后端日志: tail -f /tmp/paper_ai_backend.log"
        else
            print_error "后端服务启动失败，请查看日志: /tmp/paper_ai_backend.log"
            exit 1
        fi
    fi
}

# 设置前端环境
setup_frontend() {
    print_info "设置前端环境..."
    
    cd "$FRONTEND_DIR"
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js 未安装，请先安装 Node.js 16.0.0 或更高版本"
        exit 1
    fi
    
    # 检查 npm
    if ! command -v npm &> /dev/null; then
        print_error "npm 未安装，请先安装 npm"
        exit 1
    fi
    
    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install
        print_success "前端依赖安装完成"
    else
        # 检查 package.json 是否有更新
        if [ "package.json" -nt "node_modules/.package-lock.json" ] 2>/dev/null; then
            print_info "检测到 package.json 更新，重新安装依赖..."
            npm install
            print_success "前端依赖更新完成"
        else
            print_info "前端依赖已安装，跳过安装步骤"
        fi
    fi
    
    # 检查环境变量文件
    if [ ! -f ".env.development" ]; then
        print_warning ".env.development 文件不存在，创建默认配置..."
        cat > .env.development << EOF
# API 基础地址
VITE_API_BASE_URL=http://localhost:8000

# 部署路径
VITE_BASE_URL=/
EOF
        print_success "已创建 .env.development 文件"
    fi
}

# 启动前端服务
start_frontend() {
    print_info "启动前端服务..."
    
    cd "$FRONTEND_DIR"
    
    # 检查端口
    if check_port 5173; then
        print_warning "端口 5173 已被占用，尝试使用现有服务"
    else
        # 在后台启动开发服务器
        nohup npm run dev > /tmp/paper_ai_frontend.log 2>&1 &
        FRONTEND_PID=$!
        echo $FRONTEND_PID > /tmp/paper_ai_frontend.pid
        
        # 等待服务启动
        print_info "等待前端服务启动..."
        sleep 5
        
        # 检查服务是否启动成功
        if check_port 5173; then
            print_success "前端服务已启动 (PID: $FRONTEND_PID, 端口: 5173)"
            print_info "前端日志: tail -f /tmp/paper_ai_frontend.log"
        else
            print_error "前端服务启动失败，请查看日志: /tmp/paper_ai_frontend.log"
            exit 1
        fi
    fi
}

# 停止服务
stop_services() {
    print_info "停止所有服务..."
    
    # 停止后端
    if [ -f /tmp/paper_ai_backend.pid ]; then
        BACKEND_PID=$(cat /tmp/paper_ai_backend.pid)
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            kill $BACKEND_PID 2>/dev/null || true
            print_success "后端服务已停止 (PID: $BACKEND_PID)"
        fi
        rm -f /tmp/paper_ai_backend.pid
    fi
    
    # 停止前端
    if [ -f /tmp/paper_ai_frontend.pid ]; then
        FRONTEND_PID=$(cat /tmp/paper_ai_frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            kill $FRONTEND_PID 2>/dev/null || true
            print_success "前端服务已停止 (PID: $FRONTEND_PID)"
        fi
        rm -f /tmp/paper_ai_frontend.pid
    fi
    
    # 尝试通过端口停止
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    
    print_success "所有服务已停止"
}

# 显示服务状态
show_status() {
    echo ""
    print_info "服务状态:"
    echo ""
    
    if check_port 8000; then
        print_success "后端服务: 运行中 (http://localhost:8000)"
        print_info "  - API 文档: http://localhost:8000/ai_paper/docs"
    else
        print_error "后端服务: 未运行"
    fi
    
    echo ""
    
    if check_port 5173; then
        print_success "前端服务: 运行中 (http://localhost:5173)"
    else
        print_error "前端服务: 未运行"
    fi
    
    echo ""
}

# 清理函数（在脚本退出时调用）
cleanup() {
    if [ "$?" != "0" ]; then
        print_error "启动过程中出现错误"
    fi
}

trap cleanup EXIT

# 主函数
main() {
    echo ""
    print_info "=========================================="
    print_info "  Paper AI 一键启动脚本"
    print_info "=========================================="
    echo ""
    
    # 检查参数
    if [ "$1" == "stop" ]; then
        stop_services
        exit 0
    fi
    
    if [ "$1" == "status" ]; then
        show_status
        exit 0
    fi
    
    # 设置后端
    setup_backend
    
    # 设置前端
    setup_frontend
    
    # 启动后端
    start_backend
    
    # 启动前端
    start_frontend
    
    # 显示状态
    show_status
    
    echo ""
    print_success "=========================================="
    print_success "  所有服务启动完成！"
    print_success "=========================================="
    echo ""
    print_info "访问地址:"
    print_info "  前端界面: http://localhost:5173"
    print_info "  后端 API: http://localhost:8000"
    print_info "  API 文档: http://localhost:8000/ai_paper/docs"
    echo ""
    print_info "停止服务: ./start.sh stop"
    print_info "查看状态: ./start.sh status"
    print_info "查看日志:"
    print_info "  后端: tail -f /tmp/paper_ai_backend.log"
    print_info "  前端: tail -f /tmp/paper_ai_frontend.log"
    echo ""
}

# 运行主函数
main "$@"
