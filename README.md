# TG2Cloud NAS 精简版

> 从 [TG2Cloud](https://github.com/LuoPoJunZi/TG2Cloud)（MIT，作者 LuoPoJunZi / 原作者 whyhhh20 的 TG115）中**仅剥离「Telegram 机器人连接」与「文件转存」核心**，去掉全部 VPS 图形化部署器、SSH 隧道、主机密钥校验、VPS 资源探测与 manage.sh 运维脚本，改造为可在局域网 NAS 上以 Docker 独立运行的精简项目。**OpenList 单独部署**。

---

## 1. 它做什么

在 Telegram 里把文件转发给你的私人 Bot，Bot 负责排队、下载/流式读取，并通过 rclone 写入 **OpenList 的 WebDAV**，最终落到你在 OpenList 中挂载的存储（NAS 本地卷或网盘）。

```
Telegram 私聊 Bot
      ↓  Telethon
SQLite 持久任务队列
      ↓  普通文件：先完整下载到本地；大文件：流式管道
rclone → OpenList WebDAV (/dav)
      ↓
你在 OpenList 挂载的存储（NAS 本地目录 / 网盘）
```

保留的核心能力（与原项目一致）：
- Telegram 私聊鉴权，只允许配置的数字 ID 使用；
- SQLite 持久队列、原子磁盘额度预留、去重、重启恢复；
- 普通落盘与流式直传共享上传并发窗口，并按 CPU/内存/磁盘/吞吐/错误率动态调节；
- 单文件超过本地预算自动切流式；WebDAV 临时文件 → 大小校验 → 安全改名 → 复验 → 本地清理；
- 完整 Bot 命令：/queue /status /performance /doctor /task /watch /pause /resume /retry /cancel /stream /orphans /help；
- python -m app.verify_destination 真实 WebDAV 写入/改名/删除验收。

---

## 2. 与上游项目的差异（剥离清单）

| 已剥离（VPS 部署专属，与"机器人+转存"无关） | 说明 |
|---|---|
| installer.py / installer_clouddrive2.py / installer_openlist.py | PySide6 图形部署器 |
| deployer_products.py / vps_resources.py | 产品标识、VPS 资源探测与建议 |
| payload_*/manage.sh / remote_install.sh | SSH 远程安装与运维脚本 |
| repair_clouddrive_network.sh / openlist_admin.sh / preserve_*.sh / backup_retention.sh | VPS 网络修复、管理员、备份脚本 |
| app/deployment_check.py | Compose/代码指纹核验（部署器专用） |
| app/backup_database.py | 部署期数据库备份（部署器专用） |
| packaging/ / build.ps1 / .github/ | Windows 打包与 CI |
| CloudDrive2 分支 | 本项目改用 OpenList 作为唯一存储网关 |

**原样保留**：app/ 下的 Bot 连接与转存核心（main.py、bot_commands.py、db.py、rclone_client.py、resources.py、config.py、states.py、naming.py、interfaces.py、healthcheck.py、verify_destination.py）。

---

## 3. 目录结构

```
tg2cloud-nas/
├── app/                       # 保留的 Bot 连接与转存核心（原样）
│   ├── main.py                # 服务入口：Telegram 客户端 + 调度循环
│   ├── bot_commands.py        # Bot 命令与消息处理
│   ├── db.py                  # SQLite 持久队列
│   ├── rclone_client.py       # rclone/WebDAV 上传与流式管道
│   ├── resources.py           # 自适应并发窗口 + 资源监控
│   ├── config.py              # 环境变量解析
│   ├── states.py / naming.py / interfaces.py
│   ├── healthcheck.py         # 容器健康检查
│   └── verify_destination.py  # WebDAV 真实验收
├── scripts/
│   └── gen-env.py             # 由明文配置生成 .env（自动 Base64 编码）
├── Dockerfile                 # Bot 镜像（非 root、含 rclone/tini）
├── docker-compose.yml         # 仅 Bot
├── docker-compose.openlist.yml# OpenList 单独部署
├── .env.example               # 环境变量模板（含 B64 字段）
├── config.plain.env.example   # 明文配置模板（配合 gen-env.py）
├── .dockerignore
├── .gitignore
└── LICENSE                    # 保留 MIT 许可证
```

---

## 4. 快速开始（NAS 局域网）

### 4.1 启动 OpenList（单独部署）

```bash
cp .env.example .env      # 至少填 OPENLIST_ADMIN_PASSWORD（首次初始化用）
docker compose -f docker-compose.openlist.yml up -d
```

浏览器打开 http://<NAS_IP>:5244 ，用管理员账号登录，然后：
1. 添加并授权目标存储（本地目录可用"本地存储"，或添加网盘）；
2. 开启 WebDAV（端点默认 http://<NAS_IP>:5244/dav ）；
3. 新建一个专用普通用户（如 tg2cloud），授予目录列表、读取、创建/写入、改名/移动、删除权限。

### 4.2 填写 Bot 配置

最省事的方式是用脚本生成 .env（自动完成 Base64 编码）：

```bash
cp config.plain.env.example config.plain.env
# 编辑 config.plain.env：填 Bot Token、API ID/Hash、你的数字 ID、WebDAV 地址/用户/密码
python scripts/gen-env.py config.plain.env > .env
```

也可直接 cp .env.example .env 手工填写带 _B64 后缀的字段（值需为 Base64）。

关键字段：
- BOT_TOKEN_B64、TELEGRAM_API_ID、TELEGRAM_API_HASH_B64、ALLOWED_USER_ID
- WEBDAV_URL_B64 = http://host.docker.internal:5244/dav （OpenList 与 Bot 同机）
  或 http://<OpenList_IP>:5244/dav （OpenList 在另一台机器）
- WEBDAV_USERNAME_B64、WEBDAV_PASSWORD_B64、WEBDAV_TARGET_PATH_B64（可选子目录）

### 4.3 启动 Bot

```bash
docker compose up -d --build
docker compose logs -f tg2cloud-bot
```

### 4.4 验收 WebDAV 链路

```bash
docker compose exec tg2cloud-bot python -m app.verify_destination
# 出现 TG2CLOUD_DESTINATION=OK 表示 Bot 到 OpenList WebDAV 的写入/改名/删除链路可用
```

之后在 Telegram 私聊你的 Bot，先发一个小文件（5–20MB）验证完整链路。

---

## 5. 前置条件与注意事项

1. **Telegram 可达性**：Bot 需能访问 api.telegram.org。NAS 若无直接公网（常见于国内），请为 Bot 配置代理/旁路由出口；这是整个方案能否跑通的前提。
2. **OpenList 与 Bot 解耦**：两者用独立 compose 文件、独立生命周期。更新/重启 OpenList 不影响 Bot 数据。
3. **完整性边界**（沿用上游说明）：远端只以大小校验为准，不提供内容哈希；流式模式不在本地保留完整副本，中断通常需从头重传。
4. **凭据安全**：Base64 只是编码，不是加密；.env、config/、data/、logs/、openlist/ 均已在 .gitignore 忽略，切勿提交或外泄。
5. **权限**：Bot 容器以 UID/GID 10001、只读根文件系统、no-new-privileges、丢弃 capabilities 运行；首次启动若挂载目录属主不符，可 chown -R 10001:10001 data downloads logs config。
6. **同 Token 冲突**：切勿让两个实例同时长期使用同一个 Telegram Bot Token。

---

## 6. 许可证与致谢

本项目基于 [TG2Cloud](https://github.com/LuoPoJunZi/TG2Cloud)（MIT License）精简改写，TG2Cloud 又源自 [whyhhh20/TG115](https://github.com/whyhhh20/TG115)。保留原作者版权与 MIT 许可证原文（见 LICENSE）。OpenList 为独立开源项目，遵循其自身许可证。本项目与 Telegram、OpenList、各云存储服务及其运营方无隶属或官方合作关系，请自行评估账号、数据与网络风险。
