# NAS 精简版 TG2Cloud Bot —— 仅保留机器人连接与文件转存核心
FROM python:3.12-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# rclone 负责实际的 WebDAV 上传；tini 负责正确的信号/僵尸进程处理
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates rclone tini \
    && groupadd --system --gid 10001 tg2cloud \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent \
        --shell /usr/sbin/nologin tg2cloud \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

USER 10001:10001

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "app.main"]
