# 飞书集成工具 · Feishu Toolkit

> 飞书开放平台（open.feishu.cn）的 **Python 工具包**，把飞书各项能力封装成可复用、可安装、可测试的 SDK。
>
> **首批能力：多维表格（Bitable）** —— 提供 Base / Table / Field / Record / View 的创建、编辑、写入，以及一套**标准化的「需求 + Bug 看板」模板**，可直接把 GitHub Issue 同步成飞书看板。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

---

## 为什么做这个

把散落在各个项目里的「飞书调用脚本」沉淀成**一套 SDK + 一套标准规范**：

- **复用**：一次封装，所有项目 `pip install` 即可；接口变更只改一处。
- **标准化**：所有项目的看板字段、选项、配色、视图完全一致，零学习成本。
- **可演进**：SDK 独立版本管理，带单元测试与回归；后续可平滑扩展消息、日历、云文档、审批等更多飞书 API。

它是一个**被调用的库**，不是常驻服务。典型运行环境是 GitHub Actions、本地脚本或你自己的后端。

---

## 能力范围

### v0.1（多维表格）

| 模块 | 能力 |
|---|---|
| 认证 | `tenant_access_token` 获取、缓存与自动刷新 |
| 资源层 | Base / Table / Field / Record / View 的增删改查 |
| 记录 | 单条与批量创建、更新、删除、搜索、分页 |
| 标准看板模板 | 固定字段、单选项、数字配色、视图（表格 / 看板 / 甘特 / 表单） |
| GitHub 适配器 | GitHub Issue → 标准字段（分类 / 状态 / 优先级 / 版本 / 终端 / 人员） |
| 同步服务 | 幂等 `upsert`（按 Issue 编号），批量按表分组 |

### 路线图

- 应用消息 / 自定义机器人推送（含群通知）
- 云文档（Docs）、电子表格（Sheets）
- 日历（Calendar）、任务（Task）、审批（Approval）
- 通讯录（Contact）、云空间（Drive）

---

## 安装

从 GitHub 安装（按 Tag 锁定版本）：

```bash
pip install git+https://github.com/FizzArT/feishu-toolkit.git@v0.1.0
```

或在 `requirements.txt` 中：

```text
feishu-toolkit @ git+https://github.com/FizzArT/feishu-toolkit.git@v0.1.0
```

---

## 快速上手

### 1. 创建一张标准看板

```python
from feishu_toolkit import FeishuClient

client = FeishuClient(app_id="cli_xxx", app_secret="xxx")

# 新建一张标准看板（需求管理 + Bug 管理 + 全部视图）
board = client.issue_board.create("我的项目看板")

print(board.app_token)
print(board.table_ids)   # {"需求管理": "tbl...", "Bug 管理": "tbl..."}
```

### 2. 把 GitHub Issue 同步到看板

```python
from feishu_toolkit.adapters import IssueMapperConfig

# 复用已存在的看板（传入 app_token 即可，按表名自动匹配）
board = client.issue_board.ensure("我的项目看板", app_token="bascnXXXX")

# 配置 GitHub 登录名 → 飞书 open_id（用于负责人 / 提交人 / 指派人）
config = IssueMapperConfig(user_map={
    "alice": "ou_xxxxxxxx",
    "bob":   "ou_yyyyyyyy",
})

sync = client.github_issue_sync(board, config=config)
result = sync.sync_issues(issues)   # issues 为 GitHub REST API 返回的 Issue 列表

print(result.created, result.updated)
```

`同步是幂等的`：以「Issue编号」为关联键，看板中没有则新建、已有则更新，重复运行不会产生重复记录。

### 3. 也可以直接操作底层资源

```python
# 新建一个空 Base
app = client.bases.create("自定义 Base")
app_token = app["app_token"]

# 新建表
table = client.tables.create(app_token, {
    "name": "任务表",
    "fields": [
        {"field_name": "任务名", "type": 1},
        {"field_name": "状态", "type": 3, "property": {"options": [
            {"name": "待办", "color": 0},
            {"name": "完成", "color": 15},
        ]}},
    ],
})

# 写入记录
client.records.create(app_token, table["table_id"], {
    "任务名": "写文档",
    "状态": "待办",
})
```

---

## 标准看板规范

所有项目的看板统一为以下结构（SSOT，定义在 `feishu_toolkit/templates/requirements_bug_board.py`）。

### 需求管理表

| 字段 | 类型 | 说明 |
|---|---|---|
| 需求名称 | 文本（主字段） | Issue 标题 |
| Issue编号 | 数字 | **幂等匹配键** |
| 需求描述 | 文本 | Issue body + GitHub 链接 |
| AI 总结 | 文本 | 预留，供 AI 摘要写入 |
| 迭代版本 | 单选 | v1.1 / V1.2 / 待排期 |
| 负责人 | 人员 | assignee（需 open_id 映射） |
| 状态 | 单选 | 待讨论 / 待启动 / 设计中 / 开发中 / 验收中 / 已完成 |
| 附件 | 附件 | 文件 |
| 优先级 | 单选 | P0 / P1 / P2 |
| 开始时间 | 日期 | Issue created_at |
| 结束时间 | 日期 | Issue closed_at |

**视图**：需求池（表格）、任务看板（看板）、迭代甘特图（甘特）。

### Bug 管理表

| 字段 | 类型 | 说明 |
|---|---|---|
| Bug 描述 | 文本（主字段） | Issue 标题 |
| Issue编号 | 数字 | **幂等匹配键** |
| 修复版本 | 单选 | V1.1 / V1.2 / 待排期 |
| 终端 | 单选 | Web / iOS / Android / Windows / Mac |
| 状态 | 单选 | 未解决 / 修复中 / 待验收 / 已关闭 |
| 优先级 | 单选 | P0 / P1 / P2 |
| 提交人 | 人员 | Issue author |
| 指派人 | 人员 | assignee |
| 创建时间 | 创建时间 | 自动记录 |
| 截图或视频 | 附件 | 复现材料 |

**视图**：Bug 列表（表格）、提交 Bug 表单（表单）。

### GitHub Issue 映射口径（默认，可配置）

- **分类**：标签含 `bug / 缺陷 / 错误 / 故障 / issue` → Bug 管理，否则需求管理。
- **需求状态**：
  - `closed` → 已完成；
  - open 时按标签：`设计`→设计中，`开发/进行中/wip`→开发中，`验收/review/测试/qa`→验收中，`待启动/todo`→待启动，默认 `待讨论`。
- **Bug 状态**：
  - `closed` → 已关闭；
  - open 时按标签：`修复/wip`→修复中，`待验收/review`→待验收，默认 `未解决`。
- **优先级**：`P0/high/urgent/紧急`→P0，`P1/medium/中`→P1，`P2/low/低`→P2，默认 `P1`。
- **版本**：优先取 milestone 标题，否则取标签中 `v` 开头且含数字的。
- **终端**：标签含 `web/ios/android/windows/mac` 关键词。
- **人员**：GitHub login（小写）→ 飞书 open_id，需通过 `user_map` 显式配置；未配置则跳过。

---

## 飞书侧前置准备

1. 在 [飞书开放平台](https://open.feishu.cn) 创建**企业自建应用**，获取 **App ID / App Secret**；
2. 开通**多维表格**相关权限（`bitable:app` 等读写 scope）；
3. **发布应用版本**（草稿状态的应用无法调用）；
4. 权限说明：
   - **应用自己通过 API 创建的 Base，应用自动拥有全部权限**，无需额外授权；
   - 若要访问「他人手动创建的 Base」，需把应用加为该 Base 的协作者（高级权限表授予「可管理」）。

> 安全：凭证请通过环境变量 / CI Secrets 注入，**不要硬编码进代码**。

---

## 用 GitHub Actions 自动同步

在你的目标仓库中通过 webhook 触发同步（Issue 新建 / 重开 / 关闭 / 打标签）。

1. 在目标仓库 **Settings → Secrets and variables → Actions** 添加：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `FEISHU_APP_TOKEN`（目标看板的 app_token）
2. 参考本仓库的示例工作流：[`examples/issue-sync.yml`](./examples/issue-sync.yml)，复制到目标仓库的 `.github/workflows/issue-sync.yml`。

---

## 项目结构

```text
feishu-toolkit/
├── pyproject.toml
├── README.md
├── src/feishu_toolkit/
│   ├── client.py          # 入口 FeishuClient
│   ├── auth.py            # tenant_access_token 管理
│   ├── http.py            # 请求 / 重试 / 分页
│   ├── errors.py          # 统一异常
│   ├── cell_value.py      # 单元格值构造
│   ├── api/               # 资源层：base/table/field/record/view
│   ├── templates/         # 标准看板模板 + 看板服务
│   └── adapters/          # GitHub Issue 适配器 + 同步服务
└── tests/                 # 单元测试
```

---

## 本地开发

```bash
git clone https://github.com/FizzArT/feishu-toolkit.git
cd feishu-toolkit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

---

## 版本说明

遵循 [语义化版本](https://semver.org/lang/zh-CN/)。**标准字段 / 选项 / 视图的变更属于破坏性变更**，会升级版本并在 Release 中说明。

---

## License

基于 [MIT License](./LICENSE) 开源。
