# -*- coding: utf-8 -*-
"""汇报概率（过程汇报抽稀）契约测试。

背景（用户定稿）：「1 常开、2 加概率、其他全改成常开」——过程汇报
（``notify_activity``）是提醒量最大的一类，按概率抽稀；其余类保持常开。

抽样只作用于**出气泡的汇报路径**（``_on_agent_activity``），绝不作用于
``raw_record``：原始记录由 ``monitors.raw_record`` 直接连到 stuck /
behavior / exploration / dialogue 消费方（``pet/agent_link.py`` 的
``_stuck_detector.feed_record``、``_behavior_detector.feed_record``、
``_exploration_watchdog.feed_record``、``_remember_dialogue_record``），
与气泡路径是两条独立链路。
"""
from __future__ import annotations

import pytest

from pet import agent_link
from pet.config import _clean_agent_link_data, _default_agent_link_data


def test_default_report_probability_is_60():
    """默认 60%：多数过程汇报照常送达，明显抑制刷屏。"""
    assert _default_agent_link_data()["report_probability"] == 60


def test_always_on_family_defaults():
    """用户定稿：1 开始干活常开、2 过程汇报（常开+概率）、其他全改成常开。"""
    d = _default_agent_link_data()
    assert d["notify_state"] is True          # 1 开始干活
    assert d["notify_activity"] is True       # 2 过程汇报（配合 report_probability 抽稀）
    assert d["notify_done"] is True
    assert d["notify_approval"] if "notify_approval" in d else True
    assert d["notify_exec_failed"] is True
    assert d["stuck_detect"] is True          # 原来默认关 → 常开
    assert d["pattern_detect"] is True        # 原来默认关 → 常开


@pytest.mark.parametrize("raw,expected", [
    (0, 0),
    (60, 60),
    (100, 100),
    (-5, 0),          # 下越界收敛到 0
    (150, 100),       # 上越界收敛到 100
    ("80", 80),       # 字符串数字可接受
    (59.6, 59),       # 浮点截断
    (None, 60),       # 非法值回落默认
    ("abc", 60),
])
def test_clean_agent_link_data_clamps_report_probability(raw, expected):
    cleaned = _clean_agent_link_data({"report_probability": raw})
    assert cleaned["report_probability"] == expected


def test_clean_agent_link_data_keeps_default_when_absent():
    assert _clean_agent_link_data({})["report_probability"] == 60


@pytest.mark.parametrize("prob,roll,expected", [
    (0, 0.0, False),
    (0, 0.999, False),
    (100, 0.0, True),
    (100, 0.999, True),
    (60, 0.0, True),
    (60, 0.59, True),
    (60, 0.6, False),      # 边界取「小于」：0.6 不汇报
    (60, 0.99, False),
])
def test_should_report_activity_boundaries(prob, roll, expected):
    assert agent_link.should_report_activity(prob, roll) is expected


class TestActivitySampling:
    """过程汇报抽稀的端到端接线（注入 rng，避免真实随机导致测试不确定）。"""

    def _make(self, tmp_path, cfg=None, rolls=None):
        from PySide6.QtWidgets import QApplication

        from pet.agent_link import AgentLinkManager
        from pet.config import Config

        QApplication.instance() or QApplication([])
        bubbles: list[str] = []

        class DummyWin:
            cats = {"acts": ["写代码"], "idles": ["待机呼吸"]}
            _bubble_busy_until = 0.0

            def isVisible(self):
                return True

            def show_bubble(self, text, duration_ms=3000):
                bubbles.append(text)

            def _pick(self, lst):
                return lst[0]

            def request_link_anim(self, name):
                pass

            def request_link_idle(self):
                pass

        win = DummyWin()
        config = Config(base=tmp_path)
        data = config.data
        data["agent_link"] = {**data.get("agent_link", {}), **(cfg or {})}
        config.save()
        seq = list(rolls if rolls is not None else [0.0])
        clock = [1000.0]
        mgr = AgentLinkManager(
            win, config, min_interval=2.0, clock=lambda: clock[0],
            rng=lambda: seq.pop(0) if seq else 0.0,
        )
        return mgr, bubbles, clock

    def test_roll_above_probability_drops_bubble(self, tmp_path):
        mgr, bubbles, _ = self._make(
            tmp_path, {"notify_activity": True, "report_probability": 60}, [0.7]
        )
        mgr._on_agent_activity("dsh", "bash")
        assert bubbles == []

    def test_roll_below_probability_shows_bubble(self, tmp_path):
        mgr, bubbles, _ = self._make(
            tmp_path, {"notify_activity": True, "report_probability": 60}, [0.1]
        )
        mgr._on_agent_activity("dsh", "bash")
        assert len(bubbles) == 1

    def test_zero_probability_equals_off(self, tmp_path):
        """概率 0 = 过程汇报彻底静音（用户未暴露该开关时的等效关闭手段）。"""
        mgr, bubbles, _ = self._make(
            tmp_path, {"notify_activity": True, "report_probability": 0}, [0.0, 0.0]
        )
        mgr._on_agent_activity("dsh", "bash")
        mgr._on_agent_activity("dsh", "read")
        assert bubbles == []

    def test_hundred_probability_always_reports(self, tmp_path):
        mgr, bubbles, clock = self._make(
            tmp_path, {"notify_activity": True, "report_probability": 100}, [0.99, 0.99]
        )
        mgr._on_agent_activity("dsh", "bash")
        clock[0] += 15.0
        mgr._on_agent_activity("dsh", "read")
        assert len(bubbles) == 2

    def test_dropped_sample_does_not_consume_throttle(self, tmp_path):
        """抽稀丢弃不记账：否则概率与节流叠加会过度衰减（时钟不前进也应立刻能汇报）。"""
        mgr, bubbles, _ = self._make(
            tmp_path, {"notify_activity": True, "report_probability": 60}, [0.7, 0.1]
        )
        mgr._on_agent_activity("dsh", "bash")   # 抽稀丢弃
        assert bubbles == []
        mgr._on_agent_activity("dsh", "bash")   # 时钟未前进，仍应汇报
        assert len(bubbles) == 1

    def test_notify_activity_off_still_silences(self, tmp_path):
        """显式关闭过程汇报（config 手改）时，概率再高也不出声。"""
        mgr, bubbles, _ = self._make(
            tmp_path, {"notify_activity": False, "report_probability": 100}, [0.0]
        )
        mgr._on_agent_activity("dsh", "bash")
        assert bubbles == []
