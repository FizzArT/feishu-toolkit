

class TestTitlePrefix:
    """标题前缀解析：``[Bug][P1] xxx`` 这种约定。"""

    @staticmethod
    def _issue(number, title, labels=None, state="open"):
        return {
            "number": number,
            "title": title,
            "state": state,
            "labels": [{"name": n} for n in (labels or [])],
        }

    def test_prefixes_only_from_start(self):
        from feishu_toolkit.adapters.github_issue import GitHubIssueMapper

        assert GitHubIssueMapper.title_prefixes({"title": "[Bug][P1] 标题"}) == ["Bug", "P1"]
        assert GitHubIssueMapper.title_prefixes({"title": "[WIP] 修掉 [Bug] 标记"}) == ["WIP"]
        assert GitHubIssueMapper.title_prefixes({"title": "没有前缀"}) == []
        assert GitHubIssueMapper.title_prefixes({"title": "[未闭合"}) == []

    def test_priority_from_prefix_when_enabled(self):
        from feishu_toolkit.adapters.github_issue import GitHubIssueMapper, IssueMapperConfig

        m = GitHubIssueMapper(IssueMapperConfig(parse_title_prefix=True))
        fields = m.map(self._issue(1, "[Chore][P3] 清理"))["fields"]
        assert fields["优先级"] == "P3"
        assert fields["类型"] == "Chore"

    def test_prefix_ignored_when_disabled(self):
        from feishu_toolkit.adapters.github_issue import GitHubIssueMapper, IssueMapperConfig

        m = GitHubIssueMapper(IssueMapperConfig(parse_title_prefix=False))
        fields = m.map(self._issue(1, "[Chore][P3] 清理"))["fields"]
        assert fields["优先级"] == "P1"      # 默认值
        assert "类型" not in fields

    def test_title_beats_label(self):
        """标题写 [Chore]、标签是 enhancement 时，类型应该是 Chore。"""
        from feishu_toolkit.adapters.github_issue import GitHubIssueMapper, IssueMapperConfig

        m = GitHubIssueMapper(IssueMapperConfig(parse_title_prefix=True))
        fields = m.map(self._issue(1, "[Chore] 部署切换", labels=["enhancement"]))["fields"]
        assert fields["类型"] == "Chore"

    def test_prefix_decides_bug_table(self):
        """没有 bug 标签时，[Bug] 前缀也应该路由到 Bug 表。"""
        from feishu_toolkit.adapters.github_issue import GitHubIssueMapper, IssueMapperConfig

        m = GitHubIssueMapper(IssueMapperConfig(parse_title_prefix=True))
        assert m.map(self._issue(1, "[Bug][P0] 崩了"))["table"] == "Bug 管理"


class TestStateCase:
    """state 大小写：REST 返回小写，gh CLI 返回大写。"""

    @staticmethod
    def _issue(state):
        return {"number": 1, "title": "x", "state": state, "labels": []}

    def test_uppercase_closed_is_closed(self):
        from feishu_toolkit.adapters.github_issue import GitHubIssueMapper

        m = GitHubIssueMapper()
        assert m.map(self._issue("CLOSED"))["fields"]["状态"] == "已完成"

    def test_lowercase_closed_is_closed(self):
        from feishu_toolkit.adapters.github_issue import GitHubIssueMapper

        m = GitHubIssueMapper()
        assert m.map(self._issue("closed"))["fields"]["状态"] == "已完成"

    def test_open_stays_open(self):
        from feishu_toolkit.adapters.github_issue import GitHubIssueMapper

        m = GitHubIssueMapper()
        assert m.map(self._issue("OPEN"))["fields"]["状态"] == "待讨论"
