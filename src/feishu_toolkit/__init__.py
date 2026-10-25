"""飞书集成工具（Feishu Toolkit）。

飞书开放平台 Python SDK，首批提供多维表格（Bitable）与标准看板能力。

当前版本为仓库初始化阶段，模块将按计划逐步落地：
- client: 入口 FeishuClient
- auth: tenant_access_token 管理
- http: 请求 / 重试 / 分页
- api: 资源层（base / table / field / record / view）
- templates: 标准看板模板与同步服务
- adapters: GitHub Issue 适配器
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
