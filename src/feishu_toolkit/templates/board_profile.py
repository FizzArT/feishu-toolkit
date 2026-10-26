"""看板档案（BoardProfile）：把 Issue 映射到**任意已有表**。

## 为什么需要它

标准看板模板（``requirements_bug_board``）字段名是固定的：
「需求名称」「状态」「优先级」。但真实项目里的表往往是别的团队建的，
字段名不一样、选项不一样、甚至一张表只有四个列。

档案把这些差异挪到**数据**里（JSON），代码不用改：

```json
{
  "tables": [
    {
      "name": "需求池",
      "key": "Issue编号",
      "fields": {
        "需求名称": {"to": "需求描述"},
        "状态": {"to": "需求状态", "values": {"待讨论": "待评估"}},
        "优先级": {"to": "优先级"}
      }
    }
  ]
}
```

## 字段映射的三种规则

一条规则 = 一个标准字段名 → 目标表里怎么写：

| 写法 | 含义 |
|---|---|
| ``{"to": "目标字段名"}`` | 直接改名写过去 |
| ``{"to": "X", "values": {"待讨论": "待评估"}}`` | 改名 **且** 换值（单选选项名不一致时用） |
| ``{"labels": {"产品缺陷": "产品缺陷"}}`` | **不来自标准字段**，而是拿 issue 的标签去匹配，取第一个命中的标签作为值 |

没在 ``fields`` 里列出的标准字段**不写**——防止把「需求描述」这类
标准字段硬塞进只认四个列的表。

## 方向是「标准名 → 目标名」

不是反过来。标准名来自 ``GitHubIssueMapper`` 的输出（中文，见
``adapters/github_issue.py``），目标名是目标表里的实际字段名。
``{"to": ...}`` 里的 ``to`` 明确标了方向，避免中文名对中文名时的歧义。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


@dataclass
class FieldRule:
    """一条字段映射规则。

    三种形态互斥：

    - ``{"to": "需求描述"}`` —— 改名写过去
    - ``{"to": "需求状态", "values": {...}}`` —— 改名且换值
    - ``{"labels": {"产品缺陷": "产品缺陷"}}`` —— 从 issue 标签取值

    ``create`` 是例外开关：默认**不往目标表里塞词表外的选项**，
    缺了就跳过并记 warning；显式写 ``"create": true`` 才允许自动建选项。
    """

    to: Optional[str] = None
    values: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    create: bool = False

    @property
    def is_label_rule(self) -> bool:
        """是否是从标签取值（而不是从标准字段改名）。"""
        return bool(self.labels)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "FieldRule":
        return cls(
            to=raw.get("to"),
            values=dict(raw.get("values") or {}),
            labels=dict(raw.get("labels") or {}),
            create=bool(raw.get("create") or False),
        )


@dataclass
class TableProfile:
    """一张目标表的档案。"""

    name: str
    key: str
    fields: Dict[str, FieldRule] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "TableProfile":
        key = raw.get("key")
        if not key:
            raise ValueError(f"表「{raw.get('name', '?')}」缺少 key（去重键字段名）")
        rules: Dict[str, FieldRule] = {}
        for source, spec in (raw.get("fields") or {}).items():
            rules[source] = FieldRule.from_dict(spec or {})
        return cls(name=str(raw.get("name", "")), key=str(key), fields=rules)

    def target_of(self, source: str) -> Optional[str]:
        """标准字段名 → 目标字段名。"""
        rule = self.fields.get(source)
        if rule is None or rule.is_label_rule:
            return None
        return rule.to or source


@dataclass
class BoardProfile:
    """整个看板的档案。"""

    tables: List[TableProfile] = field(default_factory=list)

    def table(self, name: str) -> Optional[TableProfile]:
        for table in self.tables:
            if table.name == name:
                return table
        return None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "BoardProfile":
        return cls(
            tables=[TableProfile.from_dict(t) for t in (raw.get("tables") or [])]
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "BoardProfile":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)
