#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把仓库所有文本文件统一成 UTF-8 无 BOM。
策略：
  - 按扩展名黑名单排除明显二进制
  - 其余文件读字节，依次检测：UTF-8 BOM / UTF-16 BOM / 无BOM UTF-8 / GB18030 / UTF-16无BOM
  - 已是 UTF-8 无 BOM 的跳过；其余转换后写回（仅当内容变化时）
  - 解码均失败的当作二进制跳过
"""

import os
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\33643\git\notepad-- github")
SKIP_DIRS = {".git", ".codeartsdoer", "build", "build-release", "debug",
             "release", "x64", "Win32", "tmp", "temp", "__pycache__",
             ".vs", ".vscode", "node_modules"}
SKIP_FILES = {"_to_utf8.py", "_compare_repos.py", "_compare_content.py",
              "_compare_cross.py", "_repo_diff_report.md", "_content_diff_report.md",
              "_cross_match_report.md", "_整合方案.md", "_utf8_report.md"}

BIN_EXT = {
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".pdf",
    ".db", ".sqlite", ".sqlite3", ".mdb",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp", ".tiff", ".tif",
    ".zip", ".gz", ".tar", ".tgz", ".bz2", ".7z", ".rar", ".xz",
    ".o", ".a", ".so", ".dll", ".exe", ".lib", ".obj", ".pdb",
    ".bin", ".dat", ".mo", ".qm", ".rcc", ".qss",
    ".pyc", ".pyo", ".class", ".jar", ".war", ".wasm",
    ".eot", ".ttf", ".otf", ".woff", ".woff2",
    ".mp3", ".mp4", ".wav", "avi", ".mov", ".flv", ".swf",
    ".tlog", ".lastbuildstate", ".unsuccessfulbuild", ".recipe",
    ".hdr", ".sdf", ".opensdf", ".aps", ".ncb", ".opendb",
    ".ipch", ".pch", ".ilk", ".meta", ".iobj", ".ipdb",
    ".pgc", ".pgd", ".rsp", ".sbr", ".tlb", ".tli", ".tlh",
    ".tmp", ".suo", ".user", ".userosscache",
}

UTF8_BOM = b"\xef\xbb\xbf"
UTF16_LE_BOM = b"\xff\xfe"
UTF16_BE_BOM = b"\xfe\xff"


def detect_and_convert(data: bytes):
    """返回 (new_bytes_or_None, action)。new_bytes 为 None 表示无需写入。"""
    if data.startswith(UTF8_BOM):
        body = data[3:]
        try:
            body.decode("utf-8")
            return body, "bom_removed"
        except UnicodeDecodeError:
            pass
    if data.startswith(UTF16_LE_BOM):
        try:
            return data.decode("utf-16-le").encode("utf-8"), "utf16le_bom"
        except UnicodeDecodeError:
            pass
    if data.startswith(UTF16_BE_BOM):
        try:
            return data.decode("utf-16-be").encode("utf-8"), "utf16be_bom"
        except UnicodeDecodeError:
            pass
    try:
        data.decode("utf-8")
        return None, "skip_utf8"
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("gb18030").encode("utf-8"), "gb18030_to_utf8"
    except UnicodeDecodeError:
        pass
    if len(data) >= 2 and data[1] == 0x00 and data[0] != 0x00:
        try:
            return data.decode("utf-16-le").encode("utf-8"), "utf16le_nobom"
        except UnicodeDecodeError:
            pass
    if len(data) >= 2 and data[0] == 0x00 and data[1] != 0x00:
        try:
            return data.decode("utf-16-be").encode("utf-8"), "utf16be_nobom"
        except UnicodeDecodeError:
            pass
    return None, "skip_unknown"


def main():
    stats = {}
    changed = []
    unknown = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES:
                continue
            p = Path(dirpath) / fn
            if p.suffix.lower() in BIN_EXT:
                continue
            try:
                data = p.read_bytes()
            except Exception:
                continue
            if not data:
                continue
            total += 1
            new, action = detect_and_convert(data)
            stats[action] = stats.get(action, 0) + 1
            if new is not None and new != data:
                try:
                    p.write_bytes(new)
                    changed.append((p.relative_to(ROOT).as_posix(), action))
                except Exception as e:
                    unknown.append((str(p), f"写入失败: {e}"))
            elif action == "skip_unknown":
                unknown.append((p.relative_to(ROOT).as_posix(), "无法识别编码"))

    out = []
    out.append("# UTF-8 统一转换报告")
    out.append("")
    out.append(f"扫描文本文件数: **{total}**")
    out.append("")
    out.append("## 统计")
    out.append("")
    out.append("| 动作 | 数量 | 说明 |")
    out.append("|------|------|------|")
    desc = {
        "skip_utf8": "已是 UTF-8 无 BOM，跳过",
        "bom_removed": "去除 UTF-8 BOM",
        "utf16le_bom": "UTF-16 LE(BOM) → UTF-8",
        "utf16be_bom": "UTF-16 BE(BOM) → UTF-8",
        "utf16le_nobom": "UTF-16 LE(无BOM) → UTF-8",
        "utf16be_nobom": "UTF-16 BE(无BOM) → UTF-8",
        "gb18030_to_utf8": "GB18030/GBK → UTF-8",
        "skip_unknown": "无法识别，跳过",
    }
    for k in ["skip_utf8", "bom_removed", "gb18030_to_utf8",
              "utf16le_bom", "utf16be_bom", "utf16le_nobom", "utf16be_nobom",
              "skip_unknown"]:
        if k in stats:
            out.append(f"| {k} | {stats[k]} | {desc[k]} |")
    out.append("")
    out.append(f"**实际改写文件: {len(changed)} 个**")
    out.append("")
    if changed:
        out.append("## 已转换文件清单")
        out.append("")
        out.append("| # | 文件 | 转换 |")
        out.append("|---|------|------|")
        for i, (f, a) in enumerate(sorted(changed), 1):
            out.append(f"| {i} | `{f}` | {a} |")
        out.append("")
    if unknown:
        out.append(f"## 无法识别/写入失败的文件（{len(unknown)} 个，可能为二进制）")
        out.append("")
        for f, r in unknown[:200]:
            out.append(f"- `{f}` — {r}")
        out.append("")

    rep = ROOT / "_utf8_report.md"
    rep.write_text("\n".join(out), encoding="utf-8")
    print(f"\n报告: {rep}", file=sys.stderr)
    print(f"扫描 {total} 个文本文件，改写 {len(changed)} 个，"
          f"无法识别 {len(unknown)} 个", file=sys.stderr)


if __name__ == "__main__":
    main()