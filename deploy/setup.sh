#!/bin/bash
# =============================================================================
# iching-ai.cn — 一键部署脚本
# 适用环境：Ubuntu 22.04+ / CentOS 7.9+，阿里云 ECS 2核 2GiB 1Mbps
# 使用方法：以 root 用户运行 bash setup.sh
# 前提条件：
#   1. 域名 iching-ai.cn 已解析到服务器 IP
#   2. 服务器已安装 curl（一般默认已安装）
#   3. 端口 80 和 443 已在阿里云安全组中开放
# =============================================================================

set -e  # 任何一步失败则退出脚本

# ---- 颜色输出 ----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ---- 辅助函数 ----
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---- 检查是否以 root 运行 ----
if [ "$EUID" -ne 0 ]; then
    error "请以 root 用户运行此脚本（sudo bash setup.sh）"
    exit 1
fi

# =============================================================================
# 步骤 1：安装系统依赖
# =============================================================================
info "=========================================="
info "步骤 1/10：安装系统依赖"
info "=========================================="

# 检测操作系统类型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS=$(uname -s)
fi

case $OS in
    ubuntu|debian)
        info "检测到操作系统：$OS，使用 apt 安装依赖"
        apt update -qq
        apt install -y python3 python3-venv python3-dev \
                       nginx git curl net-tools certbot python3-certbot-nginx
        ;;
    centos|rhel|fedora|alinux|alinux2|alinux3)
        info "检测到操作系统：$OS，使用 yum 安装依赖"
        yum install -y epel-release
        yum install -y python3 python3-pip python3-devel \
                       nginx git curl net-tools certbot python3-certbot-nginx
        ;;
    *)
        error "不支持的操作系统：$OS。请手动安装依赖。"
        exit 1
        ;;
esac

info "系统依赖安装完成。"

# =============================================================================
# 步骤 2：创建目录和用户
# =============================================================================
info "=========================================="
info "步骤 2/10：创建目录和用户"
info "=========================================="

# 创建 www-data 用户（如果不存在）
if id "www-data" &>/dev/null; then
    info "用户 www-data 已存在，跳过创建。"
else
    useradd -r -s /usr/sbin/nologin -M www-data
    info "用户 www-data 创建完成。"
fi

# 创建应用相关目录
mkdir -p /opt/iching/data
mkdir -p /opt/iching/deploy
info "应用目录 /opt/iching 准备就绪。"

# =============================================================================
# 步骤 3：克隆项目代码
# =============================================================================
info "=========================================="
info "步骤 3/10：从 GitHub 克隆项目代码"
info "=========================================="

if [ -d "/opt/iching/.git" ]; then
    info "项目已存在，正在更新代码..."
    cd /opt/iching
    git fetch origin
    git reset --hard origin/server
else
    info "正在克隆项目（server 分支）..."
    # 如果目录非空但无 .git，先清空
    rm -rf /opt/iching/*
    git clone -b server https://github.com/netlinemelon/iching.git /opt/iching
fi

info "代码克隆/更新完成。"

# =============================================================================
# 步骤 4：创建 Python 虚拟环境
# =============================================================================
info "=========================================="
info "步骤 4/10：创建 Python 虚拟环境"
info "=========================================="

if [ -d "/opt/iching/venv" ]; then
    info "虚拟环境已存在，跳过创建。"
else
    python3 -m venv /opt/iching/venv
    info "虚拟环境创建完成。"
fi

# =============================================================================
# 步骤 5：安装 Python 依赖
# =============================================================================
info "=========================================="
info "步骤 5/10：安装 Python 依赖"
info "=========================================="

/opt/iching/venv/bin/pip install --upgrade pip -q
/opt/iching/venv/bin/pip install -r /opt/iching/requirements.txt -q

info "Python 依赖安装完成。"

# =============================================================================
# 步骤 6：配置 .env 环境变量
# =============================================================================
info "=========================================="
info "步骤 6/10：配置 .env 环境变量"
info "=========================================="

if [ -f "/opt/iching/.env" ]; then
    warn "已存在 .env 文件，将保留现有配置。"
    warn "如需重新配置，请手动编辑 /opt/iching/.env"
else
    # 从示例文件复制
    cp /opt/iching/.env.example /opt/iching/.env

    echo ""
    echo -e "${YELLOW}==================== 重要配置 ====================${NC}"
    echo -e "${YELLOW}请编辑 /opt/iching/.env 文件，填入以下关键配置：${NC}"
    echo ""
    echo "  1. ANTHROPIC_API_KEY — AI 解卦 API 密钥（必填）"
    echo "     获取方式：https://platform.deepseek.com/"
    echo ""
    echo "  2. DEBUG — 生产环境请设为 false"
    echo ""
    echo -e "${YELLOW}==================================================${NC}"
    echo ""

    # 提示用户编辑 .env
    read -p "是否现在编辑 .env 文件？(y/n，默认 y): " EDIT_ENV
    EDIT_ENV=${EDIT_ENV:-y}
    if [ "$EDIT_ENV" = "y" ] || [ "$EDIT_ENV" = "Y" ]; then
        # 检测可用的编辑器
        if command -v nano &>/dev/null; then
            nano /opt/iching/.env
        elif command -v vim &>/dev/null; then
            vim /opt/iching/.env
        else
            vi /opt/iching/.env
        fi
    fi
fi

# =============================================================================
# 步骤 7：部署 nginx 配置
# =============================================================================
info "=========================================="
info "步骤 7/10：部署 nginx 配置"
info "=========================================="

# 将 deploy 目录中的配置文件复制到 nginx 目录
case $OS in
    ubuntu|debian)
        # Ubuntu/Debian 使用 sites-available + sites-enabled
        NGINX_CONF_DIR="/etc/nginx/sites-available"
        NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"

        cp /opt/iching/deploy/iching-nginx.conf "$NGINX_CONF_DIR/iching-ai.cn"

        # 创建软链接启用站点
        ln -sf "$NGINX_CONF_DIR/iching-ai.cn" "$NGINX_ENABLED_DIR/"

        # 移除默认站点
        rm -f "$NGINX_ENABLED_DIR/default"
        ;;
    centos|rhel|fedora|alinux|alinux2|alinux3)
        # CentOS/RHEL 使用 conf.d 目录
        NGINX_CONF_DIR="/etc/nginx/conf.d"

        cp /opt/iching/deploy/iching-nginx.conf "$NGINX_CONF_DIR/iching-ai.cn.conf"

        # CentOS 默认关闭了 443，需要确认 SELinux
        if command -v getenforce &>/dev/null && [ "$(getenforce)" = "Enforcing" ]; then
            warn "SELinux 处于 Enforcing 模式，可能需要放行 443 端口："
            echo "  semanage port -a -t http_port_t -p tcp 443"
        fi
        ;;
esac

# 测试 nginx 配置
info "测试 nginx 配置..."
if nginx -t; then
    info "nginx 配置测试通过。"
else
    error "nginx 配置测试失败，请检查配置文件。"
    exit 1
fi

# =============================================================================
# 步骤 8：部署 systemd 服务
# =============================================================================
info "=========================================="
info "步骤 8/10：部署 systemd 服务"
info "=========================================="

cp /opt/iching/deploy/iching.service /etc/systemd/system/iching.service
systemctl daemon-reload

info "systemd 服务部署完成。"

# =============================================================================
# 步骤 9：设置目录权限
# =============================================================================
info "=========================================="
info "步骤 9/10：设置目录权限"
info "=========================================="

# 确保 www-data 用户能读写应用目录和数据库
chown -R www-data:www-data /opt/iching
chmod 755 /opt/iching
chmod 755 /opt/iching/data

# 确保 nginx 能读取静态文件（www-data 或 nginx 用户）
if [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    # CentOS 上 nginx 以 nginx 用户运行，需添加 www-data 到 nginx 组或调整权限
    usermod -aG www-data nginx 2>/dev/null || true
fi

info "权限设置完成。"

# =============================================================================
# 步骤 10：启动服务
# =============================================================================
info "=========================================="
info "步骤 10/10：启动服务"
info "=========================================="

# 启动应用服务（开机自启）
info "正在启动 iching 服务..."
systemctl enable --now iching
info "iching 服务状态："
systemctl status iching --no-pager -l | head -20

# 启动 nginx
info "正在启动 nginx..."
systemctl enable --now nginx
systemctl reload nginx 2>/dev/null || true
info "nginx 服务状态："
systemctl status nginx --no-pager -l | head -10

# =============================================================================
# 完成
# =============================================================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  iching-ai.cn 部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "下一步操作："
echo ""
echo -e "  1. ${YELLOW}DNS 配置${NC}（如未完成）："
echo -e "     在阿里云 DNS 控制台添加 A 记录："
echo -e "       @ → 服务器公网IP"
echo -e "       www → 服务器公网IP"
echo ""
echo -e "  2. ${YELLOW}SSL 证书${NC}（必须申请才能启用 HTTPS）："
echo -e "     运行：certbot --nginx -d iching-ai.cn -d www.iching-ai.cn"
echo ""
echo -e "  3. ${YELLOW}验证部署${NC}："
echo -e "     curl http://iching-ai.cn/api/health"
echo ""
echo -e "  4. ${YELLOW}查看应用日志${NC}："
echo -e "     journalctl -u iching -f"
echo ""
echo -e "  5. ${YELLOW}编辑 .env 配置${NC}（如需修改）："
echo -e "     nano /opt/iching/.env && systemctl restart iching"
echo ""

# 检查是否已申请 SSL 证书
if [ -f "/etc/letsencrypt/live/iching-ai.cn/fullchain.pem" ]; then
    info "检测到 SSL 证书已存在，HTTPS 应可正常访问。"
else
    warn "未检测到 SSL 证书，请尽快运行 certbot 申请证书！"
    warn "   certbot --nginx -d iching-ai.cn -d www.iching-ai.cn"
fi

# 检查端口监听
info "端口监听状态："
ss -tlnp | grep -E ':(80|443|8088) ' || echo "  端口未监听（服务可能尚未完全启动）"
