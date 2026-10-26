"""feishu-toolkit 命令行入口（供 CI / GitHub Actions 调用）。

环境变量：
    FEISHU_APP_ID / FEISHU_APP_SECRET     必填，自建应用凭证
    FEISHU_APP_TOKEN                       必填，目标多维表格 app_token
    FEISHU_USER_MAP                        可选，JSON：{"github_login": "本应用 open_id"}
                                           未配置的人员字段会自动跳过

输入：
    GitHub Issue 对象的 JSON（单条对象或数组），从文件或 stdin 读取。
    注意：open_id 必须是「当前这个自建应用」视角下的 open_id，跨应用不可用。

子命令：
    describe      dump Base 的表 / 字段 / 单选选项结构（配档案前先看真实 schema）
    github-sync   把 Issue 同步到看板（--profile 指定自定义表时按档案写）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

from . import FeishuClient
from .adapters import IssueMapperConfig, ProfileIssueSync
from .templates import BoardProfile


def _load_issues(path: str) -> List[Dict[str, Any]]:
    if path == "-":
        data = json.load(sys.stdin)
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    if isinstance(data, dict):
        return [data]
    return data


def _config_from_env() -> IssueMapperConfig:
    user_map_raw = os.environ.get("FEISHU_USER_MAP", "{}")
    user_map = {str(k).lower(): str(v) for k, v in json.loads(user_map_raw).items()} if user_map_raw else {}
    # 有的仓库不靠标签，把类型和优先级写进标题前缀（[Bug][P1] ...）。
    # 默认关，免得把「[WIP] 修一下」这种标题误判。
    prefix = os.environ.get("FEISHU_TITLE_PREFIX", "").strip().lower()
    return IssueMapperConfig(
        user_map=user_map,
        parse_title_prefix=prefix in ("1", "true", "yes", "on"),
    )


def _client_from_env() -> FeishuClient:
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not (app_id and app_secret):
        print(
            "ERROR: 需要 FEISHU_APP_ID / FEISHU_APP_SECRET",
            file=sys.stderr,
        )
        return None  # type: ignore[return-value]
    return FeishuClient(app_id, app_secret)


def cmd_describe(args: argparse.Namespace) -> int:
    """dump Base 的表结构。"""
    app_token = os.environ.get("FEISHU_APP_TOKEN")
    if not app_token:
        print("ERROR: 需要 FEISHU_APP_TOKEN", file=sys.stderr)
        return 2
    client = _client_from_env()
    if client is None:
        return 2

    tables = client.tables.list(app_token)
    if args.table:
        tables = [t for t in tables if t.get("name") == args.table]
        if not tables:
            print(f"ERROR: 没有名为「{args.table}」的表", file=sys.stderr)
            return 2

    out = []
    for table in tables:
        fields = client.fields.list(app_token, table["table_id"])
        out.append(
            {
                "table_id": table["table_id"],
                "name": table.get("name"),
                "fields": [
                    {
                        "field_name": f.get("field_name"),
                        "type": f.get("type"),
                        "options": [
                            o.get("name")
                            for o in ((f.get("property") or {}).get("options") or [])
                        ],
                    }
                    for f in fields
                ],
            }
        )
    print(json.dumps({"app_token": app_token, "tables": out}, ensure_ascii=False, indent=2))
    return 0


def cmd_github_sync(args: argparse.Namespace) -> int:
    app_token = os.environ.get("FEISHU_APP_TOKEN")
    if not app_token:
        print("ERROR: 需要 FEISHU_APP_TOKEN", file=sys.stderr)
        return 2
    client = _client_from_env()
    if client is None:
        return 2

    issues = _load_issues(args.issues_file)

    if args.profile:
        profile = BoardProfile.from_json_file(args.profile)
        sync = ProfileIssueSync(
            client, app_token, profile, config=_config_from_env()
        )
    else:
        board = client.issue_board.ensure(
            args.board_name or "需求管理看板", app_token=app_token
        )
        sync = client.github_issue_sync(board, config=_config_from_env())

    result = sync.sync_issues(issues)

    for warning in result.warnings:
        print(f"WARN: {warning}", file=sys.stderr)

    print(json.dumps({
        "received": len(issues),
        "created": result.created,
        "updated": result.updated,
        "warnings": len(result.warnings),
        "app_token": app_token,
        "url": f"https://feishu.cn/base/{app_token}",
    }, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="feishu-toolkit", description="飞书集成工具命令行")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("github-sync", help="把 GitHub Issue 同步到需求/Bug 看板")
    p_sync.add_argument("issues_file", help="Issue JSON 文件（单条对象或数组），- 表示 stdin")
    p_sync.add_argument("--board-name", default=None, help="看板名（仅在未提供 app_token 新建时用）")
    p_sync.add_argument(
        "--profile",
        default=None,
        help="看板档案 JSON；给了就按档案写指定的表和字段，不再用标准看板",
    )
    p_sync.set_defaults(func=cmd_github_sync)

    p_desc = sub.add_parser("describe", help="dump Base 的表 / 字段 / 选项结构")
    p_desc.add_argument("--table", default=None, help="只看这张表")
    p_desc.set_defaults(func=cmd_describe)
    return parser


def main(argv: Any = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
