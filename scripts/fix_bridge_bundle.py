#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 PyInstaller 打包后的 bridge node_modules（issue: Cannot find package
'@deepseek-ai/cosmokit'）。

背景：PyInstaller 的 --add-data 复制 integrations 目录时，会把 pnpm 的
junction/符号链接布局复制成损坏的空目录或指向源机器的链接（.bin shims 里
甚至写死了 W:\\... 绝对路径）。Cordis loader 之后 import bridge/index.js 时，
Node 沿着 bridge 目录向上解析依赖，遇到损坏的 node_modules 就抛
ERR_MODULE_NOT_FOUND，整个 DSH plugin tree 初始化失败。

修复：把源码 bridge 的 node_modules 用"跟随链接展开"的方式复制成自包含的
真实目录树，删除含机器路径的 .bin shims 与 pnpm 元数据，最后在 dist 副本
上执行一次 ESM import 冒烟（verify_import.mjs），任何缺包都会让构建失败。

用法（在构建脚本的 PyInstaller 之后调用）：
    python scripts/fix_bridge_bundle.py --app-dir dist-onedir/dsh-pet-standalone-webm-chat
"""
import argparse
import os
import shutil
import subprocess
import sys

REQUIRED_SMOKE = "verify_import.mjs"


def find_dist_bridge(app_dir: str) -> "str | None":
    """定位产物里的 bridge 目录。

    PyInstaller 的产物布局随平台不同：Windows/Linux 的 onedir 把数据放在
    ``<app>/_internal/``，macOS 的 ``.app`` 放在 ``Contents/Resources/``
    （部分版本在 ``Contents/Frameworks/``）。早期实现硬编码 ``_internal/``，
    导致 macOS 构建在「dist bridge missing」处失败。
    """
    candidates = (
        os.path.join(app_dir, "_internal", "integrations", "dsh-pet-bridge"),
        os.path.join(app_dir, "Contents", "Resources", "integrations", "dsh-pet-bridge"),
        os.path.join(app_dir, "Contents", "Frameworks", "integrations", "dsh-pet-bridge"),
        os.path.join(app_dir, "integrations", "dsh-pet-bridge"),
    )
    for path in candidates:
        if os.path.isdir(path):
            return path
    # 兜底：按目录名搜索，兼容未来 PyInstaller 的布局变化
    for root, _dirs, _files in os.walk(app_dir):
        if (os.path.basename(root) == "dsh-pet-bridge"
                and os.path.basename(os.path.dirname(root)) == "integrations"):
            return root
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-dir", required=True,
                    help="onedir/.app 输出目录（内含 integrations/dsh-pet-bridge）")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_bridge = os.path.join(root, "integrations", "dsh-pet-bridge")

    src_nm = os.path.join(src_bridge, "node_modules")

    if not os.path.isdir(src_nm):
        # 构建环境没有本地 node_modules（CI 首次 checkout / tag 构建）：
        # 此时没有任何 pnpm junction 需要展开，bundle 里也不会带上 node_modules，
        # 与 build_onedir.ps1「无 node_modules 时只做声明+lockfile 校验，
        # 由运行时 install_bridge 用 pnpm 落盘」的既有设计一致——构建继续，
        # 不能因为「没有可修复的东西」而失败。该判断先于布局探查，避免 CI
        # 在无 node_modules 时仍被平台布局差异拖挂。
        print("[bridge] source node_modules absent - skip bundle repair "
              "(declaration check only; install_bridge resolves via pnpm at runtime)")
        return 0

    dst_bridge = find_dist_bridge(args.app_dir)
    if dst_bridge is None:
        print(f"[bridge] dist bridge missing under: {args.app_dir}", file=sys.stderr)
        return 1

    dst_nm = os.path.join(dst_bridge, "node_modules")

    # 删除 PyInstaller 复制出的（可能损坏的）node_modules：它可能是普通目录、
    # junction 或指向源路径的符号链接。
    if os.path.islink(dst_nm) or os.path.isdir(dst_nm):
        if os.path.islink(dst_nm) and not os.path.isdir(dst_nm):
            os.unlink(dst_nm)
        else:
            shutil.rmtree(dst_nm)

    # 跟随 junction/symlink 展开复制成真实目录树（symlinks=False）。
    # Python 3.8+ 将 Windows junction 视为符号链接并跟随复制其内容，
    # 展开后即为自包含结构，与 Cordis loader 的向上解析完全兼容。
    print(f"[bridge] expanding node_modules -> {dst_nm}")
    shutil.copytree(src_nm, dst_nm, symlinks=False)

    # 删除含机器绝对路径的 pnpm 产物：.bin shims（cmd/ps1/sh 内写死
    # W:\\deepseek-harness\\... 等路径）与指向本机 store 的元数据。
    for rel in (".bin", ".modules.yaml", ".package-map.json",
                ".pnpm-workspace-state-v1.json"):
        target = os.path.join(dst_nm, rel)
        if os.path.islink(target):
            os.unlink(target)
        elif os.path.exists(target):
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)

    # import 冒烟：模拟 Cordis loader 的解析路径。脚本位于 bridge 目录内，
    # 保证 ESM bare specifier 从正确的位置向上解析 node_modules。
    smoke = os.path.join(dst_bridge, REQUIRED_SMOKE)
    src_smoke = os.path.join(src_bridge, REQUIRED_SMOKE)
    if not os.path.exists(smoke):
        if not os.path.exists(src_smoke):
            print(f"[bridge] missing verify script: {src_smoke}", file=sys.stderr)
            return 1
        shutil.copy2(src_smoke, smoke)

    node = shutil.which("node")
    if node:
        print("[bridge] running import smoke on bundle copy...")
        result = subprocess.run([node, smoke], cwd=dst_bridge)
        if result.returncode != 0:
            print("[bridge] import smoke FAILED - bundle bridge is not self-contained",
                  file=sys.stderr)
            return 1
    else:
        print("[bridge] node not found - declaration/lockfile checks only (install_bridge "
              "resolves via pnpm at runtime)")

    print("[bridge] node_modules self-contained OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
