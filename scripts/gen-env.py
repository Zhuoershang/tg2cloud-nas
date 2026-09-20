#!/usr/bin/env python3
"""TG2Cloud NAS 精简版 —— 由明文配置生成 .env。

用法：
    cp config.plain.env.example config.plain.env
    # 编辑 config.plain.env 填入明文
    python scripts/gen-env.py config.plain.env > .env

这样做的好处：无需手工对敏感字段做 Base64 编码，脚本会自动处理。
注意：Base64 只是编码，不是加密；.env 与 config.plain.env 都应按敏感文件保管，
     切勿提交到任何仓库。两者都已在 .gitignore 中忽略。
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

# 需要做 Base64 编码的字段：<明文字段名> -> <输出到 .env 的字段名>
B64_FIELDS = {
    "TELEGRAM_API_HASH": "TELEGRAM_API_HASH_B64",
    "BOT_TOKEN": "BOT_TOKEN_B64",
    "WEBDAV_URL": "WEBDAV_URL_B64",
    "WEBDAV_USERNAME": "WEBDAV_USERNAME_B64",
    "WEBDAV_PASSWORD": "WEBDAV_PASSWORD_B64",
    "WEBDAV_TARGET_PATH": "WEBDAV_TARGET_PATH_B64",
}

# 原样透传的字段（含默认值）
PLAIN_FIELDS = {
    "TELEGRAM_API_ID": "",
    "ALLOWED_USER_ID": "",
    "TG2CLOUD_STORAGE_BACKEND": "openlist",
    "TG2CLOUD_RCLONE_REMOTE_NAME": "openlist",
    "LOCAL_TEMP_BUDGET_GB": "20",
    "MIN_FREE_DISK_GB": "8",
    "TZ": "Asia/Shanghai",
    "OPENLIST_ADMIN_PASSWORD": "",
}


def parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "用法: python scripts/gen-env.py <明文配置文件>",
            file=sys.stderr,
        )
        return 2
    src = Path(sys.argv[1])
    if not src.exists():
        print(f"找不到明文配置文件：{src}", file=sys.stderr)
        return 2

    plain = parse_env_file(src)
    out: list[str] = [
        "# 由 scripts/gen-env.py 自动生成，请勿手工编辑；改动请修改明文配置后重跑脚本",
    ]

    required_plain = ("TELEGRAM_API_ID", "ALLOWED_USER_ID", "TELEGRAM_API_HASH", "BOT_TOKEN")
    missing = [k for k in required_plain if not plain.get(k)]
    if missing:
        print(f"缺少必填字段：{', '.join(missing)}", file=sys.stderr)
        return 1

    out.append("")
    out.append("# ---------- Telegram ----------")
    out.append(f"TELEGRAM_API_ID={plain['TELEGRAM_API_ID']}")
    out.append(f"TELEGRAM_API_HASH_B64={b64(plain['TELEGRAM_API_HASH'])}")
    out.append(f"BOT_TOKEN_B64={b64(plain['BOT_TOKEN'])}")
    out.append(f"ALLOWED_USER_ID={plain['ALLOWED_USER_ID']}")

    out.append("")
    out.append("# ---------- 存储网关 (OpenList) ----------")
    out.append("TG2CLOUD_STORAGE_BACKEND=openlist")
    out.append("TG2CLOUD_RCLONE_REMOTE_NAME=openlist")
    out.append(f"WEBDAV_URL_B64={b64(plain['WEBDAV_URL'])}")
    out.append(f"WEBDAV_USERNAME_B64={b64(plain['WEBDAV_USERNAME'])}")
    out.append(f"WEBDAV_PASSWORD_B64={b64(plain['WEBDAV_PASSWORD'])}")
    out.append(
        "WEBDAV_TARGET_PATH_B64="
        + (b64(plain["WEBDAV_TARGET_PATH"]) if plain.get("WEBDAV_TARGET_PATH") else "")
    )

    out.append("")
    out.append("# ---------- 容量与调度 ----------")
    for key, default in PLAIN_FIELDS.items():
        if key in ("TG2CLOUD_STORAGE_BACKEND", "TG2CLOUD_RCLONE_REMOTE_NAME"):
            continue
        out.append(f"{key}={plain.get(key, default)}")

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
