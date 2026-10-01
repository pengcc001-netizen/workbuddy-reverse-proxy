# WorkBuddy Reverse Proxy

通过 WorkBuddy 桌面版 Token 反代 GLM-5.3-Flash 的独立代理服务。

## 架构

```
ZCode → WorkBuddy Reverse Proxy (端口 8091)
  ├─ 步骤1: 读取本地 Token 文件（WorkBuddy 桌面版登录后自动生成）
  ├─ 步骤2: Python httpx 直连 copilot.tencent.com/v2/chat/completions
  ├─ 步骤3: Token 过期时自动用 refreshToken 刷新
  └─ 步骤4: 返回 OpenAI / Anthropic 兼容格式
```

Token 文件位置（WorkBuddy 桌面版自动生成）:
```
%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info
```

## 使用方式

### 方式 A：打包版（推荐，其他电脑无需装 Python）

**打包步骤（在有 Python 环境的电脑上执行一次）：**

1. 双击 `start.bat` 初始化环境（首次会创建虚拟环境并安装依赖）
2. 双击 `build_exe.bat` 打包
3. 生成的 `dist\workbuddy-proxy.exe` 就是独立可执行文件

**分发使用：**

1. 将 `workbuddy-proxy.exe` 复制到其他电脑
2. 双击运行即可（无需安装 Python）
3. 确保 WorkBuddy 桌面版已安装并登录

### 方式 B：源码运行（需要 Python 环境）

1. 安装 Python 3.10+
2. 双击 `start.bat` 启动（首次自动创建虚拟环境并安装依赖）

## ZCode 配置

| 配置项 | 值 |
|--------|-----|
| Provider | OpenAI Compatible |
| Base URL | `http://127.0.0.1:8091/v1` |
| API Key | 随意填 |
| Model | `glm-5.3-flash` |

## 端口

- `8091` - OpenAI 兼容 API (`/v1/chat/completions`) + Anthropic 兼容 API (`/v1/messages`)

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/chat/completions` | POST | OpenAI 兼容 |
| `/v1/messages` | POST | Anthropic 兼容 |
| `/health` | GET | 健康检查 |

## 依赖

- Python 3.10+（仅源码运行需要，打包版不需要）
- WorkBuddy 桌面版（已安装并登录）
- fastapi / uvicorn / httpx（`start.bat` 自动安装）
