# -*- coding: utf-8 -*-
import json
import re
from pet.persona_phrases import phrase_keys
from pet.persona_template import build_persona_template, template_json


def test_template_is_complete_and_safe():
    data = build_persona_template({"dialogue_mode": "custom", "dialogue_phrases": {"start": "你好，{name}"}, "api_key": "secret", "path": "C:/secret"})
    assert data["template"] == "persona-phrases/v1"
    assert set(data["phrases"]) == set(phrase_keys())
    assert data["phrases"]["start"] == ["你好，{name}"]
    assert data["phrases"]["thinking"] == []
    assert data["variables"]["command"]
    text = template_json({"dialogue_phrases": {"start": "中文\n\""}})
    assert json.loads(text)["phrases"]["start"] == ["中文\n\""]
    assert "secret" not in text and "C:/secret" not in text


def test_template_limits_and_ignores_bad_values():
    data = build_persona_template({"dialogue_phrases": {"start": [" a ", 3] * 10, "thinking": None}})
    assert data["phrases"]["start"] == ["a"] * 8
    assert data["phrases"]["thinking"] == []

def test_all_advertised_fields_reach_presentation_layer():
    """模板宣称的每个字段都必须真正到达表现层（气泡/弹窗文案渲染）。

    两层机械验证，杜绝「模板提供了字段、运行时却从未注入」的糖衣：
    1. AST 解析 pet/agent_link.py 与 pet/app.py 里全部 _dialogue/_persona_text
       调用点，断言 PARAMETERS[key] == 该 key 调用点显式注入的 kwargs 并集
       （双向：多宣称=占位符永远原样露出的谎言；少宣称=已注入却不告知）。
       动态 key 调用点（activity/pattern/rate_limit）按 kwargs 签名归组校验。
    2. UPSTREAM_FIELDS 的每个上下文字段都必须在桥接插件源码中出现（桥确实
       会写出），或属于 Pet 侧注入（agent_key）。
    审计依据：docs/PERSONA-TEMPLATE-FIELD-ALIGNMENT-2026-09-05.md
    """
    import ast
    from pathlib import Path

    from pet.persona_template import (
        DISPLAY_HINTS, EVENT_SOURCES, PARAMETERS, UPSTREAM_FIELDS, VARIABLES,
    )

    root = Path(__file__).resolve().parent.parent
    delivered = {}
    dynamic = []
    for fname in ("agent_link.py", "app.py"):
        tree = ast.parse((root / "pet" / fname).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if callee not in ("_dialogue", "_persona_text") or not node.args:
                continue
            key_arg = node.args[0] if callee == "_dialogue" else node.args[1]
            kws = {kw.arg for kw in node.keywords if kw.arg}
            has_expansion = any(kw.arg is None for kw in node.keywords)
            if isinstance(key_arg, ast.Constant) and isinstance(key_arg.value, str):
                delivered.setdefault(key_arg.value, set()).update(kws)
            else:
                dynamic.append((has_expansion, frozenset(kws)))

    # 动态 key 调用点：activity（**values 展开）/ pattern（name, reasons）/ rate_limit（count）
    assert (True, frozenset()) in dynamic, "activity 调用点应显式传 values 字典（含 tool/target 等）"
    assert (False, frozenset({"name", "reasons"})) in dynamic, "pattern 动态调用点缺失"
    assert (False, frozenset({"count"})) in dynamic, "rate_limit 动态调用点缺失"
    # activity 调用点会读记录里的 target/ok 并按需注入，但桥接写出的 tool/call
    # 记录从不含这两个字段（只在 tool/result / watchdog reasoning）——活动气泡
    # 渲染时填充物是 tool/call，因此模板不宣称（写了就是永不替换的占位符）。
    activity_fields = ("name", "tool", "label", "target", "callId", "step", "ok")
    activity_unadvertised = {"target", "ok"}
    dynamic_delivered = {
        "activity.read": set(activity_fields), "activity.search": set(activity_fields),
        "activity.edit": set(activity_fields), "activity.run": set(activity_fields),
        "activity.default": set(activity_fields),
        "pattern.warning": {"name", "reasons"}, "pattern.control": {"name", "reasons"},
        "rate_limit.one": {"count"}, "rate_limit.many": {"count"},
    }

    data = build_persona_template(None)
    entries = {e["key"]: e for e in data["entries"]}

    # variables/upstream 结构 sanity：cordis 等死字段不得回流
    assert set(VARIABLES) == {
        "name", "command", "label", "body", "count", "reasons", "detail", "text",
        "tool", "callId", "step",
    }
    assert "cordis" not in data["upstream"]["fields"]
    assert "sessionName" not in UPSTREAM_FIELDS["base"], "桥接从不写出 sessionName"
    assert set(PARAMETERS) == set(entries) == set(phrase_keys())
    for key, entry in entries.items():
        assert key in DISPLAY_HINTS and key in EVENT_SOURCES, key
        # 严格逐 key 相等：entries.parameters 只能列该项上游方法显式注入的字段，
        # 组级上下文字段（ts/sessionId/errorCode 等）不得混入——否则 AI 会写出
        # 运行时永远原样露出的占位符（如 agent.error 宣称 {errorCode}）。
        assert entry["parameters"] == list(PARAMETERS[key]), key

    # 典型误报场景抽查：状态机/检测器触发的弹窗只有保证参数
    assert entries["start"]["parameters"] == ["name"]
    assert entries["agent.error"]["parameters"] == ["name"]
    assert entries["llm_error.api"]["parameters"] == []
    assert entries["rate_limit.one"]["parameters"] == ["count"]
    assert entries["approval.command"]["parameters"] == ["name", "command"]

    # ── 核心保证：模板宣称参数 == 调用点实际注入（双向相等）──
    # activity 的 target/ok 属「注入但不宣称」：记录里永不出现，宣称即谎言。
    for key in phrase_keys():
        actual = delivered.get(key, set()) | dynamic_delivered.get(key, set())
        if key.startswith("activity."):
            actual = actual - activity_unadvertised
        assert set(PARAMETERS[key]) == actual, (
            key + ": 模板宣称 " + str(sorted(PARAMETERS[key]))
            + " != 运行时注入 " + str(sorted(actual))
        )

    # activity 不得残留从未传入的死字段；宣称的字段必须全部真的注入
    advertised_activity = {"name", "tool", "label", "callId", "step"}
    assert advertised_activity <= set(entries["activity.read"]["parameters"])
    for dead in ("arguments", "argsKey", "command", "toolName", "riskScore", "pluginId",
                 "sessionName", "target", "ok"):
        assert dead not in entries["activity.read"]["parameters"]

    # 审批/提问/限流/余额：与调用点一致
    assert set(entries["approval.command"]["parameters"]) >= {"name", "command"}
    assert set(entries["question.one"]["parameters"]) >= {"name", "body"}
    assert "count" in entries["rate_limit.one"]["parameters"]
    assert entries["balance.result"]["parameters"] == ["text"]

    # balance.loading/balance.result 真实渲染（pet/app.py），必须可导出；死键不得回流
    assert "balance.loading" in entries and "balance.result" in entries
    assert "balance.query" not in entries

    # ── 上下文字段层：桥接插件确实写出这些字段（或 Pet 侧注入）──
    bridge_src = (root / "integrations" / "dsh-pet-bridge" / "index.js").read_text(encoding="utf-8")
    agent_link_src = (root / "pet" / "agent_link.py").read_text(encoding="utf-8")
    pet_side_fields = {"agent_key"}
    for group, fields in UPSTREAM_FIELDS.items():
        for field in fields:
            if field in pet_side_fields:
                assert "agent_key" in agent_link_src
                continue
            pattern = chr(92) + "b" + re.escape(field) + chr(92) + "b"
            assert re.search(pattern, bridge_src), (
                "UPSTREAM_FIELDS[" + repr(group) + "] 的 " + repr(field)
                + " 在桥接插件中不存在，模板不得宣称"
            )
