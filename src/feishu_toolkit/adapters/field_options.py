"""写入前补齐单选字段缺失的选项。

批量 batch_create 对「自动新建单选选项」处理不稳定（偶发 1254060），
所以先读字段定义，把将要写入、但尚不存在的选项用字段更新接口建好。
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..api.fields import FieldType


def ensure_select_options(
    client: Any,
    app_token: str,
    table_id: str,
    field_maps: List[Dict[str, Any]],
) -> None:
    """确保 field_maps 里用到的单选选项在目标表中存在。

    Args:
        client: FeishuClient（或其 http 命名空间的等价物）。
        app_token: Base 的 app_token。
        table_id: 目标表 id。
        field_maps: 待写入的字段字典列表（值为最终写入值，不含改名）。
    """
    if not field_maps:
        return

    fields = {f["field_name"]: f for f in client.fields.list(app_token, table_id)}
    needed: Dict[str, set] = {}
    for fmap in field_maps:
        for key, val in fmap.items():
            fdef = fields.get(key)
            if (
                fdef
                and fdef.get("type") == FieldType.SINGLE_SELECT
                and isinstance(val, str)
            ):
                needed.setdefault(key, set()).add(val)

    for name, values in needed.items():
        fdef = fields[name]
        prop = fdef.get("property") or {}
        options = list(prop.get("options", []))
        existing = {o["name"] for o in options}
        added = False
        for val in values:
            if val not in existing:
                options.append({"name": val})
                added = True
        if added:
            client.fields.update(
                app_token,
                table_id,
                fdef["field_id"],
                {
                    "field_name": name,
                    "type": fdef["type"],
                    "property": {"options": options},
                },
            )
