# Docker 部署说明

## 1. 准备环境变量

在项目根目录复制示例文件：

```bash
cp .env.example .env
```

编辑 `.env`，至少填写：

```env
DASHSCOPE_API_KEY=sk-your-api-key
API_REGION=beijing
```

如实时模型需要独立 Key，可额外配置：

```env
DASHSCOPE_API_KEY_REALTIME=sk-your-realtime-api-key
```

## 2. 启动

```bash
docker compose up -d --build
```

默认访问：

- 前端：http://服务器IP 或 http://localhost
- 健康检查：http://服务器IP/health
- API 文档：http://服务器IP/docs

如果宿主机 80 端口已被占用，可把 `docker-compose.yml` 中的 `80:80` 改回 `8080:80`，然后通过 `http://服务器IP:8080` 访问。

## 3. 查看日志

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

## 4. 停止

```bash
docker compose down
```

## 5. 配置挂载

`docker-compose.yml` 默认把以下目录挂载到后端容器：

```text
./config  -> /app/config
./prompts -> /app/prompts
```

因此修改 `config/settings.yaml`、`config/personas/*.yaml` 或 `prompts/interaction_rules.txt` 后，重启后端即可生效：

```bash
docker compose restart backend
```

## 6. 生产域名和 HTTPS

当前 compose 提供基础 HTTP 部署。正式公网部署建议在外层增加 HTTPS 入口（云负载均衡、Caddy、Traefik 或宿主机 Nginx），并确保 WebSocket 路径 `/api/realtime/ws` 支持 Upgrade。
