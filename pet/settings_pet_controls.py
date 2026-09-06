"""Pet-page control builders for the modern settings dialog (host-based).

ModernSettingsDialog retains a thin delegation method of the same name, so
existing callers and test patches keep working unchanged.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import autostart as autostart_mod
from . import catalog
from .agent_link import AgentLinkManager
from .config import (
    DEFAULT_CONTEXT_MENU_APPEARANCE,
    DEFAULT_MENU_EASTER_EGG,
    DEFAULT_SELF_TALK_BUBBLE_STYLE,
    DEFAULT_SELF_TALK_DURATION_SECONDS,
    DEFAULT_SELF_TALK_MAX_INTERVAL,
    DEFAULT_SELF_TALK_MIN_INTERVAL,
    DEFAULT_SELF_TALK_TEXTS,
    _float_or_default,
)
from .context_menus.icons import vector_widget_icon
from .fun_image_popup import oijingjing_image_path, resolve_fun_asset
from .persona_phrases import phrase_keys
from .settings_widgets import (
    AUDIO_NAME_FILTER,
    BrowserDoubleSpinBox,
    BrowserSpinBox,
    ClickSoundPackPicker,
    ColorPicker,
    ModernSelect,
    ResourcePathPicker,
    ResponsiveToggleActionRow,
    ToggleSwitch,
    _line_edit,
)
from .speech_bubble import BUBBLE_STYLE_PRESETS

def build_pet_controls(host) -> None:
    from .modern_settings_dialog import dialogue_params_hint
    host.scale_combo = ModernSelect(host, width=132)
    current_scale = float(host.config.get("scale", catalog.DEFAULT_SCALE))
    scales = list(catalog.SCALE_STEPS)
    if not any(abs(current_scale - value) < 0.001 for value in scales):
        scales.append(current_scale)
        scales.sort()
    for scale in scales:
        host.scale_combo.addItem(f"{int(round(catalog.CANVAS_W * scale))} px", scale)
    host.scale_combo.setCurrentIndex(host.scale_combo.findData(current_scale))

    # 生小肥鱼尺寸策略：默认继承主肥鱼大小；关闭后使用 spawn_scale 独立选择。
    host.spawn_inherit_size_check = ToggleSwitch(host)
    host.spawn_inherit_size_check.setChecked(bool(host.config.get("spawn_inherit_size", True)))
    host.spawn_scale_combo = ModernSelect(host, width=132)
    current_spawn_scale = float(host.config.get("spawn_scale", catalog.DEFAULT_SCALE))
    spawn_scales = list(catalog.SCALE_STEPS)
    if not any(abs(current_spawn_scale - value) < 0.001 for value in spawn_scales):
        spawn_scales.append(current_spawn_scale)
        spawn_scales.sort()
    for scale in spawn_scales:
        host.spawn_scale_combo.addItem(f"{int(round(catalog.CANVAS_W * scale))} px", scale)
    host.spawn_scale_combo.setCurrentIndex(host.spawn_scale_combo.findData(current_spawn_scale))
    host.spawn_inherit_dynamic_island_check = ToggleSwitch(host)
    host.spawn_inherit_dynamic_island_check.setChecked(
        bool(host.config.get("spawn_inherit_dynamic_island", False))
    )
    host.clear_spawned_pets_btn = QPushButton("一键清除…", host)
    host.clear_spawned_pets_btn.clicked.connect(host._on_clear_spawned_pets)

    host.on_top_check = ToggleSwitch(host)
    host.on_top_check.setChecked(bool(host.config.get("on_top", True)))
    host.no_move_check = ToggleSwitch(host)
    host.no_move_check.setChecked(bool(host.config.get("no_move", False)))
    host.mouse_through_check = ToggleSwitch(host)
    host.mouse_through_check.setChecked(bool(host.config.get("mouse_through", False)))
    # Windows 专属的光标隐藏穿透仅在 Windows 创建，避免非 Windows 未入布局时游离到窗口左上角。
    host.cursor_hidden_passthrough_check = None
    if sys.platform == "win32":
        host.cursor_hidden_passthrough_check = ToggleSwitch(host)
        host.cursor_hidden_passthrough_check.setChecked(bool(host.config.get("cursor_hidden_passthrough", True)))
    host.drag_physics_check = ToggleSwitch(host)
    host.drag_physics_check.setChecked(bool(host.config.get("drag_physics", False)))
    host.single_process_spawn_check = ToggleSwitch(host)
    host.single_process_spawn_check.setChecked(bool(host.config.get("experimental_single_process_spawn", False)))

    # 甩出力度四档：gentle (轻柔) / standard (标准) / strong (强力) / crazy (疯狂)
    host.throw_strength_select = ModernSelect(host, width=132)
    host.throw_strength_select.addItem("轻柔", "gentle")
    host.throw_strength_select.addItem("标准", "standard")
    host.throw_strength_select.addItem("强力", "strong")
    host.throw_strength_select.addItem("疯狂", "crazy")
    current_strength = str(host.config.get("throw_strength", "standard") or "standard")
    host.throw_strength_select.setCurrentData(current_strength if current_strength in {"gentle", "standard", "strong", "crazy"} else "standard")

    # 弹弓弹射开关
    host.slingshot_check = ToggleSwitch(host)
    host.slingshot_check.setChecked(bool(host.config.get("slingshot_enabled", True)))

    # 多开碰撞设置
    host.collision_enabled_check = ToggleSwitch(host)
    host.collision_enabled_check.setChecked(bool(host.config.get("collision_enabled", True)))
    host.collision_restitution_spin = BrowserDoubleSpinBox(host)
    host.collision_restitution_spin.setRange(0.0, 1.0)
    host.collision_restitution_spin.setSingleStep(0.05)
    host.collision_restitution_spin.setDecimals(2)
    host.collision_restitution_spin.setValue(float(_float_or_default(host.config.get("collision_restitution", 0.82), 0.82, 0.0, 1.0)))
    host.collision_friction_spin = BrowserDoubleSpinBox(host)
    host.collision_friction_spin.setRange(0.0, 0.30)
    host.collision_friction_spin.setSingleStep(0.01)
    host.collision_friction_spin.setDecimals(2)
    host.collision_friction_spin.setValue(float(_float_or_default(host.config.get("collision_friction", 0.08), 0.08, 0.0, 0.30)))
    host.collision_mass_scale_spin = BrowserDoubleSpinBox(host)
    host.collision_mass_scale_spin.setRange(0.5, 2.0)
    host.collision_mass_scale_spin.setSingleStep(0.1)
    host.collision_mass_scale_spin.setDecimals(2)
    host.collision_mass_scale_spin.setValue(float(_float_or_default(host.config.get("collision_mass_scale", 1.0), 1.0, 0.5, 2.0)))
    host.collision_impulse_cap_spin = BrowserDoubleSpinBox(host)
    host.collision_impulse_cap_spin.setRange(1000.0, 12000.0)
    host.collision_impulse_cap_spin.setSingleStep(500.0)
    host.collision_impulse_cap_spin.setDecimals(0)
    host.collision_impulse_cap_spin.setValue(float(_float_or_default(host.config.get("collision_impulse_cap", 9000.0), 9000.0, 1000.0, 12000.0)))
    host.collision_sound_check = ToggleSwitch(host)
    host.collision_sound_check.setChecked(bool(host.config.get("collision_sound_enabled", True)))
    host.collision_sound_volume_spin = BrowserSpinBox(host)
    host.collision_sound_volume_spin.setRange(0, 100)
    host.collision_sound_volume_spin.setSuffix(" %")
    collision_sound_vol = float(host.config.get("collision_sound_volume", 0.70))
    host.collision_sound_volume_spin.setValue(int(round(collision_sound_vol * 100)))

    host.lock_position_check = ToggleSwitch(host)
    host.lock_position_check.setChecked(bool(host.config.get("lock_position", False)))
    host.shift_drag_check = ToggleSwitch(host)
    host.shift_drag_check.setChecked(bool(host.config.get("shift_drag", False)))
    host.pet_opacity_spin = BrowserSpinBox(host)
    host.pet_opacity_spin.setRange(10, 100)
    host.pet_opacity_spin.setSuffix(" %")
    host.pet_opacity_spin.setValue(int(_float_or_default(host.config.get("pet_opacity", 100), 100, 10, 100)))
    host.autostart_check = ToggleSwitch(host)
    host._autostart_initial = autostart_mod.is_enabled()
    host.autostart_check.setChecked(host._autostart_initial)
    if host.config.instance_id:
        host.autostart_check.setEnabled(False)
        host.autostart_check.setToolTip("仅主桌宠可设置")
    host.dock_icon_check = None
    if sys.platform == "darwin":
        host.dock_icon_check = ToggleSwitch(host)
        host.dock_icon_check.setChecked(bool(host.config.get("show_dock_icon", True)))

    # 点击音效控件群
    host.click_sound_check = ToggleSwitch(host)
    host.click_sound_check.setChecked(bool(host.config.get("click_sound_enabled", True)))
    host.click_sound_picker = ClickSoundPackPicker(
        host.config.get("click_sound_pack"),
        parent=host,
    )
    host.click_sound_volume_spin = BrowserSpinBox(host)
    host.click_sound_volume_spin.setRange(0, 100)
    host.click_sound_volume_spin.setSuffix(" %")
    click_vol = float(host.config.get("click_sound_volume", 0.70))
    host.click_sound_volume_spin.setValue(int(round(click_vol * 100)))

    host.click_sound_preview_btn = QPushButton("试听", host)
    host.click_sound_preview_btn.setIcon(vector_widget_icon(host, "sound", 14))
    host.click_sound_preview_btn.setFixedWidth(72)
    host.click_sound_preview_btn.clicked.connect(host._preview_click_sound)

    host.click_sound_check.toggled.connect(host._update_click_sound_controls)
    # 音效开关即时生效：对话框的批量写回发生在关闭时，但声音开关是即时
    # 听觉反馈——用户关掉后期望立刻静音，而不是等关对话框。
    host.click_sound_check.toggled.connect(host._apply_click_sound_enabled_now)
    host.click_balance_check = None
    if host.include_ai:
        host.click_balance_check = ToggleSwitch(host)
        host.click_balance_check.setChecked(bool(host.config.get("click_show_balance", False)))
    host.click_self_talk_check = ToggleSwitch(host)
    host.click_self_talk_check.setChecked(bool(host.config.get("click_show_self_talk", False)))
    host.music_sing_check = ToggleSwitch(host)
    host.music_sing_check.setChecked(bool(host.config.get("music_sing_enabled", False)))
    host.balance_refresh_spin = None
    host.balance_tier_mode_select = None
    host.balance_tier_peak_edit = None
    host.balance_tier_idle_edit = None
    host.balance_tier_color_check = None
    if host.include_ai:
        host.balance_refresh_spin = BrowserSpinBox(host)
        host.balance_refresh_spin.setRange(0, 1440)
        host.balance_refresh_spin.setSuffix(" 分钟")
        host.balance_refresh_spin.setValue(int(host.config.get("balance_refresh_minutes", 0) or 0))
        host.balance_tier_mode_select = ModernSelect(host, width=180)
        host.balance_tier_mode_select.addItem("空闲 / 高峰（默认）", "default")
        host.balance_tier_mode_select.addItem("梁文谷 / 梁文峰", "liangwen")
        host.balance_tier_mode_select.addItem("自定义", "custom")
        host.balance_tier_mode_select.setCurrentData(
            str(host.config.get("balance_tier_labels_mode", "default") or "default")
        )
        host.balance_tier_peak_edit = QLineEdit(host)
        host.balance_tier_peak_edit.setPlaceholderText("高峰文本，例如：梁文峰")
        host.balance_tier_peak_edit.setText(str(host.config.get("balance_tier_label_peak", "") or ""))
        host.balance_tier_idle_edit = QLineEdit(host)
        host.balance_tier_idle_edit.setPlaceholderText("空闲文本，例如：梁文谷")
        host.balance_tier_idle_edit.setText(str(host.config.get("balance_tier_label_idle", "") or ""))
        host.balance_tier_color_check = ToggleSwitch(host)
        host.balance_tier_color_check.setChecked(bool(host.config.get("balance_tier_color_enabled", True)))
    host.auto_hide_fullscreen_check = None
    host.stream_capture_check = None
    if sys.platform == "win32":
        host.auto_hide_fullscreen_check = ToggleSwitch(host)
        host.auto_hide_fullscreen_check.setChecked(bool(host.config.get("auto_hide_fullscreen", True)))
        host.stream_capture_check = ToggleSwitch(host)
        host.stream_capture_check.setChecked(bool(host.config.get("stream_capture_mode", False)))

    host.speed_select = ModernSelect(host, width=112)
    current_speed = float(host.config.get("playback_speed", 1.0))
    speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
    if not any(abs(current_speed - value) < 0.001 for value in speeds):
        speeds.append(current_speed)
        speeds.sort()
    for speed in speeds:
        host.speed_select.addItem(f"{speed:g}x", speed)
    host.speed_select.setCurrentData(current_speed)
    host.gap_spin = BrowserDoubleSpinBox(host)
    host.gap_spin.setRange(0.0, 3600.0)
    host.gap_spin.setSingleStep(0.5)
    host.gap_spin.setDecimals(1)
    host.gap_spin.setSuffix(" 秒")
    host.gap_spin.setValue(float(host.config.get("animation_gap_seconds", 0.0)))

    host.self_talk_check = ToggleSwitch(host)
    host.self_talk_check.setChecked(bool(host.config.get("self_talk_enabled", False)))
    host.idle_low_fps_check = ToggleSwitch(host)
    host.idle_low_fps_check.setChecked(bool(host.config.get("idle_low_fps_enabled", False)))
    host.self_talk_duration_spin = BrowserDoubleSpinBox(host)
    host.self_talk_duration_spin.setRange(1.0, 300.0)
    host.self_talk_duration_spin.setSingleStep(0.5)
    host.self_talk_duration_spin.setDecimals(1)
    host.self_talk_duration_spin.setSuffix(" 秒")
    host.self_talk_duration_spin.setValue(float(host.config.get(
        "self_talk_duration_seconds", DEFAULT_SELF_TALK_DURATION_SECONDS
    )))
    host.bubble_style_select = ModernSelect(host, width=172)
    for value, preset in BUBBLE_STYLE_PRESETS.items():
        host.bubble_style_select.addItem(str(preset["label"]), value)
    host.bubble_style_select.setCurrentData(
        str(host.config.get("self_talk_bubble_style", DEFAULT_SELF_TALK_BUBBLE_STYLE))
    )
    host.min_spin = BrowserDoubleSpinBox(host)
    host.max_spin = BrowserDoubleSpinBox(host)
    for spin, value in (
        (host.min_spin, host.config.get("self_talk_min_interval", DEFAULT_SELF_TALK_MIN_INTERVAL)),
        (host.max_spin, host.config.get("self_talk_max_interval", DEFAULT_SELF_TALK_MAX_INTERVAL)),
    ):
        spin.setRange(5.0, 3600.0)
        spin.setDecimals(0)
        spin.setSuffix(" 秒")
        spin.setValue(float(value))
    host.texts_edit = QPlainTextEdit(host)
    host.texts_edit.setMinimumSize(240, 82)
    host.texts_edit.setMaximumHeight(170)
    texts = host.config.get("self_talk_texts", DEFAULT_SELF_TALK_TEXTS)
    host.texts_edit.setPlainText("\n".join(str(item) for item in texts))
    host.self_talk_image_dir_picker = ResourcePathPicker(
        str(host.config.get("self_talk_image_dir", "") or ""),
        directory=True,
        image_preview=True,
        parent=host,
    )
    host.self_talk_image_scale_spin = BrowserSpinBox(host)
    host.self_talk_image_scale_spin.setRange(50, 300)
    host.self_talk_image_scale_spin.setSuffix(" %")
    host.self_talk_image_scale_spin.setValue(int(host.config.get("self_talk_image_scale", 100)))
    host.click_talk_bindings_btn = QPushButton("编辑…", host)
    host.click_talk_bindings_btn.setObjectName("clickTalkBindingsButton")
    host.click_talk_bindings_btn.clicked.connect(host._open_click_talk_bindings)

    # Agent 联动：每个 Agent 的自定义 thinking 气泡文案
    agent_link_cfg = host.config.get("agent_link", {})
    thinking_texts = agent_link_cfg.get("thinking_texts") or {}
    # 兼容旧的全局 thinking_text 字段
    legacy_text = str(agent_link_cfg.get("thinking_text", "") or "")
    host.thinking_text_edits: dict[str, QLineEdit] = {}
    for agent_key, agent_name in AgentLinkManager.AGENT_NAMES.items():
        edit = QLineEdit(host)
        default = AgentLinkManager._THINKING_DEFAULTS.get(agent_key, f"{agent_name} 正在深度烧烤……")
        edit.setPlaceholderText(default)
        text = str(thinking_texts.get(agent_key, "") or "")
        if not text and legacy_text:
            text = legacy_text
        edit.setText(text)
        edit.setClearButtonEnabled(True)
        host.thinking_text_edits[agent_key] = edit

    host.dialogue_mode_select = ModernSelect(host, width=190)
    for label, value in (("原有模式", "legacy"), ("鲸鱼娘女仆模式", "whale_maid"), ("自定义台词", "custom")):
        host.dialogue_mode_select.addItem(label, value)
    host.dialogue_mode_select.setCurrentData(str(host.config.get("dialogue_mode", "legacy") or "legacy"))
    configured_phrases = host.config.get("dialogue_phrases", {})
    host.dialogue_phrase_edits: dict[str, QPlainTextEdit] = {}
    for key in phrase_keys():
        edit = QPlainTextEdit(host)
        raw_value = configured_phrases.get(key, "")
        if isinstance(raw_value, list):
            edit.setPlainText("\n".join(str(item) for item in raw_value if isinstance(item, str)))
        else:
            edit.setPlainText(str(raw_value or ""))
        edit.setMinimumHeight(48)
        edit.setMaximumHeight(120)
        hint = dialogue_params_hint(key)
        if hint:
            placeholder = "留空使用基础模式台词；本事件支持：" + hint
        else:
            placeholder = "留空使用基础模式台词；本事件无可替换参数"
        edit.setPlaceholderText(placeholder)
        host.dialogue_phrase_edits[key] = edit

    host.dialogue_template_import_edit = QPlainTextEdit(host)
    host.dialogue_template_import_edit.setObjectName("dialogueTemplateImportEdit")
    host.dialogue_template_import_edit.setPlaceholderText(
        "粘贴 persona-phrases/v1 JSON 模板到这里，然后点击“导入模板”"
    )
    host.dialogue_template_import_edit.setMinimumHeight(92)
    host.dialogue_template_import_edit.setMaximumHeight(180)
    host.dialogue_template_export_btn = QPushButton("一键复制模板", host)
    host.dialogue_template_export_btn.setObjectName("dialogueTemplateExportButton")
    host.dialogue_template_export_btn.clicked.connect(host._export_dialogue_template)
    host.dialogue_template_import_btn = QPushButton("导入模板", host)
    host.dialogue_template_import_btn.setObjectName("dialogueTemplateImportButton")
    host.dialogue_template_import_btn.clicked.connect(host._import_dialogue_template_json)
    host.dialogue_template_actions = QWidget(host)
    dialogue_template_actions_layout = QVBoxLayout(host.dialogue_template_actions)
    dialogue_template_actions_layout.setContentsMargins(0, 0, 0, 0)
    dialogue_template_actions_layout.setSpacing(6)
    dialogue_template_actions_layout.addWidget(host.dialogue_template_import_edit)
    dialogue_template_buttons = QHBoxLayout()
    dialogue_template_buttons.setContentsMargins(0, 0, 0, 0)
    dialogue_template_buttons.addWidget(host.dialogue_template_export_btn)
    dialogue_template_buttons.addWidget(host.dialogue_template_import_btn)
    dialogue_template_actions_layout.addLayout(dialogue_template_buttons)
    host.agent_sound_check = ToggleSwitch(host)
    host.agent_sound_check.setChecked(bool(agent_link_cfg.get("sound_enabled", False)))

    # 辅助构建包含“开关+路径选择+试听”的组合控件
    def _build_agent_event_row(evt_key: str, default_builtin: str) -> tuple[QWidget, ToggleSwitch, ResourcePathPicker, QPushButton]:
        toggle = ToggleSwitch(host)
        toggle.setChecked(bool(agent_link_cfg.get(f"sound_{evt_key}_enabled", True)))
        path_val = str(agent_link_cfg.get(f"sound_{evt_key}_path") or default_builtin)
        picker = ResourcePathPicker(path_val, name_filter=AUDIO_NAME_FILTER, parent=host)
        preview_btn = QPushButton("试听", host)
        preview_btn.setIcon(vector_widget_icon(host, "sound", 14))
        preview_btn.setFixedWidth(72)
        preview_btn.clicked.connect(lambda _, k=evt_key: host._preview_agent_sound(k))
        container = ResponsiveToggleActionRow(toggle, picker, preview_btn, host)
        return container, toggle, picker, preview_btn

    (host.agent_sound_start_widget, host.agent_sound_start_check,
     host.agent_sound_start_picker, host.agent_sound_start_preview) = _build_agent_event_row("start", "builtin:agent-start")

    (host.agent_sound_done_widget, host.agent_sound_done_check,
     host.agent_sound_done_picker, host.agent_sound_done_preview) = _build_agent_event_row("done", "builtin:agent-done")

    (host.agent_sound_error_widget, host.agent_sound_error_check,
     host.agent_sound_error_picker, host.agent_sound_error_preview) = _build_agent_event_row("error", "builtin:agent-error")

    host.agent_sound_volume_spin = BrowserSpinBox(host)
    host.agent_sound_volume_spin.setRange(0, 100)
    host.agent_sound_volume_spin.setSuffix(" %")
    agent_vol = float(agent_link_cfg.get("sound_volume", 0.65))
    host.agent_sound_volume_spin.setValue(int(round(agent_vol * 100)))

    host.agent_sound_cooldown_spin = BrowserDoubleSpinBox(host)
    host.agent_sound_cooldown_spin.setRange(0.0, 30.0)
    host.agent_sound_cooldown_spin.setSingleStep(0.5)
    host.agent_sound_cooldown_spin.setDecimals(1)
    host.agent_sound_cooldown_spin.setSuffix(" 秒")
    host.agent_sound_cooldown_spin.setValue(float(agent_link_cfg.get("sound_cooldown_seconds", 2.0)))

    host.agent_sound_check.toggled.connect(host._update_agent_sound_controls)
    host.agent_sound_check.toggled.connect(host._apply_agent_sound_enabled_now)
    host.agent_sound_start_check.toggled.connect(lambda: host._update_agent_sound_subcontrols())
    host.agent_sound_done_check.toggled.connect(lambda: host._update_agent_sound_subcontrols())
    host.agent_sound_error_check.toggled.connect(lambda: host._update_agent_sound_subcontrols())

    # 待办提醒：偏好两键（条目在右键菜单「待办提醒」面板中管理）
    host.todo_reminder_check = ToggleSwitch(host)
    host.todo_reminder_check.setChecked(bool(host.config.get("todo_reminder_enabled", True)))
    host.todo_reminder_lead_spin = BrowserSpinBox(host)
    host.todo_reminder_lead_spin.setRange(0, 60)
    host.todo_reminder_lead_spin.setSuffix(" 分钟")
    host.todo_reminder_lead_spin.setValue(int(host.config.get("todo_reminder_lead_minutes", 5) or 0))

    appearance = host.config.get("context_menu_appearance", DEFAULT_CONTEXT_MENU_APPEARANCE)
    host.menu_theme_select = ModernSelect(host, width=132)
    for label, value in (("跟随系统", "system"), ("浅色", "light"), ("深色", "dark")):
        host.menu_theme_select.addItem(label, value)
    host.menu_theme_select.setCurrentData(appearance.get("theme", "system"))
    host.menu_density_select = ModernSelect(host, width=132)
    for label, value in (("紧凑", "compact"), ("标准", "standard"), ("宽松", "spacious")):
        host.menu_density_select.addItem(label, value)
    host.menu_density_select.setCurrentData(appearance.get("density", "standard"))
    host.menu_radius_select = ModernSelect(host, width=112)
    for radius in (8, 12, 16, 18):
        host.menu_radius_select.addItem(f"{radius} px", radius)
    host.menu_radius_select.setCurrentData(int(appearance.get("corner_radius", 12)))
    host.menu_font_select = ModernSelect(host, width=172)
    host.menu_font_select.addItem("系统默认", "system")
    host._menu_fonts_populated = False
    current_font = str(appearance.get("ui_font") or "system")
    if current_font != "system":
        # 保留当前配置值无需枚举字体库，确保用户未展开选择器直接保存时
        # 不会把自定义字体静默重置为 system。
        host.menu_font_select.addItem(current_font, current_font)
    host.menu_font_select.setCurrentData(current_font)
    # Windows 字体较多时首次枚举可阻塞数秒。零延迟定时器仍会在
    # 设置窗口首帧绘制前运行，因此改为仅在用户真正展开字体选择器时加载。
    host.menu_font_select.aboutToShowPopup.connect(host._populate_menu_fonts)
    host.menu_font_size_select = ModernSelect(host, width=112)
    for size in range(10, 19):
        host.menu_font_size_select.addItem(f"{size} px", size)
    host.menu_font_size_select.setCurrentData(int(appearance.get("ui_font_size", 13)))
    host.menu_translucent_check = ToggleSwitch(host)
    host.menu_translucent_check.setChecked(bool(appearance.get("translucent", True)))
    host.menu_opacity_spin = BrowserDoubleSpinBox(host)
    host.menu_opacity_spin.setRange(0.72, 1.0)
    host.menu_opacity_spin.setSingleStep(0.02)
    host.menu_opacity_spin.setDecimals(2)
    host.menu_opacity_spin.setValue(float(appearance.get("opacity", 0.94)))

    def color_picker(key: str) -> ColorPicker:
        return ColorPicker(str(appearance.get(key) or DEFAULT_CONTEXT_MENU_APPEARANCE[key]), host)

    host.light_background_picker = color_picker("light_background")
    host.light_foreground_picker = color_picker("light_foreground")
    host.light_hover_picker = color_picker("light_hover")
    host.dark_background_picker = color_picker("dark_background")
    host.dark_foreground_picker = color_picker("dark_foreground")
    host.dark_hover_picker = color_picker("dark_hover")

    egg = host.config.get("menu_easter_egg", DEFAULT_MENU_EASTER_EGG)
    host.egg_enabled_check = ToggleSwitch(host)
    host.egg_enabled_check.setChecked(bool(egg.get("enabled", True)))
    host.egg_title_edit = _line_edit(str(egg.get("title") or "厉害了我的鲸"), width=240)
    host.egg_hint_edit = _line_edit(str(egg.get("hint") or "请点击"), width=160)
    avatar = resolve_fun_asset(egg.get("avatar"), oijingjing_image_path())
    image_dir = resolve_fun_asset(egg.get("image_dir"), oijingjing_image_path().parent)
    host.egg_avatar_picker = ResourcePathPicker(str(avatar.resolve()), parent=host)
    host.egg_image_dir_picker = ResourcePathPicker(
        str(image_dir.resolve()), directory=True, image_preview=True, parent=host,
    )

    # 灵动岛
    island_cfg = host.config.get("dynamic_island", {})
    if not isinstance(island_cfg, dict):
        island_cfg = {}
    host.island_enabled_check = ToggleSwitch(host)
    host.island_enabled_check.setChecked(bool(island_cfg.get("enabled", False)))
    host.island_icon_check = ToggleSwitch(host)
    host.island_icon_check.setChecked(bool(island_cfg.get("show_icon", True)))
    host.island_name_check = ToggleSwitch(host)
    host.island_name_check.setChecked(bool(island_cfg.get("show_name", True)))
    host.island_info_check = ToggleSwitch(host)
    host.island_info_check.setChecked(bool(island_cfg.get("show_info", True)))
    host.island_status_check = ToggleSwitch(host)
    host.island_status_check.setChecked(bool(island_cfg.get("show_status", True)))
    host.island_info_mode_select = ModernSelect(host, width=160)
    for label, value in (
        ("当前时间", "time"),
        ("余额峰谷", "balance_tier"),
        ("余额数值", "balance"),
        ("自定义短文本", "custom"),
    ):
        host.island_info_mode_select.addItem(label, value)
    host.island_info_mode_select.setCurrentData(str(island_cfg.get("info_mode") or "time"))
    host.island_style_select = ModernSelect(host, width=160)
    for label, value in (
        ("黑色", "dark"),
        ("白色", "light"),
        ("玻璃质感", "glass"),
    ):
        host.island_style_select.addItem(label, value)
    host.island_style_select.setCurrentData(str(island_cfg.get("style") or "dark"))
    host.island_icon_select = ModernSelect(host, width=160)
    for emoji in ("🐳", "🐟", "🐙", "🦭", "🐧", "🐱", "🐶", "🌟", "⚡", "❤️"):
        host.island_icon_select.addItem(emoji, emoji)
    host.island_icon_select.setCurrentData(str(island_cfg.get("icon") or "🐳"))
    host.island_custom_text_edit = _line_edit(str(island_cfg.get("custom_text") or ""), width=220)

# ------------------------------------------------------------ 主动识屏
    if sys.platform == "win32" and host.include_ai:
        host._build_proactive_controls()
