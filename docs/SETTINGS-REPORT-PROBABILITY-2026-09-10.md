# 设置变更记录：过程汇报概率 report_probability（2026-09-10）

按 `docs/SETTINGS-CHANGE-GATES.md` 记录准入契约与准出证据。本次变更类型：**新增设置项 +
调整既有默认值**（不新增设置分组，不引入平台分支）。

## 1. 准入契约

| 字段 | 内容 |
|---|---|
| setting_id | `report_probability` |
| domain_id / group_id | `agent_link` / 设置页「Agent 联动 · 汇报频率」 |
| title | 过程汇报概率 |
| description | Agent 干活中的过程汇报（「正在读文件/跑命令/改代码…」）是提醒量最大的一类，按此概率抽稀。0% 等于关闭过程汇报，100% 全部汇报；开始干活、完成、审批/提问、硬失败、模型访问失败等提醒不受影响，始终汇报。 |
| search_aliases | 过程汇报、汇报概率、抽稀、概率、report_probability、提醒频率 |
| default | `60` |
| capability_requirement / platform_availability | 无（纯配置项，不依赖音频/托盘/IPC 等能力，全平台一致） |
| disclosure_level | 一级：与过程汇报相关的可调参数直接露出，不折叠 |
| dependency | 逻辑依赖 `agent_link.notify_activity`；`notify_activity=false` 或 `report_probability=0` 均静音，二者取交集 |
| preview_target | 无独立预览（概率不产生可视化产物）；改动即时生效，无需重启 |
| commit_policy | 保存即落盘（与其他 agent_link 数值项一致） |
| migration | 无需迁移：旧配置缺键时按默认 60 读取；越界/非法值在 `_clean_agent_link_data` 收敛（见下） |
| recovery | 设置页可随时改回；`0` 与 `100` 均为可逆端点值 |

### 同批调整的默认值（用户定稿：1 常开、2 加概率、其他常开）

`notify_state`、`notify_activity`、`stuck_detect`、`pattern_detect` 由 `False` 改为 `True`；
`report_probability` 新增默认 `60`。**不暴露** 5 个 `notify_*` 开关（用户决定），
因此 `report_probability = 0%` 即是「关闭过程汇报」的入口。

**副作用（需知）**：`stuck_detect` / `pattern_detect` 默认由关改开，卡住提醒与行为模式提醒的
量会上升；如觉得吵，本次未提供开关，需要后续单独决策。

## 2. 清洗与边界

`pet/config.py::_clean_agent_link_data`：

```python
if "report_probability" in raw:
    result["report_probability"] = int(_float_or_default(
        raw.get("report_probability"), defaults["report_probability"], 0.0, 100.0
    ))
```

- 非数值（`None` / `"abc"`）→ 回落默认 60
- 数值字符串 `"80"` → 80
- 越界 → 收敛到 `[0, 100]`（`-5`→0、`999`→100）
- 小数 → `int()` 截断（`59.6`→59）

## 3. 抽稀语义（为什么放在这里）

`pet/agent_link.py::should_report_activity(probability, roll) → roll * 100.0 < probability`

- 只作用于**出气泡的汇报路径**（`_on_agent_activity`）。
- 位置在三重节流（同 agent 10s / 全局 8s / 同工具 60s）**之后**，且抽稀丢弃**不记账**
  （不更新 `_last_activity` / `_activity_global_last`），避免概率与节流叠加造成过度衰减。
- `raw_record` 是独立信号链（侧接 `_stuck_detector` / `_behavior_detector` /
  `_exploration_watchdog` / `_on_exploration_lifecycle` / `_on_interaction_lifecycle` /
  `_remember_dialogue_record`），不经过本函数——检测类消费者与对话记忆不受抽样影响。
- `rng` 可注入（`AgentLinkManager(..., rng=...)`），供测试使用确定序列；否则默认 60% 抽样会
  使默认路径的用例时而弹时而静默。

## 4. 准出证据

| 项 | 证据 |
|---|---|
| 默认值 | `tests/test_report_probability.py::test_default_report_probability_is_60`、`test_always_on_family_defaults`；`ptmp-prob-drive.py` 默认值 5 项全 OK |
| 持久化往返 | `ptmp-ui-entry-drive.py`：设置页设 25 → `_save()` → 重新加载 Config 仍 25（11/0 通过） |
| 迁移 | 缺键按默认 60；`test_clean_agent_link_data_keeps_default_when_absent` |
| 依赖 | `notify_activity=false` 静音、`report_probability=0` 静音，二者取交集（`test_notify_activity_off_still_silences`、`test_zero_probability_equals_off`） |
| 边界 | `test_should_report_activity_boundaries` 8 例；驱动脚本 0/100、roll 0.6 边界 |
| 保存策略 | 保存即落盘，与同组数值项一致（驱动脚本验证 0/100/25 均落盘） |
| 恢复 | 设置页改回即恢复；无破坏性写入 |
| 布局与可访问性 | 未做完整验收（见 §5 未完成项） |
| 跨平台 | 无平台分支；仅在 Windows 做了一次真实 GUI 构建（`ptmp-ui-entry-drive.py`，offscreen） |
| 视觉与文档 | 本文件；`CONTEXT.md` 待同步 |

复跑命令（本地已执行）：

```
python -m ruff check pet/config.py pet/agent_link.py pet/settings_pet_controls.py \
    pet/modern_settings_dialog.py tests/test_report_probability.py tests/test_agent_link.py
python -m pytest tests/test_report_probability.py -q      # 20 passed（6 个 error 为沙箱 tmp_path 权限）
python ptmp-prob-drive.py                                  # 20 通过 / 0 失败
python ptmp-ui-entry-drive.py                              # 11 通过 / 0 失败
```

## 5. 未完成项

1. 设置页门禁的布局/可访问性三档（紧凑/常规/宽屏无裁切、字体放大、Tab 顺序、明暗主题）
   与代表截图未做；跨平台仅 Windows + offscreen。
2. `CONTEXT.md` 的 Settings System 段落待同步。
3. 全量 pytest 由用户执行（沙箱无法跑 `tmp_path` 用例）。

## 6. 标识符决策（原遗留问题 4）

**结论：不改名。** 用户可见语义已统一为「模型访问失败」，但以下标识符保持原样：

| 标识符 | 位置 | 保持不变的理由 |
|---|---|---|
| `rate_limit.one` / `rate_limit.many` | 人格文案词表键（`pet/persona_template.py`、`pet/persona_presets/*.json`） | 是**用户可编辑文案**的存储键。改名会使已保存的自定义文案失配，需要迁移；而用户看到的标签已改成「模型访问失败 / 模型访问失败（连续）」，改键名只有内部命名收益 |
| 线协议事件名 `rate_limit` | 桥接写出 → pet 消费 | 属跨仓协议标识符；改名需两端协同发布，不应夹在本阶段收尾 |
| `alert_id` 前缀 `429-rate-limit:` | 运行期内部标识 | 不落盘、不对用户展示，改名无收益 |

若后续确实要改键名，按第二刀既有纪律做「换新名 + config 一次性迁移（不留兼容别名）」，
并在 `docs/PERSONA-PHRASES-PRESET-STORAGE-2026-09-08.md` 登记。
