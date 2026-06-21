# iching-ai.cn 部署指南

> 适用于阿里云 ECS **2核 2GiB 1Mbps**，操作系统 Ubuntu 22.04 / CentOS 7.9+
>
> 应用栈：Python FastAPI + SQLite + Jinja2 | 反向代理：nginx | SSL：Let's Encrypt

---

## 目录

- [1. 服务器初始化](#1-服务器初始化)
- [2. DNS 配置](#2-dns-配置)
- [3. 克隆项目与安装依赖](#3-克隆项目与安装依赖)
- [4. systemd 服务](#4-systemd-服务)
- [5. nginx 配置](#5-nginx-配置)
- [6. SSL 证书](#6-ssl-证书)
- [7. 启动与开机自启](#7-启动与开机自启)
- [8. 验证部署](#8-验证部署)
- [9. 1Mbps 带宽优化策略](#9-1mbps-带宽优化策略)
- [10. 日常运维](#10-日常运维)
- [附录：一键部署](#附录一键部署)

---

## 1. 服务器初始化

SSH 登录到服务器（首次登录会提示修改密码）：

```bash
ssh root@<服务器公网IP>
```

### 1.1 Ubuntu 系统

```bash
# 更新系统包
apt update && apt upgrade -y

# 安装必要依赖
apt install -y python3.10 python3.10-venv python3.10-dev \
               nginx git curl net-tools certbot python3-certbot-nginx
```

### 1.2 CentOS 系统

```bash
# 更新系统
yum update -y

# 安装 EPEL 和必要依赖
yum install -y epel-release
yum install -y python3.11 python3.11-pip python3.11-devel \
               nginx git curl net-tools certbot python3-certbot-nginx
```

### 1.3 验证安装

```bash
python3 --version     # 确保 >= 3.10
nginx -v
git --version
certbot --version
```

---

## 2. DNS 配置

在 **阿里云 DNS 控制台**（云解析 DNS）为域名 `iching-ai.cn` 添加 A 记录：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| A | `@` | 服务器公网IP | 600 |
| A | `www` | 服务器公网IP | 600 |

配置后等待 DNS 生效（通常几分钟），用 `ping iching-ai.cn` 确认 IP 正确。

---

## 3. 克隆项目与安装依赖

```bash
# 创建应用目录
mkdir -p /opt/iching

# 克隆项目（server 分支）
git clone -b server https://github.com/netlinemelon/iching.git /opt/iching

# 进入项目目录
cd /opt/iching

# 创建 Python 虚拟环境
python3 -m venv venv

# 激活虚拟环境并安装依赖
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 创建数据目录
mkdir -p /opt/iching/data

# 配置环境变量
cp .env.example .env
```

### 3.1 编辑 .env 文件

```bash
nano /opt/iching/.env
```

关键配置（根据实际情况修改）：

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | **必填** AI API 密钥 | `sk-xxx` |
| `ANTHROPIC_BASE_URL` | API 端点 | `https://api.deepseek.com/anthropic` |
| `ANTHROPIC_MODEL` | 模型名称 | `deepseek-v4-pro` |
| `REDIS_URL` | Redis 连接（可选） | `redis://localhost:6379/0` |
| `DEBUG` | 生产环境设为 `false` | `false` |
| `HOST` | 监听地址 | `127.0.0.1` |
| `PORT` | 监听端口 | `8088` |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite+aiosqlite:///./data/iching.db` |

> **注意**：生产环境务必设置 `DEBUG=false`，否则性能会下降且可能泄露调试信息。

---

## 4. systemd 服务

创建 systemd 服务文件，使应用在后台持续运行并支持开机自启。

```bash
# 创建 iching 用户（用于运行应用，提高安全性）
useradd -r -s /usr/sbin/nologin -M www-data 2>/dev/null || true

# 设置目录权限
chown -R www-data:www-data /opt/iching
chmod 755 /opt/iching
chmod 755 /opt/iching/data

# 部署 service 文件
cp deploy/iching.service /etc/systemd/system/iching.service

# 重新加载 systemd
systemctl daemon-reload
```

服务文件路径：`/etc/systemd/system/iching.service`

配置要点：
- 以 `www-data` 用户身份运行，**禁止 root 运行**
- 工作目录为 `/opt/iching`
- 自动重启（异常退出时）
- 日志由 journald 管理

---

## 5. nginx 配置

### 5.1 部署配置文件

```bash
# 复制 nginx 配置
cp deploy/iching-nginx.conf /etc/nginx/sites-available/iching-ai.cn

# 启用站点（创建软链接）
ln -sf /etc/nginx/sites-available/iching-ai.cn /etc/nginx/sites-enabled/

# 测试配置是否正确
nginx -t
```

> **CentOS 注意**：配置文件路径为 `/etc/nginx/conf.d/iching-ai.cn.conf`，直接复制到该目录即可，无需创建软链接。

### 5.2 配置要点说明

| 功能 | 配置位置 | 说明 |
|------|---------|------|
| HTTP→HTTPS 重定向 | `server listen 80` 块 | 所有 HTTP 流量强制跳转 HTTPS |
| SSL 终止 | `server listen 443 ssl` 块 | 由 nginx 处理 TLS 加密 |
| 反向代理 | `location /` 块 | 非静态文件请求转发到 `127.0.0.1:8088` |
| 静态文件直服 | `location /static/` 块 | 绕过 Python，nginx 直接返回静态文件 |
| gzip 压缩 | `http` 块 | 对 HTML/CSS/JS/JSON 启用压缩 |
| 静态缓存 | `location /static/` 内的 `expires` | 静态文件缓存 7 天 |
| 安全头 | `server` 块 | HSTS、XSS 防护等安全相关 HTTP 头 |

### 5.3 关键代理头说明

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

`X-Real-IP` 头用于将客户端真实 IP 传递给应用，配合限流中间件使用。生产环境中，`forwarded_allow_ips=""` 确保应用层不信任任何代理头，防止 IP 伪造绕过限流。

---

## 6. SSL 证书

使用 Let's Encrypt 免费证书（Certbot 自动续期）：

```bash
# 申请证书（需先完成 DNS 配置并确保域名指向本机）
certbot --nginx -d iching-ai.cn -d www.iching-ai.cn

# 按照提示：
# 1. 输入邮箱（用于过期提醒）
# 2. 同意服务条款
# 3. 选择是否将 HTTP 重定向到 HTTPS（选择是）
```

### 自动续期

Certbot 会自动添加 systemd timer 或 cron 任务。验证方法：

```bash
# 测试续期流程（不实际续期）
certbot renew --dry-run

# 查看定时任务
systemctl list-timers | grep certbot
# 或
crontab -l | grep certbot
```

---

## 7. 启动与开机自启

```bash
# 启动应用服务
systemctl enable --now iching

# 查看服务状态
systemctl status iching

# 查看实时日志
journalctl -u iching -f

# 重新加载 nginx（如果之前已启动）
systemctl reload nginx

# 或首次启动 nginx
systemctl enable --now nginx
```

### 启动后检查

```bash
# 检查端口监听
ss -tlnp | grep -E '8088|80|443'

# 检查进程
ps aux | grep iching
```

---

## 8. 验证部署

### 8.1 API 健康检查

```bash
# 健康检查端点
curl https://iching-ai.cn/api/health

# 预期响应：
# {"status":"ok","timestamp":...,"version":"1.0.0"}
```

### 8.2 浏览器访问

打开 https://iching-ai.cn，确认：
- ✓ 页面正常加载
- ✓ HTTPS 证书有效（地址栏显示安全锁）
- ✓ 静态资源（CSS/JS/图片）正常加载
- ✓ 占卜功能正常
- ✓ 响应速度在合理范围内

### 8.3 DNS 验证

```bash
# 确认 DNS 解析正确
nslookup iching-ai.cn
nslookup www.iching-ai.cn
```

---

## 9. 1Mbps 带宽优化策略

1Mbps 带宽约等于 **128KB/s** 的理论最大传输速度，优化至关重要。

### 9.1 nginx gzip 压缩（收益最大）

已在 nginx 配置中启用，预期压缩率：

| 文件类型 | 原始大小 | 压缩后 | 压缩率 |
|---------|---------|--------|--------|
| HTML | ~5KB | ~1.5KB | 70% |
| CSS | ~20KB | ~4KB | 80% |
| JavaScript | ~30KB | ~8KB | 73% |
| JSON | ~10KB | ~2KB | 80% |

### 9.2 静态文件缓存

```
expires 7d;
add_header Cache-Control "public, immutable";
```

- 用户首次访问后，静态资源在本地缓存 7 天
- 后续页面加载几乎零带宽消耗
- 更新静态资源时通过修改文件名（如 `main.v2.css`）强制刷新

### 9.3 图片优化

```bash
# 压缩收款码图片（确保单张 < 100KB）
apt install -y imagemagick
convert /opt/iching/app/static/img/wechat-qr.jpg -resize 400x400 -quality 70 /opt/iching/app/static/img/wechat-qr.jpg
convert /opt/iching/app/static/img/alipay-qr.jpg -resize 400x400 -quality 70 /opt/iching/app/static/img/alipay-qr.jpg
```

### 9.4 减少 HTTP 请求

- 合并 CSS 文件（生产环境考虑合并为一个文件）
- 合并 JavaScript 文件
- 使用 CSS Sprite 或内联小图标

### 9.5 带宽监控

```bash
# 安装 nethogs 查看实时带宽占用
apt install -y nethogs
nethogs eth0

# 查看 nginx 访问日志中的流量
tail -f /var/log/nginx/access.log | awk '{print $1, $10, $7}'
```

---

## 10. 日常运维

### 10.1 查看日志

```bash
# 应用日志（journald）
journalctl -u iching -n 100 --no-pager
journalctl -u iching -f                          # 实时跟踪

# nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 10.2 更新代码

```bash
cd /opt/iching
git pull origin server
source venv/bin/activate
pip install -r requirements.txt
systemctl restart iching
```

### 10.3 备份数据库

```bash
# SQLite 数据库文件
cp /opt/iching/data/iching.db /opt/iching/data/iching.db.bak.$(date +%Y%m%d)

# 定期备份可添加 cron 任务：
# crontab -e
# 0 3 * * * cp /opt/iching/data/iching.db /opt/iching/data/backups/iching.db.$(date +\%Y\%m\%d)
```

### 10.4 重启服务

```bash
systemctl restart iching      # 重启应用
systemctl reload nginx        # 重载 nginx 配置（不中断连接）
systemctl restart nginx       # 完全重启 nginx
```

### 10.5 SSL 证书续期

```bash
# 手动续期（自动续期失败时的备选方案）
certbot renew
systemctl reload nginx
```

### 10.6 服务器监控

```bash
# 查看系统资源
htop                                    # 需要安装
free -h                                 # 内存
df -h                                   # 磁盘
ss -tlnp                                # 端口监听

# 查看磁盘 I/O（SQLite 频繁写入时关注）
iostat -x 1 5
```

---

## 附录：一键部署

如果从头开始部署，可以使用 `deploy/setup.sh` 一键部署脚本：

```bash
# 以 root 登录服务器后
bash <(curl -sL https://raw.githubusercontent.com/netlinemelon/iching/server/deploy/setup.sh)
```

该脚本会完成除 DNS 配置和 SSL 证书申请外的所有步骤。详见 `deploy/setup.sh` 中的注释说明。

---

> **文档版本**: v1.0 | **最后更新**: 2026-06-21
>
> 如有问题欢迎提交 GitHub Issue: https://github.com/netlinemelon/iching/issues
