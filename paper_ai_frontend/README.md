# Paper AI Frontend

论文爬取与智能总结系统的前端应用，基于 Vue 3 + Vite 构建。

## 📋 项目简介

这是一个用于展示和管理论文数据的前端应用，支持：
- 📚 论文列表浏览和搜索
- 🔍 多条件筛选（日期、分类、关键词、作者）
- 📊 统计报表和数据分析
- 📄 PDF 预览功能
- 📅 日期选择器（标记有数据的日期）
- 🔎 可搜索的分类下拉菜单

## 🛠️ 开发环境

### 系统要求

- **Node.js**: >= 16.0.0 (推荐使用 18.x 或更高版本)
- **npm**: >= 8.0.0 (或使用 yarn/pnpm)
- **浏览器**: 支持 ES6+ 的现代浏览器（Chrome、Firefox、Safari、Edge）

### 技术栈

- **框架**: Vue 3.5.24
- **构建工具**: Vite 7.2.4
- **路由**: Vue Router 4.6.4
- **HTTP 客户端**: Axios 1.13.2
- **日期处理**: Day.js 1.11.19
- **Markdown 渲染**: Marked 17.0.1
- **PDF 预览**: PDF.js 5.4.530

## 🚀 快速开始

### 安装依赖

```bash
npm install
```

### 开发环境运行

```bash
npm run dev
```

应用将在 `http://localhost:5173` 启动（Vite 默认端口）。

### 环境变量配置

创建 `.env.development` 文件用于开发环境：

```env
# API 基础地址
VITE_API_BASE_URL=http://localhost:8000

# 部署路径（可选，默认使用 vite.config.js 中的配置）
VITE_BASE_URL=/
```

创建 `.env.production` 文件用于生产环境：

```env
# API 基础地址
VITE_API_BASE_URL=http://your-api-server:8088

# 部署路径
VITE_BASE_URL=/ai_paper/
```

## 🧪 测试

### 本地开发测试

1. **启动开发服务器**:
   ```bash
   npm run dev
   ```

2. **预览生产构建**:
   ```bash
   npm run build
   npm run preview
   ```

3. **功能测试清单**:
   - ✅ 论文列表加载和分页
   - ✅ 日期选择器（检查有数据的日期标记）
   - ✅ 分类搜索下拉菜单
   - ✅ 关键词和作者搜索
   - ✅ 论文详情页和 PDF 预览
   - ✅ 统计报表页面
   - ✅ 路由导航

### 浏览器兼容性测试

建议在以下浏览器中测试：
- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

## 📦 构建和发布

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

### 部署步骤

1. **构建项目**:
   ```bash
   npm run build
   ```

2. **上传文件**:
   将 `dist/` 目录下的所有文件上传到服务器的部署目录（如 `/data/ai_paper/paper_ai_frontend/`）

3. **配置 Nginx**:
   参考下面的 Nginx 配置示例

4. **验证部署**:
   访问 `https://your-domain.com/ai_paper/` 检查应用是否正常运行

### 部署路径配置

如果部署到其他路径（非 `/ai_paper/`），需要：

1. 在 `.env.production` 中设置 `VITE_BASE_URL`:
   ```env
   VITE_BASE_URL=/your-path/
   ```

2. 重新构建:
   ```bash
   npm run build
   ```

3. 更新 Nginx 配置中的路径

## 🔧 Nginx 配置示例

### 完整配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件服务
    location /ai_paper/ {
        # 缓存配置
        proxy_cache_valid  200 304 301 302 10d;
        proxy_cache_valid  any 1d;
        proxy_cache_key $host$uri$is_args$args;
        expires 600;
        add_header Cache-Control "web-html";
        add_header Access-Control-Allow-Origin *;

        # 静态文件目录
        alias /data/ai_paper/paper_ai_frontend/;
        index index.html;

        # 处理 Vue Router 的 history 模式
        # 所有未匹配的路由都回退到 index.html
        try_files $uri $uri/ /ai_paper/index.html;
        
        # 确保 .mjs 文件使用正确的 MIME 类型（PDF.js worker）
        location ~ \.mjs$ {
            add_header Content-Type application/javascript;
        }
        
        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API 代理
    location /ai_paper/api {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### HTTPS 配置（推荐）

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书配置
    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 前端静态文件服务
    location /ai_paper/ {
        # ... (同上)
    }

    # API 代理
    location /ai_paper/api {
        # ... (同上)
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### 配置说明

1. **路径配置**:
   - `alias` 指向实际的静态文件目录
   - `try_files` 确保 Vue Router 的 history 模式正常工作

2. **缓存策略**:
   - HTML 文件：600 秒缓存
   - 静态资源（JS/CSS/图片）：1 年缓存
   - API 响应：根据状态码设置不同缓存时间

3. **MIME 类型**:
   - `.mjs` 文件需要设置为 `application/javascript`，用于 PDF.js worker

4. **API 代理**:
   - 将 `/ai_paper/api` 请求代理到后端服务器
   - 设置必要的请求头

## 📁 项目结构

```
paper_ai_frontend/
├── public/                 # 静态资源
│   └── workers/            # PDF.js worker 文件
├── src/
│   ├── api/               # API 接口封装
│   │   └── index.js
│   ├── components/        # 组件
│   │   ├── DatePickerWithMarkers.vue
│   │   └── SearchableSelect.vue
│   ├── router/           # 路由配置
│   │   └── index.js
│   ├── views/            # 页面视图
│   │   ├── PaperList.vue
│   │   ├── PaperDetail.vue
│   │   └── StatsReport.vue
│   ├── App.vue          # 根组件
│   └── main.js          # 入口文件
├── .env.development     # 开发环境变量
├── .env.production      # 生产环境变量
├── vite.config.js       # Vite 配置
├── package.json         # 项目配置
└── README.md           # 项目文档
```

## 🔑 环境变量

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `http://localhost:8000` | `http://api.example.com` |
| `VITE_BASE_URL` | 部署路径 | `/ai_paper/` | `/app/` |

## 🐛 常见问题

### 1. PDF 预览失败

**问题**: PDF.js worker 加载失败

**解决方案**:
- 确保 Nginx 配置了 `.mjs` 文件的 MIME 类型
- 检查 `public/workers/pdf.worker.min.mjs` 文件是否存在
- 检查浏览器控制台的错误信息

### 2. 路由 404 错误

**问题**: 刷新页面或直接访问路由时出现 404

**解决方案**:
- 确保 Nginx 配置了 `try_files $uri $uri/ /ai_paper/index.html;`
- 检查 `vite.config.js` 中的 `base` 配置是否正确

### 3. API 请求失败

**问题**: 无法连接到后端 API

**解决方案**:
- 检查 `VITE_API_BASE_URL` 环境变量配置
- 检查 Nginx API 代理配置
- 检查后端服务是否正常运行

### 4. 资源加载失败

**问题**: JS/CSS 文件 404

**解决方案**:
- 确保构建时 `base` 配置正确
- 检查 Nginx `alias` 路径是否正确
- 检查文件权限

## 📝 开发规范

- 使用 Vue 3 Composition API (`<script setup>`)
- 组件使用 PascalCase 命名
- 文件使用 kebab-case 命名
- 遵循 ESLint 规则（如果配置了）

## 📄 许可证

[根据项目实际情况填写]

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

**最后更新**: 2024年
