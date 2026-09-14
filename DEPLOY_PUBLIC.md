# Company Agent 公网演示部署

本文方案面向作品集演示：Ubuntu 云主机 + Docker Compose + Caddy HTTPS。公网只开放 Caddy 的 80/443 端口；FastAPI、Redis 和 Ollama 不直接暴露。站点使用 HTTP Basic Auth，避免陌生人消耗模型额度或滥用附件上传。

## 1. 准备资源

- Ubuntu 22.04/24.04 云主机：建议至少 2 vCPU、4 GB 内存、30 GB SSD。
- 一个解析到主机公网 IP 的域名。没有自有域名时，可以暂用 `公网IP.sslip.io`，例如 `203.0.113.10.sslip.io`。
- 放通入站 TCP 22、80、443，并放通 UDP 443。不要放通 6379、8000、11434。
- 可正常调用的 DeepSeek API Key，并设置账户消费上限。

若服务器位于中国大陆，域名公网访问通常涉及备案。只做面试演示时，香港、新加坡等区域通常更省事，但应先确认服务器能访问 DeepSeek API。

## 2. 安装 Docker

登录服务器后执行：

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker "$USER"
newgrp docker
docker version
docker compose version
```

`get.docker.com` 是 Docker 官方便捷安装脚本；对供应链要求较高时，应改用 Docker 官方 apt 仓库安装流程。

## 3. 上传代码

推荐将代码推送到自己的私有 Git 仓库，然后在服务器克隆：

```bash
git clone <你的仓库地址> company_agent
cd company_agent
```

也可以用 `scp`/SFTP 上传整个目录，但不要上传 `.venv`、`.env`、`uploads` 和日志。

## 4. 配置域名与密码

先将域名的 A 记录解析到服务器公网 IP。然后创建配置：

```bash
cp .env.example .env
docker run --rm caddy:2-alpine caddy hash-password --plaintext '换成一个强密码'
nano .env
```

把输出的密码哈希填到 `DEMO_PASSWORD_HASH`，并保留单引号，避免哈希中的 `$` 被 Compose 当作变量。配置示例：

```dotenv
DOMAIN=demo.example.com
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_IMAGE_MODEL=deepseek-v4-flash-vision-exp
DEMO_USERNAME=interviewer
DEMO_PASSWORD_HASH='$2a$14$完整哈希'
```

如果 DeepSeek 返回“模型不存在”，请把两个模型名改成当前账户实际可用的模型；不同 API 渠道支持的模型名可能不同。

## 5. 启动

```bash
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=200
```

首次启动会下载 Python 镜像、Ollama 镜像和 `nomic-embed-text`，通常比后续启动慢。日志稳定后按 `Ctrl+C` 退出日志查看，不会停止服务。

访问 `https://你的域名`。浏览器会先要求输入 `.env` 中配置的演示账号和密码。Caddy 会自动申请和续期 TLS 证书。

## 6. 验证

```bash
curl -I https://你的域名
docker compose ps
docker compose logs app --tail=100
docker compose logs caddy --tail=100
```

未携带账号密码时返回 `401` 是正确行为。随后应在浏览器中完成以下检查：

1. 页面可以打开，静态资源无 404。
2. 提问能够流式返回内容。
3. 制度问题能够调用检索工具。
4. 刷新后会话仍然有效。
5. 上传、删除和文档修改功能正常。

## 7. 更新与维护

拉取代码并重建：

```bash
git pull
docker compose up -d --build
docker image prune -f
```

查看状态和日志：

```bash
docker compose ps
docker compose logs -f --tail=200 app
```

重启：

```bash
docker compose restart
```

停止但保留数据：

```bash
docker compose down
```

不要执行 `docker compose down -v`，该命令会删除 Chroma、Redis、Ollama 和上传文件卷。

## 8. 演示环境安全清单

- 只开放 22、80、443；SSH 优先使用密钥并禁止密码登录。
- 把 Basic Auth 账号密码单独发给面试官，不要写进公开简历或 Git 仓库。
- 给 DeepSeek 账户设置低额度告警和消费上限。
- 定期更新系统、Docker 镜像和 Python 依赖。
- 定期清理演示附件；当前应用没有自动过期清理。
- 使用虚构制度和脱敏文件，不上传真实公司或客户资料。
- 当前方案适合低流量作品集展示，不等同于企业生产环境。
