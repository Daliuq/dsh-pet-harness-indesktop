# -*- coding: utf-8 -*-
"""共享的绘制/命中变换小工具（黄金回旋 + 边缘探头共用）。

旋转在绘制层完成，不改动 _rebuild_frame / 帧缓存 / 解码链。paintEvent 与
_sync_mask 使用同一 begin/end 旋转路径，保证非 Windows mask 与画面一致；
_is_transparent_at 使用 unrotate_point 做逆变换，保证 Windows 逐像素命中一致。
"""
from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRect


def begin_rotation(painter, rect: QRect, angle_deg: float) -> None:
    """围绕 rect 中心旋转；调用方在绘制后必须配对 end_rotation。"""
    if abs(float(angle_deg)) < 1e-6:
        return
    center = QPointF(rect.center())
    painter.save()
    painter.translate(center)
    painter.rotate(float(angle_deg))
    painter.translate(-center)


def end_rotation(painter, angle_deg: float) -> None:
    """与 begin_rotation 配对；无旋转时为 no-op。"""
    if abs(float(angle_deg)) < 1e-6:
        return
    painter.restore()


def unrotate_point(point: QPointF, rect: QRect, angle_deg: float) -> QPointF:
    """把窗口内某逻辑点逆旋转回未旋转坐标系。

    用于 _is_transparent_at：先逆变换再查 alpha，保证旋转后的可见像素
    与命中测试一致。angle=0 时原样返回。
    """
    angle = float(angle_deg)
    if abs(angle) < 1e-6:
        return QPointF(point)
    center = QPointF(rect.center())
    rad = math.radians(-angle)
    dx = point.x() - center.x()
    dy = point.y() - center.y()
    return QPointF(
        center.x() + dx * math.cos(rad) - dy * math.sin(rad),
        center.y() + dx * math.sin(rad) + dy * math.cos(rad),
    )


def eased_progress(
    elapsed_ms: float,
    duration_ms: float,
    curve: QEasingCurve = QEasingCurve.Type.OutCubic,
) -> float:
    """把已流逝毫秒映射到 [0,1] 的缓动进度；duration<=0 视为完成。"""
    if duration_ms <= 0:
        return 1.0
    raw = max(0.0, min(1.0, float(elapsed_ms) / float(duration_ms)))
    easing = QEasingCurve(curve)
    return float(easing.valueForProgress(raw))
