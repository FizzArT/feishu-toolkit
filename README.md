# 飞书集成工具 · Feishu Toolkit

> 飞书开放平台（open.feishu.cn）的 **Python 工具包**，把飞书各项能力封装成可复用、可安装、可测试的 SDK。
>
> **首批能力：多维表格（Bitable）** —— 提供 Base / Table / Field / Record / View 的创建、编辑、写入，以及一套**标准化的「需求 + Bug 看板」模板**，可直接把 GitHub Issue 同步成飞书看板。
>
> **通知能力：消息 / 卡片推送** —— 支持应用身份与自定义群机器人两种方式，可把 GitHub Issue 事件以交互卡片即时推送到飞书群。

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
| 看板档案 | 把字段名 / 单选词表的差异写进 JSON，写入**任意已有表**（`describe` 先 dump 真实结构） |
| 消息 / 通知 | 应用身份（IM API）与自定义群机器人（webhook），文本 / 交互卡片 |
| GitHub 事件通知 | Issue 事件 → 交互卡片（按动作配色，含状态 / 优先级 / 跳转按钮） |

### 路线图

- 云文档（Docs）、电子表格（Sheets）
- 日历（Calendar）、任务（Task）、审批（Approval）
- 通讯录（Contact）、云空间（Drive）

---

## 安装

从 GitHub 安装（按 Tag 锁定版本）：

```bash
pip install git+https://github.com/FizzArT/feishu-toolkit.git@v0.1.1
```

或在 `requirements.txt` 中：

```text
feishu-toolkit @ git+https://github.com/FizzArT/feishu-toolkit.git@v0.1.1
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

### 3. 写入已有的自定义表（看板档案）

标准看板的字段名是固定的。如果要写进**别人建好的表**（字段名、选项都不一样），
用一份**看板档案**把差异挪到数据里，代码不用动。

**第一步：先看真实的表结构**（别照着记忆写档案）：

```bash
export FEISHU_APP_ID=cli_xxx FEISHU_APP_SECRET=xxx FEISHU_APP_TOKEN=bascnXXXX
feishu-toolkit describe                    # 全部表
feishu-toolkit describe --table 需求池     # 只看一张
```

输出里能看到每张表的 `field_name` / `type` / 单选的 `options`，照着写档案。

**第二步：写档案**（例如 `.github/feishu-board.json`）：

```json
{
  "tables": [
    {
      "name": "需求池",
      "key": "Issue编号",
      "fields": {
        "需求名称": {"to": "需求描述"},
        "状态": {"to": "需求状态", "values": {
          "待讨论": "待评估",
          "待启动": "待评估",
          "设计中": "方案设计中",
          "开发中": "开发交付中",
          "验收中": "验收中",
          "已完成": "已完成"
        }},
        "优先级": {"to": "优先级"},
        "负责人": {"to": "需求提出人"},
        "开始时间": {"to": "需求提出日期"},
        "需求分类": {"to": "需求分类", "labels": {
          "产品缺陷": "产品缺陷",
          "资源支持": "资源支持"
        }}
      }
    }
  ]
}
```

**第三步：同步**

```bash
feishu-toolkit github-sync issues.json --profile .github/feishu-board.json
```

档案的规则：

| 写法 | 含义 |
|---|---|
| `{"to": "目标字段名"}` | 标准字段改名写过去 |
| `{"to": "X", "values": {"标准值": "目标值"}}` | 改名 **且** 换值（两边词表不一致时用） |
| `{"labels": {"标签名": "选项值"}}` | 不来自标准字段，直接拿 issue 的**标签**去匹配取值 |

- 方向是 **标准字段名 → 目标字段名**（标准名见上面的「GitHub Issue 映射口径」）。
- 没在 `fields` 里列出的标准字段**不写**，不会把「需求描述」硬塞进只认四列的表。
- `key` 是去重键（幂等匹配），字段不存在会自动建一个数字字段。
- 写单选字段时：档案里 `values` 映射过的值直接写并自动建选项；目标表**已有**的选项原样写；
  其余情况**这一列不更新**并记一条 warning——不在别人的表里塞词表外的选项。

同步结果里有 `warnings`，CI 里可以直接看到「哪一列没写、为什么」。

### 4. 也可以直接操作底层资源

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

### 5. 推送通知到飞书群

**方式 A：自定义群机器人（最简单，无需应用权限）**

```python
from feishu_toolkit.notifier import WebhookNotifier

notifier = WebhookNotifier("https://open.feishu.cn/open-apis/bot/v2/hook/xxxx")
notifier.send_text("构建完成 ✅")
notifier.send_card(card)   # card 为交互卡片 dict
```

**方式 B：应用身份（需应用开通 IM 权限、加进群）**

```python
# 发文本 / 卡片到群（chat_id），也可发个人（open_id）
client.notifier.send_text("oc_xxx", "构建完成")
client.notifier.send_card("oc_xxx", card)
```

**GitHub Issue 事件 → 交互卡片**

```python
# 应用身份
gh = client.github_notifier()
gh.notify_event(event, receive_id="oc_xxx")   # event 为 GitHub issues webhook payload

# 群机器人
from feishu_toolkit.notifier import GitHubNotifier
GitHubNotifier(WebhookNotifier(webhook)).notify_event(event)
```

卡片按动作自动配色：新建=绿、完成=绿、不计划关闭=灰、重开=橙、打标签=青、指派=紫；正文含状态、优先级、标签、负责人和「查看 Issue」按钮。

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

## 统一标签规范（GitHub 各项目）

适配器靠 **labels（标签）** 识别类型 / 优先级 / 状态 / 终端。为让所有项目零配置即可同步，
约定每个仓库使用下面这套**统一标签**。标签名建议使用下列英文规范名（稳定、跨项目通用），
mapper 同时兼容中文别名。

### 1. 必选：类型（决定进哪张表）

| 标签 | 含义 | 映射去向 | 推荐颜色 |
|---|---|---|---|
| `bug` | 缺陷 / 故障 | **Bug 管理** | `D73A4A` 红 |
| `enhancement` | 功能增强 / 需求 | **需求管理** | `A2EEEF` 青 |
| `documentation` | 文档 | **需求管理**（文档） | `0075CA` 蓝 |

> 三个都没有时默认按「需求管理」处理；标题含「缺陷」字样也会识别为 Bug。

### 2. 必选：优先级

| 标签 | 含义 | 映射 | 推荐颜色 |
|---|---|---|---|
| `P0` | 紧急 / 最高 | P0 | `B60202` 深红 |
| `P1` | 中（**默认**） | P1 | `FBCA04` 黄 |
| `P2` | 低 | P2 | `0E8A16` 绿 |

> 兼容 `priority:high` / `high` / `urgent`、`priority:medium` / `medium`、`priority:low` / `low`。

### 3. 可选：状态（Issue 仍 open 时用于推断阶段）

| 标签 | 需求状态 | Bug 状态 | 推荐颜色 |
|---|---|---|---|
| `todo` | 待启动 | 未解决 | `F9D0C4` |
| `wip` | 开发中 | 修复中 | `CCCCCC` |
| `review` | 验收中 | 待验收 | `1D76DB` |

> 一旦 Issue 被关闭，状态自动置为「已完成 / 已关闭」，无需标签。

### 4. 可选：终端（Bug 用）

| 标签 | 终端 | 推荐颜色 |
|---|---|---|
| `web` | Web / 网页 | `C5DEF5` |
| `ios` | iOS（iPhone / iPad） | `C5DEF5` |
| `android` | Android / 安卓 | `3DD47E` |
| `windows` | Windows | `5319E7` |
| `mac` | Mac / macOS | `006B75` |

### 一键应用到某个仓库

把下面脚本中的 `OWNER/REPO` 改成目标仓库，运行即可批量创建上述标签（已存在的会更新为标准颜色）：

```bash
gh api 'repos/OWNER/REPO/labels' --method POST -f name='bug' -f color='D73A4A' -f description='缺陷：进 Bug 管理'
gh api 'repos/OWNER/REPO/labels' --method POST -f name='enhancement' -f color='A2EEEF' -f description='功能增强：进需求管理'
gh api 'repos/OWNER/REPO/labels' --method POST -f name='documentation' -f color='0075CA' -f description='文档：进需求管理'
gh api 'repos/OWNER/REPO/labels' --method POST -f name='P0' -f color='B60202' -f description='紧急 / 最高优先级'
gh api 'repos/OWNER/REPO/labels' --method POST -f name='P1' -f color='FBCA04' -f description='中优先级（默认）'
gh api 'repos/OWNER/REPO/labels' --method POST -f name='P2' -f color='0E8A16' -f description='低优先级'
```

> 标签名在 mapper 中大小写不敏感；中文别名（缺陷 / 紧急 / 高、中、低 等）已内置识别，
> 历史项目无需强制改名也能同步，只是建议逐步统一。

---

## 飞书侧前置准备

1. 在 [飞书开放平台](https://open.feishu.cn) 创建**企业自建应用**，获取 **App ID / App Secret**；
2. 开通**多维表格**相关权限（`bitable:app` 等读写 scope）；
3. 若要用**应用身份发消息**：
   - 开通 IM 权限（`im:message` 或 `im:message:send_as_bot`）；
   - 启用「**机器人**」能力并发布新版本；
   - 把应用加进目标群（应用需在群内且有发言权限）。
4. **发布应用版本**（草稿状态的应用无法调用）；
5. 权限说明：
   - **应用自己通过 API 创建的 Base，应用自动拥有全部权限**，无需额外授权；
   - 若要访问「他人手动创建的 Base」，需把应用加为该 Base 的协作者（高级权限表授予「可管理」）。

> 不想给应用开 IM 权限？可以直接用**自定义群机器人**：群设置 → 机器人 → 添加「自定义机器人」→ 复制 webhook，无需应用、无需发布。

> 安全：凭证请通过环境变量 / CI Secrets 注入，**不要硬编码进代码**。

---

## 用 GitHub Actions 自动同步 / 通知

有两个示例工作流，可单独使用，也可一起用：

| 示例 | 作用 | 触发 |
|---|---|---|
| [`examples/issue-sync.yml`](./examples/issue-sync.yml) | 全量同步 Issue 到多维表格看板 | Issue 事件 + 手动 |
| [`examples/issue-notify.yml`](./examples/issue-notify.yml) | 单次事件即时推送交互卡片到群 | Issue 事件 |

**同步看板**需要的 Secrets：

- `FEISHU_APP_ID`、`FEISHU_APP_SECRET`
- `FEISHU_APP_TOKEN`（目标看板的 app_token）
- 可选 `FEISHU_USER_MAP`（GitHub login → open_id）

**群通知**二选一：

- 群机器人：`FEISHU_WEBHOOK_URL`（最简单，无需权限）；
- 应用身份：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`。

把示例文件复制到目标仓库的 `.github/workflows/` 即可。

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
│   ├── api/               # 资源层：base/table/field/record/view/message
│   ├── templates/         # 标准看板模板 + 看板服务 + 看板档案
│   ├── adapters/          # GitHub Issue 适配器 + 同步服务（标准 / 按档案）
│   └── notifier/          # 卡片构建 + 通知器（应用 / webhook）
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
