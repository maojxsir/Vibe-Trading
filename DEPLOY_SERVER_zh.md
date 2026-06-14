# Vibe-Trading 云服务器部署手册

本文档说明如何在 **阿里云 ECS**（或其他 Ubuntu 云主机）上，使用 Docker 部署 Vibe-Trading 供个人远程访问。

适用场景：单用户、私有部署；前端与 API 由同一容器提供，通过浏览器访问。

---

## 目录

1. [架构概览](#1-架构概览)
2. [服务器要求](#2-服务器要求)
3. [安装 Docker（Ubuntu / 阿里云）](#3-安装-dockerubuntu--阿里云)
4. [拉取代码](#4-拉取代码)
5. [配置环境变量](#5-配置环境变量)
6. [构建并启动](#6-构建并启动)
7. [开放防火墙与安全组](#7-开放防火墙与安全组)
8. [首次访问与认证](#8-首次访问与认证)
9. [日常运维](#9-日常运维)
10. [安全建议](#10-安全建议)
11. [故障排查](#11-故障排查)
12. [与本地 Docker 的区别](#12-与本地-docker-的区别)

---

## 1. 架构概览

```
浏览器  ──HTTP──►  ECS:52889  ──►  Docker 容器 :8899
                                      ├── 静态前端 (frontend/dist)
                                      └── Python API (vibe-trading serve)
```

| 项目 | 说明 |
|------|------|
| 配置文件 | `docker-compose.prod.yml` |
| 对外端口 | **52889**（宿主机）→ 8899（容器内） |
| 环境文件 | `agent/.env`（含 LLM key、API 认证等） |
| 持久化数据 | Docker volumes `vibe-runs`、`vibe-sessions` |

本地开发用的 `docker-compose.yml` 只绑定 `127.0.0.1:8899`，**不适合**直接暴露到公网。远程部署请始终使用 `docker-compose.prod.yml`。

---

## 2. 服务器要求

| 项目 | 建议 |
|------|------|
| 系统 | Ubuntu 22.04 / 24.04（Noble） |
| 内存 | ≥ 2 GB（首次 `docker build` 会编译前端并安装 Python 依赖） |
| 磁盘 | ≥ 10 GB 可用空间 |
| 软件 | Git、Docker CE、Docker Compose 插件 |

---

## 3. 安装 Docker（Ubuntu / 阿里云）

### 3.1 常见错误

若执行以下命令失败：

```bash
sudo apt install -y docker.io docker-compose-v2
```

并出现：

```text
containerd.io : Conflicts: containerd
```

**原因**：系统已配置 **Docker CE 源**（如 `mirrors.aliyun.com/docker-ce`），与 Ubuntu 自带的 `docker.io` 依赖不同的 containerd 包，二者互斥。

**结论**：不要安装 `docker.io`，改用 Docker CE。

### 3.2 正确安装步骤

```bash
# 清理可能冲突的旧包（没有安装过可忽略报错）
sudo apt remove -y docker.io docker-doc docker-compose docker-compose-v2 \
  podman-docker containerd runc 2>/dev/null || true

# 安装 Docker CE（含 compose 插件）
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

# 启动并设置开机自启
sudo systemctl enable --now docker

# 验证
docker --version
docker compose version
sudo docker run --rm hello-world
```

### 3.3 若 Docker CE 源尚未配置

阿里云 ECS 通常已预装 Docker CE 源。若没有，可参考 [Docker 官方文档](https://docs.docker.com/engine/install/ubuntu/) 或阿里云镜像站说明添加 `docker-ce` 源后再执行 3.2 的安装命令。

### 3.4 仍无法安装时

查看已安装的相关包：

```bash
dpkg -l | grep -E 'docker|containerd'
```

将输出保存后对照排查，避免同时保留 `containerd`（Ubuntu 包）与 `containerd.io`（Docker CE 包）。

### 3.5 配置 Docker 镜像加速（国内 ECS 必做）

在阿里云上 `docker compose build` 前**必须先**配置可用的 registry mirror。旧版一键镜像 `registry.docker-cn.com` 已长期不可用，若仍写在配置里会导致拉取 `node:20-slim`、`python:3.11-slim` 超时：

```text
failed to resolve source metadata for docker.io/library/python:3.11-slim
Head "https://registry.docker-cn.com/...": dial tcp ...:443: i/o timeout
```

**查看当前配置：**

```bash
cat /etc/docker/daemon.json
```

**替换为可用 mirror（删除 `registry.docker-cn.com`）：**

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
docker info | grep -A5 "Registry Mirrors"
```

**验证能否拉基础镜像：**

```bash
sudo docker pull node:20-slim
sudo docker pull python:3.11-slim
```

两条都成功后再执行 `docker compose ... up --build`。

也可在阿里云控制台 **容器镜像服务 ACR → 镜像工具 → 镜像加速器** 获取专属地址，填入 `registry-mirrors` 数组**最前面**。

---

## 4. 拉取代码

国内 ECS 直接 `git clone https://github.com/...` 常超时，任选其一。

### 4.1 在服务器上生成 GitHub SSH key（推荐，便于后续 `git pull`）

```bash
ssh-keygen -t ed25519 -C "aliyun-ecs" -f ~/.ssh/id_ed25519_github -N ""

cat >> ~/.ssh/config <<'EOF'
Host github.com
  Hostname ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/id_ed25519_github
EOF
chmod 600 ~/.ssh/config

cat ~/.ssh/id_ed25519_github.pub
```

将输出的公钥添加到 GitHub（仓库 **Deploy keys** 只读即可，或账号 **SSH keys**），然后：

```bash
ssh -T git@github.com
git clone git@github.com:maojxsir/Vibe-Trading.git
cd Vibe-Trading
```

### 4.2 从本机上传（最快，不依赖服务器访问 GitHub）

在 Mac 上：

```bash
cd /Users/maojianxin/my_test
tar czf vibe-trading.tar.gz \
  --exclude='Vibe-Trading/frontend/node_modules' \
  --exclude='Vibe-Trading/agent/runs' \
  Vibe-Trading
scp vibe-trading.tar.gz root@<服务器IP>:~/
```

在服务器上：

```bash
cd ~ && tar xzf vibe-trading.tar.gz && cd Vibe-Trading
```

### 4.3 HTTPS 镜像 clone（临时方案）

```bash
git clone https://ghfast.top/https://github.com/maojxsir/Vibe-Trading.git
```

如需特定分支：`git checkout feature/trading_buddy`

---

## 5. 配置环境变量

### 5.1 创建配置文件

```bash
cp agent/.env.example agent/.env
nano agent/.env    # 或 vim agent/.env
```

### 5.2 必改项

**（1）LLM 提供商** — 取消注释其中一个 provider 并填入 API Key，例如 DashScope：

```bash
LANGCHAIN_PROVIDER=dashscope
LANGCHAIN_MODEL_NAME=qwen-plus-latest
DASHSCOPE_API_KEY=sk-xxxxxxxx
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

其他 provider 见 `agent/.env.example` 中的注释块（OpenRouter、DeepSeek、OpenAI 等）。

**（2）API 认证密钥** — 对外部署**必须**设置：

```bash
API_AUTH_KEY=your-long-random-secret-here
```

生成随机密钥：

```bash
openssl rand -hex 32
```

### 5.3 可选项

| 变量 | 说明 |
|------|------|
| `TUSHARE_TOKEN` | A 股 Tushare Pro token |
| `CORS_ORIGINS` | 若通过独立域名访问，可设置允许的 origin |
| `VIBE_TRADING_SSE_TIMEOUT` | 慢模型可适当增大 SSE 超时 |

完整说明见 `agent/.env.example`。

### 5.4 从本机上传已有配置

若本地已配好 `agent/.env`，可在**本机**执行：

```bash
scp /path/to/Vibe-Trading/agent/.env root@<服务器公网IP>:~/TradingBuddy/agent/.env
```

**注意**：`.env` 含密钥，勿提交到 Git，勿在公开场合分享。

上传或编辑 `.env` 后，需让容器重新加载环境变量，见 [§9.3 修改配置后让容器重新加载](#93-修改配置后让容器重新加载)：

```bash
cd ~/TradingBuddy
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## 6. 构建并启动

项目目录以 `~/TradingBuddy` 为例（clone 到其他路径时自行替换）。

### 6.1 前台启动（构建快、内存够时）

```bash
cd ~/TradingBuddy
sudo docker compose -f docker-compose.prod.yml up --build -d
```

`-d` 表示容器**后台运行**；但 `up --build` 本身会占用当前终端直到镜像构建完成。

### 6.2 构建也放后台（推荐：小 ECS / SSH 易断）

构建可能 10–30 分钟，且会吃满 CPU/内存，SSH 容易卡住。**把整个 build + 启动丢到后台**，关掉 Workbench 也会继续：

```bash
cd ~/TradingBuddy

# 可选：加 swap，减少 OOM 杀 build
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile

# 后台构建并启动，日志写入文件
nohup docker compose -f docker-compose.prod.yml up --build -d \
  > /tmp/vibe-deploy.log 2>&1 &

echo "deploy_pid=$!"
```

**查看进度（另开一个终端或稍后执行）：**

```bash
tail -f /tmp/vibe-deploy.log          # 跟踪构建日志
docker compose -f ~/TradingBuddy/docker-compose.prod.yml ps
curl -s http://127.0.0.1:52889/health
```

**判断是否还在 build：**

```bash
pgrep -af "docker compose" || echo "compose 已结束，看 ps / 日志"
```

**构建成功后日志末尾**会出现 `Started` / `Running`，且 `curl` 返回 200。

首次构建可能需要 **5–30 分钟**（多阶段：Node 构建前端 + Python 安装依赖）。

### 6.3 检查状态

```bash
# 容器是否在运行
sudo docker compose -f docker-compose.prod.yml ps

# 实时日志
sudo docker compose -f docker-compose.prod.yml logs -f

# 健康检查（在服务器本机）
curl -s http://127.0.0.1:52889/health
```

正常时 `/health` 应返回成功响应；日志中可见 `vibe-trading serve` 已在 `0.0.0.0:8899` 监听。

### 6.4 访问地址

```text
http://<服务器公网 IP>:52889
```

---

## 7. 开放防火墙与安全组

### 7.1 阿里云安全组

ECS 控制台 → **实例** → **安全组** → **入方向规则**，新增：

| 协议 | 端口 | 授权对象 | 说明 |
|------|------|----------|------|
| TCP | 52889 | 你的公网 IP /32 | 建议仅允许自用 IP |
| TCP | 52889 | 0.0.0.0/0 | 仅测试用，生产不推荐 |

### 7.2 系统防火墙（若启用 ufw）

```bash
sudo ufw allow 52889/tcp
sudo ufw status
```

---

## 8. 首次访问与认证

1. 浏览器打开 `http://<服务器公网 IP>:52889`。
2. 进入 **Settings（设置）** 页面。
3. 在 **Server API key** 输入框填入与 `agent/.env` 中 **`API_AUTH_KEY` 完全相同**的值，保存。
4. 页面会刷新；此后浏览器将 key 存入 localStorage，请求自动携带 `Authorization: Bearer <key>`。

若未设置 Server API key，远程访问时 API 会返回认证错误，Agent 等功能无法使用。

---

## 9. 日常运维

以下命令默认项目目录为 **`~/TradingBuddy`**，compose 文件为 **`docker-compose.prod.yml`**。若路径不同，请自行替换。

为方便复制，可先设变量：

```bash
export VT_DIR=~/TradingBuddy
export VT_COMPOSE="docker compose -f $VT_DIR/docker-compose.prod.yml"
cd "$VT_DIR"
```

未使用 `sudo` 时，若报权限错误，在命令前加 `sudo` 即可。

---

### 9.1 查看状态

```bash
cd ~/TradingBuddy

# 容器是否在跑、端口映射、健康状态
docker compose -f docker-compose.prod.yml ps

# 本机 API 健康检查（应返回 JSON，含 "healthy"）
curl -s http://127.0.0.1:52889/health

# 外网（在你电脑上）
curl -s http://<服务器公网IP>:52889/health
```

---

### 9.2 启动 / 停止 / 重启

```bash
cd ~/TradingBuddy

# 启动（镜像已构建好时，不重新 build）
docker compose -f docker-compose.prod.yml up -d

# 停止并移除容器（数据卷保留，runs/sessions 不丢）
docker compose -f docker-compose.prod.yml down

# 仅重启已有容器（不改镜像、不重新读 .env 文件内容*）
docker compose -f docker-compose.prod.yml restart
```

\* `restart` 不会重新挂载已变更的 `agent/.env`。**改 `.env` 后请用 [§9.3](#93-修改配置后让容器重新加载)**。

---

### 9.3 修改配置后让容器重新加载

配置文件：`~/TradingBuddy/agent/.env`（LLM key、`API_AUTH_KEY`、`TUSHARE_TOKEN` 等）。

```bash
cd ~/TradingBuddy
nano agent/.env          # 或 vim
chmod 600 agent/.env     # 建议权限
```

**改完 `.env` 后必须重建容器**，环境变量才会注入：

```bash
cd ~/TradingBuddy
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

| 你改了什么 | 推荐命令 |
|------------|----------|
| 仅 `agent/.env`（LLM、API_AUTH_KEY 等） | `up -d --force-recreate` |
| `Dockerfile` / 代码 / 依赖 | `up --build -d`（见 [§9.4](#94-更新代码或镜像)） |
| `docker-compose.prod.yml` 端口等 | `up -d --force-recreate` |

**改 `API_AUTH_KEY` 后还需：**

1. 浏览器打开 **Settings → Server API key**，填入**新** key 并保存；或清除旧 key 后重填。
2. 若只改了 LLM key、未改 `API_AUTH_KEY`，一般只需 `--force-recreate`，浏览器 Settings 不必动。

**验证配置已生效：**

```bash
docker compose -f docker-compose.prod.yml ps
curl -s http://127.0.0.1:52889/health
docker compose -f docker-compose.prod.yml logs --tail=30 vibe-trading
```

---

### 9.4 更新代码或镜像

**拉代码 + 重新构建（改业务代码、`Dockerfile`、前端后）：**

```bash
cd ~/TradingBuddy
git pull                 # 或 scp/rsync 同步
docker compose -f docker-compose.prod.yml up --build -d
```

**构建较慢时放后台：**

```bash
cd ~/TradingBuddy
nohup docker compose -f docker-compose.prod.yml up --build -d \
  > /tmp/vibe-deploy.log 2>&1 &
tail -f /tmp/vibe-deploy.log
```

**强制无缓存重建（依赖或 Dockerfile 怀疑有问题时）：**

```bash
cd ~/TradingBuddy
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

---

### 9.5 日志

```bash
cd ~/TradingBuddy

# 最近 100 行
docker compose -f docker-compose.prod.yml logs --tail=100 vibe-trading

# 持续跟踪（Ctrl+C 退出，不影响容器）
docker compose -f docker-compose.prod.yml logs -f vibe-trading

# 按关键词过滤（如 OCR、401、error）
docker compose -f docker-compose.prod.yml logs --tail=200 vibe-trading | grep -iE 'ocr|error|401'
```

---

### 9.6 进入容器与组件自检

```bash
# 容器名以 docker compose ps 为准，一般为 tradingbuddy-vibe-trading-1
docker exec -it tradingbuddy-vibe-trading-1 bash

# 不进入 shell，直接测 OCR
docker exec -it tradingbuddy-vibe-trading-1 python -c \
  "from rapidocr_onnxruntime import RapidOCR; print('ocr ok')"

# 测 WeasyPrint（Shadow 报告 PDF）
docker exec -it tradingbuddy-vibe-trading-1 python -c \
  "from weasyprint import HTML; print('weasyprint ok')"
```

---

### 9.7 数据卷与备份

runs 与 sessions 在 Docker **named volumes** 里，`docker compose down` **不会**删除它们：

```bash
docker volume ls | grep vibe
```

**建议定期备份：**

- `~/TradingBuddy/agent/.env`（含密钥，勿泄露）
- 重要 run 可从 Agent / runs 目录导出

`.env` 备份示例：

```bash
cp ~/TradingBuddy/agent/.env ~/TradingBuddy/agent/.env.bak.$(date +%Y%m%d)
chmod 600 ~/TradingBuddy/agent/.env.bak.*
```

---

### 9.8 磁盘清理（可选）

多次 `up --build` 会留下旧镜像，占磁盘：

```bash
# 查看 Docker 占用
docker system df

# 删除未使用的镜像/构建缓存（不影响正在运行的容器）
docker image prune -f
docker builder prune -f

# 慎用：会删掉所有未使用镜像与卷
# docker system prune -a
```

---

### 9.9 常用场景速查

| 场景 | 命令 |
|------|------|
| 改 LLM / API key | 编辑 `agent/.env` → `up -d --force-recreate` |
| 改 Dockerfile / 拉代码 | `up --build -d` |
| 服务假死 | `restart` 或 `up -d --force-recreate` |
| 持仓 OCR 报错 | 见 [§11 持仓截图 OCR](#持仓截图-ocr-失败--libxcbso1) |
| 浏览器 401 | Settings 填 Server API key，与 `API_AUTH_KEY` 一致 |
| 看是否在 build | `pgrep -af "docker compose"` 或 `tail /tmp/vibe-deploy.log` |

---

## 10. 安全建议

1. **必须设置 `API_AUTH_KEY`**：`docker-compose.prod.yml` 将端口绑定到 `0.0.0.0`，无 key 等于公开裸奔。
2. **安全组限制来源 IP**：52889 为非默认端口，仍应在入方向规则中尽量收窄来源。
3. **`.env` 权限**：`chmod 600 agent/.env`，仅 root 或部署用户可读。
4. **自托管非可信密钥库**：LLM、Tushare 等 token 只应放在你控制的服务器上；勿使用不可信的第三方托管。
5. **HTTPS（可选）**：生产环境可在前面加 Nginx / Caddy 反代到 `127.0.0.1:52889`，并配置 TLS 证书（如 Let's Encrypt）。
6. **勿开启** `VIBE_TRADING_TRUST_DOCKER_LOOPBACK=1`：该选项仅用于本地 `docker-compose.yml` 开发场景。

---

## 11. 故障排查

### Docker 安装冲突

见 [§3 安装 Docker](#3-安装-dockerubuntu--阿里云)。

### 拉镜像超时 / `registry.docker-cn.com` / `DeadlineExceeded`

**症状：**

```text
failed to resolve source metadata for docker.io/library/python:3.11-slim
Head "https://registry.docker-cn.com/...": i/o timeout
```

**处理：**

1. 按 [§3.5](#35-配置-docker-镜像加速国内-ecs-必做) 更新 `/etc/docker/daemon.json`，**去掉** `registry.docker-cn.com`。
2. `sudo systemctl restart docker`
3. 单独测试：`sudo docker pull python:3.11-slim`
4. 再执行：`sudo docker compose -f docker-compose.prod.yml build --no-cache`

若单个 mirror 不稳定，多填几个，或使用阿里云 ACR 专属加速地址。

### GitHub clone 失败

见 [§4 拉取代码](#4-拉取代码)。

### pip 下载超时 / `Read timed out` / `files.pythonhosted.org`

**症状（构建卡在 `pip install -r agent/requirements.txt`，大包如 scipy 失败）：**

```text
ReadTimeoutError: HTTPSConnectionPool(host='files.pythonhosted.org', port=443): Read timed out.
```

**原因：** 国内 ECS 访问官方 PyPI 慢或不稳定；`scipy`、`pandas` 等 wheel 体积大，默认 pip 超时易断。

**处理：**

1. 使用已配置 **阿里云 PyPI 镜像** 的 `Dockerfile`（默认 `PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/`）。
2. 同步最新 `Dockerfile` 到服务器后重建：

```bash
cd ~/TradingBuddy
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

3. 仍失败时可换清华源构建：

```bash
docker compose -f docker-compose.prod.yml build --no-cache \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
docker compose -f docker-compose.prod.yml up -d
```

4. 建议后台 build，避免 SSH 断开：`nohup docker compose ... up --build -d > /tmp/vibe-deploy.log 2>&1 &`

### 构建失败 / 内存不足

- 症状：`npm run build` 或 `pip install` 被 OOM Kill。
- 处理：升级 ECS 到 ≥ 2 GB 内存，或添加 swap 后重试 build。

### 外网无法访问，本机 curl 正常

- 检查阿里云安全组是否放行 **52889**。
- 检查 `ufw` / `iptables` 是否拦截。

### 页面能开，但 Agent 报 401 / Auth required

- 确认 `agent/.env` 中已设置 `API_AUTH_KEY`。
- 在 Settings 中填写相同的 **Server API key** 并保存。
- 修改 `.env` 后需重建容器：`sudo docker compose -f docker-compose.prod.yml up -d --force-recreate`

### 容器启动后立即退出

```bash
sudo docker compose -f docker-compose.prod.yml logs vibe-trading
```

常见原因：`.env` 语法错误、必填 LLM 配置缺失、端口被占用。

### 持仓截图 OCR 失败 / `libxcb.so.1`

**症状：** Holdings 上传截图提示「OCR 识别失败」；容器内执行：

```bash
docker exec -it tradingbuddy-vibe-trading-1 python -c "from rapidocr_onnxruntime import RapidOCR"
# ImportError: libxcb.so.1: cannot open shared object file
```

**原因：** `python:3.11-slim` 镜像缺 OpenCV（RapidOCR 依赖）所需的系统库。

**处理：** 确保 `Dockerfile` runtime 阶段安装了 OpenCV / ONNX / WeasyPrint 相关系统库（见 `Dockerfile` 中 `apt-get install` 列表），然后重建：

```bash
cd ~/TradingBuddy
docker compose -f docker-compose.prod.yml up --build -d
docker exec -it tradingbuddy-vibe-trading-1 python -c "from rapidocr_onnxruntime import RapidOCR; print('ok')"
```

### 端口被占用

```bash
sudo ss -tlnp | grep 52889
```

可修改 `docker-compose.prod.yml` 中 `"52889:8899"` 左侧端口号，并同步更新安全组规则。

---

## 12. 与本地 Docker 的区别

| 项目 | `docker-compose.yml`（本地） | `docker-compose.prod.yml`（服务器） |
|------|-------------------------------|-------------------------------------|
| 端口绑定 | `127.0.0.1:8899` | `0.0.0.0:52889` |
| 对外访问 | 仅本机 | 公网（需安全组） |
| Loopback 信任 | 默认 `VIBE_TRADING_TRUST_DOCKER_LOOPBACK=1` | 无（须 `API_AUTH_KEY`） |
| 典型用途 | 开发、本地试用 | 阿里云 ECS 私有部署 |

---

## 快速命令参考

```bash
cd ~/TradingBuddy

# 首次 / 更新代码后部署
docker compose -f docker-compose.prod.yml up --build -d

# 仅改 agent/.env 后重新加载
docker compose -f docker-compose.prod.yml up -d --force-recreate

# 健康检查
curl -s http://127.0.0.1:52889/health

# 状态与日志
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=50 vibe-trading

# 停止
docker compose -f docker-compose.prod.yml down
```

详细说明见 [§9 日常运维](#9-日常运维)。

---

## 相关文件

- `docker-compose.prod.yml` — 生产/远程 compose 配置
- `docker-compose.yml` — 本地开发 compose 配置
- `Dockerfile` — 多阶段镜像构建
- `agent/.env.example` — 环境变量模板
- `README_zh.md` — 项目总览与本地快速开始
