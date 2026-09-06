# -*- coding: utf-8 -*-
"""黄金回旋控制器测试：程序化 360° 插值旋转与“点击后接续”语义。"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from pet.golden_spin import GOLDEN_SPIN_DURATION_MS, GoldenSpinController


def _qapp():
    return QApplication.instance() or QApplication([])


class FakeWin:
    def __init__(self):
        self.updates = 0

    def update(self):
        self.updates += 1


def _clock_controller():
    times = [0.0]

    def clock():
        return times[0]

    return GoldenSpinController(FakeWin(), clock=clock), times


def test_spin_runs_ccw_and_finishes_at_zero():
    _qapp()
    controller, times = _clock_controller()
    controller.start()
    assert controller.active
    times[0] = GOLDEN_SPIN_DURATION_MS / 1000.0 / 2.0
    controller._update(times[0])
    assert controller.current_angle_deg() < 0
    assert controller.current_angle_deg() > -360.0
    times[0] = GOLDEN_SPIN_DURATION_MS / 1000.0
    controller._update(times[0])
    assert not controller.active
    assert controller.current_angle_deg() == 0.0
    controller.cancel()


def test_start_is_idempotent_while_running():
    _qapp()
    controller, times = _clock_controller()
    controller.start()
    controller.start()
    assert controller.active
    controller.cancel()
    assert not controller.active


def test_click_pending_is_consumed_once_after_click_animation_finishes():
    _qapp()
    controller, times = _clock_controller()
    controller.arm_after_click()
    assert controller.pending_after_click
    controller.consume_click_finished()
    assert not controller.pending_after_click
    assert controller.active
    times[0] = GOLDEN_SPIN_DURATION_MS / 1000.0
    controller._update(times[0])
    assert not controller.active
    # 第二次 consume 没有 pending，不再触发新的旋转。
    controller.consume_click_finished()
    assert not controller.active
    controller.cancel()


def test_cancel_clears_pending_and_stops_active_spin():
    _qapp()
    controller, times = _clock_controller()
    controller.arm_after_click()
    controller.start()
    assert controller.active
    controller.cancel()
    assert not controller.active
    assert not controller.pending_after_click
    assert controller.current_angle_deg() == 0.0
