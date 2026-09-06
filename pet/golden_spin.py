# -*- coding: utf-8 -*-
"""黄金回旋：程序化原地逆时针 360° 插值旋转。

控制器只维护角度状态与计时；绘制由 PetWindow/WindowFeatureGateMixin
经 pet/window_effects.py 应用。旋转不依赖素材，不与点击动画叠画面：
点击触发时由窗口在点击动画结束后调用 consume_click_finished()。
"""
from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer

from .window_effects import eased_progress

GOLDEN_SPIN_DURATION_MS = 700
GOLDEN_SPIN_END_ANGLE = -360.0  # Qt 正角=顺时针，负角=逆时针


class GoldenSpinController(QObject):
    """管理一次 360° 逆时针旋转。每个 PetWindow 持有同一实例。"""

    def __init__(self, win: Any, *, clock=None, parent=None) -> None:
        super().__init__(parent)
        self.win = win
        self._clock = clock if callable(clock) else time.monotonic
        self._active = False
        self._angle_deg = 0.0
        self._started_at = 0.0
        self._pending_after_click = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._on_timer)

    # ------------------------------------------------------------ 查询
    @property
    def active(self) -> bool:
        return self._active

    def current_angle_deg(self) -> float:
        return self._angle_deg

    @property
    def pending_after_click(self) -> bool:
        return self._pending_after_click

    # ------------------------------------------------------------ 启动/取消
    def start(self) -> None:
        """立即开始一段 360° 逆时针旋转；已运行/待触发时忽略重复启动。"""
        if self._active:
            return
        self._active = True
        self._started_at = self._clock()
        self._timer.start()
        self.win.update()

    def arm_after_click(self) -> None:
        """点击触发模式：等点击动画自然结束后再接续旋转。"""
        self._pending_after_click = True

    def consume_click_finished(self) -> None:
        """点击动画结束回调：有 pending 才真正启动一次。"""
        if not self._pending_after_click:
            return
        self._pending_after_click = False
        self.start()

    def cancel(self) -> None:
        """取消 pending；若正在旋转则立即归零并停表。"""
        self._pending_after_click = False
        if not self._active:
            return
        self._active = False
        self._timer.stop()
        self._angle_deg = 0.0
        self.win.update()

    def cancel_pending(self) -> None:
        """只清 pending，不打断正在进行的旋转（角色切换/隐藏时使用）。"""
        self._pending_after_click = False

    # ------------------------------------------------------------ 计时
    def _on_timer(self) -> None:
        self._update(self._clock())

    def _update(self, now: float) -> None:
        if not self._active:
            return
        elapsed_ms = max(0.0, (now - self._started_at) * 1000.0)
        progress = eased_progress(
            elapsed_ms,
            GOLDEN_SPIN_DURATION_MS,
        )
        done = progress >= 1.0
        if done:
            self._active = False
            self._timer.stop()
            self._angle_deg = 0.0
        else:
            self._angle_deg = GOLDEN_SPIN_END_ANGLE * progress
        self.win.update()
