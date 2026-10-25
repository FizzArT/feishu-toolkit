# 飞书集成工具 · Feishu Toolkit

> 飞书开放平台（open.feishu.cn）的 **Python 工具包**，目标是把飞书各项能力封装成可复用、可安装、可测试的 SDK。
>
> **首批能力：多维表格（Bitable）** —— 提供 Base / Table / Field / Record / View 的创建、编辑、写入，以及一套**标准化的「需求/开发看板」模板**，可直接把 GitHub Issue 同步成飞书看板。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

---

## 为什么做这个

把散落在各个项目里的「飞书调用脚本」沉淀成**一套内部 SDK + 一套标准规范**：

- **复用**：一次封装，所有项目 `pip install` 即可；接口变更只改一处。
- **标准化**：所有项目的看板字段、选项、视图、样式完全一致，零学习成本。
- **可演进**：SDK 独立版本管理，带单元测试与回归；后续可平滑扩展消息、日历、审批、云文档等更多飞书 API。

它是一个**被调用的库**，不是常驻服务。典型运行环境是 GitHub Actions、本地脚本或你自己的后端。

---

## 能力范围

### 已规划（v0.1 多维表格）

| 模块 | 能力 |
|---|---|
| 认证 | `tenant_access_token` 获取、缓存与自动刷新 |
| 资源层 | Base / Table / Field / Record / View 的增删改查 |
| 标准看板模板 | 固定字段、单选项、视图（表格 / 看板 / 甘特 / 仪表盘） |
| GitHub 适配器 | GitHub Issue → 标准字段（状态 / 类型 / 优先级 / 阶段映射） |
| 同步服务 | 幂等 `upsert`（按 Issue 编号）与全量 `reconcile` |

### 后续扩展（路线图）

- 自定义机器人 / 应用消息推送（含群通知）
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

## 快速上手（目标 API，随版本逐步落地）

```python
from feishu_toolkit import FeishuClient

client = FeishuClient(app_id="cli_xxx", app_secret="xxx")

# 幂等创建/复用一张标准看板
board = client.issue_board.ensure(base_name="my-project")

# 单条 upsert（按 Issue 编号匹配，有则更新、无则新建）
board.upsert_issue(issue)

# 全量对账：增、改，（可选）关闭
board.sync(issue_list)
```

---

## 标准看板规范

所有项目的看板统一为以下结构（SSOT，定义在 `feishu_toolkit/templates/`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| 标题 | 文本（主字段） | Issue 标题 |
| Issue编号 | 数字 | **幂等匹配键** |
| 状态 | 单选 | 待规划 / 待开始 / 进行中 / 待验证 / 已完成 |
| 类型 | 单选 | 功能增强 / 缺陷 / 文档 |
| 优先级 | 单选 | 高 / 中 / 低 |
| 阶段 | 单选 | 阶段0…阶段N / TASK |
| 描述 | 多行文本 | Issue body |
| 负责人 | 人员 | assignee（需 open_id 映射） |
| 标签 | 多选 | GitHub labels |
| 创建时间 | 日期 | created_at |
| 更新时间 | 日期 | updated_at |
| 完成时间 | 日期 | closed_at |
| GitHub链接 | 超链接 | html_url |

**标准视图**：表格视图、看板视图（按状态分组）、甘特视图（创建→完成）、仪表盘。

**GitHub Issue 字段映射（默认口径，可配置）**：

- 状态：`open → 进行中`，`closed → 已完成`
- 类型：`bug → 缺陷`，`enhancement → 功能增强`，`documentation → 文档`
- 优先级：`bug → 高`，`enhancement → 中`，`documentation → 低`
- 阶段：标题 `[阶段N]` 解析，否则 `TASK`

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
│   ├── api/               # 资源层：base/table/field/record/view
│   ├── templates/         # 标准看板模板 + 同步服务
│   └── adapters/          # GitHub Issue 适配器
└── tests/
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

遵循 [语义化版本](https://semver.org/lang/zh-CN/)。**标准字段 / 视图的变更属于破坏性变更**，会升级 minor 版本并在 Release 中说明。

---

## License

基于 [MIT License](./LICENSE) 开源。
