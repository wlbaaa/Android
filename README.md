# Android 12 Web Emulator

在浏览器中运行真实 Android 12 系统的模拟器，支持上传和运行 APK。

## 架构

```
GitHub Pages (前端)
├── Android 12 Material You UI
├── noVNC 客户端 (WebSocket 连接)
└── APK 上传 → 后端 API

GitHub Codespaces / 云服务器 (后端)
├── Redroid (Android 12 Docker 容器)
├── scrcpy (VNC 画面捕获)
├── websockify (VNC → WebSocket)
└── API Server (APK 安装、应用管理)
```

## 快速开始

### 方式一：GitHub Codespaces（推荐）

1. 点击仓库的 **Code → Codespaces → Create codespace**
2. Codespace 创建时会自动运行 `backend/setup.sh` 安装依赖
3. 在 Codespace 终端运行：
   ```bash
   cd /workspaces/Android && bash backend/start.sh
   ```
4. 等待 Android 启动（约 30 秒）
5. 获取 Codespace 转发 URL：
   - API: `https://<codespace-name>-8080.app.github.dev`
   - VNC: `https://<codespace-name>-6080.app.github.dev`
6. 打开 GitHub Pages 页面，进入 **设置 → 服务器配置**，填入以上 URL
7. 点击 **模拟器 → 连接** 即可操作 Android 系统

### 方式二：自有服务器

1. 将仓库克隆到服务器
2. 运行：
   ```bash
   bash backend/setup.sh
   bash backend/start.sh
   ```
3. 或使用 Docker Compose：
   ```bash
   docker compose up -d
   ```
4. 在前端设置中填入服务器地址

## 使用方法

1. **上传 APK**：在上传页面选择 .apk 文件，自动安装到 Android 容器
2. **运行应用**：在应用列表中点击"启动"，或在模拟器画面中直接操作
3. **截图**：点击截图按钮下载当前画面

## 文件结构

```
├── index.html              # 前端页面 (Android 12 Material You UI)
├── .devcontainer/
│   └── devcontainer.json   # Codespaces 配置
├── backend/
│   ├── setup.sh            # 环境安装脚本
│   ├── start.sh            # 启动脚本
│   ├── server.py           # API 服务器 (APK 上传、应用管理)
│   └── Dockerfile          # API 容器镜像
├── docker-compose.yml      # Docker Compose 部署
└── README.md
```

## API 接口

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /health | 健康检查 |
| POST | /install | 上传并安装 APK |
| GET | /apps | 列出已安装应用 |
| POST | /launch | 启动应用 |
| POST | /uninstall | 卸载应用 |
| GET | /screenshot | 截图 |
| GET | /info | 设备信息 |

## 技术栈

- **前端**：HTML/CSS/JS，Material You 设计系统
- **Android 容器**：Redroid (Docker 中的 Android 12)
- **画面传输**：scrcpy → VNC → websockify → noVNC (WebSocket)
- **后端 API**：Python HTTP Server + ADB
- **部署**：GitHub Pages + GitHub Codespaces

## 限制

- GitHub Codespaces 免费额度：每月 120 核心小时（2 核约 60 小时）
- Redroid 需要 Docker 和 privileged 权限
- 网络延迟取决于服务器位置
