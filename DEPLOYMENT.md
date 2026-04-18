# 部署指南

## 服务器要求

| 项目 | 要求 |
|-----|------|
| CPU | 2 核以上 |
| 内存 | 4GB 以上 |
| 磁盘 | 50GB 以上 |
| 系统 | Ubuntu 20.04 / CentOS 7+ |
| Docker | 20.10+ (可选) |

## 方式一：传统部署

### 1. 环境准备

```bash
# 安装 Python 3.10+
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip

# 安装 Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs

# 安装 MySQL
sudo apt install mysql-server
sudo mysql_secure_installation
```

### 2. 数据库配置

```sql
-- 创建数据库
CREATE DATABASE quality_check CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'qc_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON quality_check.* TO 'qc_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 后端部署

```bash
cd /opt/quality-check
git pull origin main

# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 初始化数据库
python -c "from database import init_db; init_db()"

# 启动服务（使用 systemd）
sudo nano /etc/systemd/system/quality-check.service
```

systemd 配置：
```ini
[Unit]
Description=Quality Check Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/quality-check
ExecStart=/opt/quality-check/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable quality-check
sudo systemctl start quality-check
```

### 4. 前端部署

```bash
cd frontend

# 安装依赖
npm install
npm run build

# 将构建文件复制到 Nginx 目录
sudo cp -r dist/* /var/www/html/

# 配置 Nginx
sudo nano /etc/nginx/sites-available/default
```

Nginx 配置：
```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 5. HTTPS 配置（使用 Let's Encrypt）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 方式二：Docker 部署

### 1. 安装 Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql://qc_user:password@db:3306/quality_check
      - SECRET_KEY=${SECRET_KEY}
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
    depends_on:
      - db
    restart: always

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: always

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=quality_check
      - MYSQL_USER=qc_user
      - MYSQL_PASSWORD=password
    volumes:
      - mysql_data:/var/lib/mysql
    restart: always

volumes:
  mysql_data:
```

### 3. 启动服务

```bash
docker-compose up -d
```

## 环境变量配置

### 后端 (.env)

```env
# 数据库
DATABASE_URL=mysql+pymysql://qc_user:password@localhost:3306/quality_check

# JWT 密钥（生产环境必须使用强密钥）
SECRET_KEY=your-very-long-secret-key-at-least-48-characters

# AI API
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx

# 允许的域名
ALLOWED_ORIGINS=https://your-domain.com

# 日志
LOG_LEVEL=INFO
```

### 生成强密钥

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 验证部署

### 后端健康检查

```bash
curl http://localhost:8000/health
# 期望返回: {"status":"healthy","database":"connected","version":"1.0.0"}
```

### API 文档

- Swagger UI: http://your-domain.com/docs
- ReDoc: http://your-domain.com/redoc

## 备份

### 数据库备份

```bash
# 备份
mysqldump -u qc_user -p quality_check > backup_$(date +%Y%m%d).sql

# 恢复
mysql -u qc_user -p quality_check < backup_20260401.sql
```

### 文件备份

```bash
# 备份上传的照片和报告
tar -czf backup_files_$(date +%Y%m%d).tar.gz data/photos/ data/reports/
```

## 监控

### 检查服务状态

```bash
# 后端状态
sudo systemctl status quality-check

# Nginx 状态
sudo systemctl status nginx

# MySQL 状态
sudo systemctl status mysql
```

### 查看日志

```bash
# 后端日志
sudo journalctl -u quality-check -f

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 更新

```bash
# 后端更新
cd /opt/quality-check
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart quality-check

# 前端更新
cd /opt/quality-check/frontend
git pull
npm install
npm run build
sudo systemctl restart nginx
```
