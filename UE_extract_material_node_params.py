#!/usr/bin/env python3
"""
虚幻材质参数提取工具
支持提取材质参数并输出为 TXT、Markdown 或 HTML 格式
"""

import re
import os
import glob
import sys
import html as html_module
from pathlib import Path
from datetime import datetime


def extract_material_name(input_text):
    """从虚幻材质文本中提取材质资产名称"""
    material_match = re.search(r'Material="[^"]*\.([A-Za-z0-9_]+)\'', input_text)
    if material_match:
        return material_match.group(1)
    return None


def extract_material_parameters(input_text):
    """
    从虚幻材质节点文本中提取参数信息
    支持: ScalarParameter, VectorParameter, TextureSampleParameter2D,
         StaticSwitchParameter, CurveAtlasRowParameter, CollectionParameter 等
    """
    parameters = []

    # 按行分割，逐行扫描
    lines = input_text.split('\n')
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i]

        # 查找包含 ParameterName 的行
        param_name_match = re.search(r'ParameterName="([^"]+)"', line)
        if param_name_match:
            param_name = param_name_match.group(1)

            # 找到当前参数节点的边界：向上找最近的 Begin Object，向下找对应的 End Object
            node_start = i
            node_end = i
            
            # 向上搜索最近的 Begin Object（最多回溯 100 行）
            for j in range(i, max(0, i-100), -1):
                if 'Begin Object Class=' in lines[j]:
                    node_start = j
                    break
            
            # 向下搜索对应的 End Object
            depth = 1  # 当前在 Begin Object 内，深度为 1
            for j in range(i+1, min(total_lines, i+200)):
                if 'Begin Object Class=' in lines[j]:
                    depth += 1
                elif 'End Object' in lines[j]:
                    depth -= 1
                    if depth == 0:
                        node_end = j
                        break
            
            # 向上查找类型（在节点开始行）
            param_type = "Unknown"
            class_match = re.search(r'Begin Object Class=([^\s]+)', lines[node_start])
            if class_match:
                full_class = class_match.group(1)
                if 'ScalarParameter' in full_class:
                    param_type = "Scalar"
                elif 'VectorParameter' in full_class:
                    param_type = "Vector4"
                elif 'TextureSampleParameter2D' in full_class:
                    param_type = "Texture2D"
                elif 'TextureObjectParameter' in full_class:
                    param_type = "Texture2D"
                elif 'StaticSwitchParameter' in full_class:
                    param_type = "StaticSwitch"
                elif 'CurveAtlasRowParameter' in full_class:
                    param_type = "Curve"
                elif 'CollectionParameter' in full_class:
                    param_type = "CollectionParameter"
                elif 'MaterialExpressionTransform' in full_class:
                    # 跳过非参数节点类型
                    param_type = "NonParameter"
                else:
                    param_type = "Other"
            
            # 只处理参数类型，跳过非参数节点
            if param_type in ["Unknown", "NonParameter", "Other"]:
                # 如果 type 是 Other 但不是已知的参数类型，跳过
                if param_type != "Other":
                    i += 1
                    continue
            
            # 在节点边界内搜索 Group（只搜当前节点内部）
            group = ""
            for k in range(node_start, node_end + 1):
                group_match = re.search(r'Group="([^"]*)"', lines[k])
                if group_match:
                    group = group_match.group(1)
                    break
            
            # 在节点边界内搜索 Desc
            description = ""
            for k in range(node_start, node_end + 1):
                desc_match = re.search(r'Desc="([^"]*)"', lines[k])
                if desc_match:
                    description = desc_match.group(1)
                    break
            
            # 在节点边界内搜索 SortPriority
            sort_priority = 32  # 默认值
            for k in range(node_start, node_end + 1):
                sort_match = re.search(r'SortPriority=(\d+)', lines[k])
                if sort_match:
                    sort_priority = int(sort_match.group(1))
                    break
            
            # 根据类型提取额外信息（节点边界内搜索）
            if param_type == "Scalar":
                default = "0.0"
                for k in range(node_start, node_end + 1):
                    default_match = re.search(r'DefaultValue=([\d.-]+)', lines[k])
                    if default_match:
                        default = default_match.group(1)
                        break
                param_data = {
                    'type': param_type,
                    'name': param_name,
                    'group': group,
                    'description': description,
                    'default': default
                }
                if sort_priority is not None:
                    param_data['sort_priority'] = sort_priority
                parameters.append(param_data)

            elif param_type == "Vector4":
                default = "(0,0,0,1)"
                for k in range(node_start, node_end + 1):
                    default_match = re.search(r'DefaultValue=\(R=([\d.]+),G=([\d.]+),B=([\d.]+),A=([\d.]+)\)', lines[k])
                    if default_match:
                        default = f"({default_match.group(1)}, {default_match.group(2)}, {default_match.group(3)}, {default_match.group(4)})"
                        break
                param_data = {
                    'type': param_type,
                    'name': param_name,
                    'group': group,
                    'description': description,
                    'default': default
                }
                if sort_priority is not None:
                    param_data['sort_priority'] = sort_priority
                parameters.append(param_data)

            elif param_type == "StaticSwitch":
                default = "false"
                for k in range(node_start, node_end + 1):
                    default_match = re.search(r'DefaultValue=(\w+)', lines[k])
                    if default_match:
                        default = default_match.group(1)
                        break
                param_data = {
                    'type': param_type,
                    'name': param_name,
                    'group': group,
                    'description': description,
                    'default': default
                }
                if sort_priority is not None:
                    param_data['sort_priority'] = sort_priority
                parameters.append(param_data)

            elif param_type == "Texture2D":
                texture = "None"
                for k in range(node_start, node_end + 1):
                    texture_match = re.search(r'Texture="([^"]+)"', lines[k])
                    if texture_match:
                        texture = texture_match.group(1)
                        break
                param_data = {
                    'type': param_type,
                    'name': param_name,
                    'group': group,
                    'description': description,
                    'default_texture': texture
                }
                if sort_priority is not None:
                    param_data['sort_priority'] = sort_priority
                parameters.append(param_data)

            elif param_type == "Curve":
                curve = "None"
                for k in range(node_start, node_end + 1):
                    curve_match = re.search(r'Curve="([^"]+)"', lines[k])
                    if curve_match:
                        curve = curve_match.group(1)
                        break
                param_data = {
                    'type': param_type,
                    'name': param_name,
                    'group': group,
                    'description': description,
                    'curve': curve
                }
                if sort_priority is not None:
                    param_data['sort_priority'] = sort_priority
                parameters.append(param_data)

            elif param_type == "CollectionParameter":
                collection = "Unknown"
                for k in range(node_start, node_end + 1):
                    collection_match = re.search(r'Collection="([^"]+)"', lines[k])
                    if collection_match:
                        collection = collection_match.group(1)
                        break
                param_data = {
                    'type': param_type,
                    'name': param_name,
                    'group': group,
                    'description': description,
                    'collection': collection
                }
                if sort_priority is not None:
                    param_data['sort_priority'] = sort_priority
                parameters.append(param_data)

        i += 1

    # 去重（同一个参数可能出现多次）
    seen = set()
    unique_params = []
    for p in parameters:
        key = (p['name'], p['type'])
        if key not in seen:
            seen.add(key)
            unique_params.append(p)

    return unique_params


def write_output_txt(parameters, output_file, input_filename, material_name):
    """将提取的参数写入 TXT 输出文件（统计信息前置）"""
    # 统计各类型数量
    type_counts = {}
    for param in parameters:
        type_counts[param['type']] = type_counts.get(param['type'], 0) + 1

    total_count = len(parameters)

    # 分离 CollectionParameter（材质参数集）和普通参数
    collection_params = [p for p in parameters if p['type'] == 'CollectionParameter']
    normal_params = [p for p in parameters if p['type'] != 'CollectionParameter']

    # 按分组排序，空分组（未分组）排在最先
    def sort_key(x):
        priority = x.get('sort_priority', 9999)
        # 空分组放在最前面
        is_empty_group = x['group'] == ""
        return (not is_empty_group, x['group'], priority, x['name'])

    normal_params.sort(key=sort_key)

    report_title = f"{material_name} 材质参数统计报告" if material_name else f"{input_filename.replace('.txt', '')} 材质参数统计报告"

    with open(output_file, 'w', encoding='utf-8') as f:
        # 文件头
        f.write("=" * 80 + "\n")
        f.write(f"{report_title}\n")
        f.write(f"源文件: {input_filename}\n")
        f.write(f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        # 统计信息（前置）
        f.write("统计信息:\n")
        f.write("-" * 40 + "\n")
        type_order = ['Scalar', 'Vector4', 'Texture2D', 'StaticSwitch', 'Curve', 'CollectionParameter']
        for t in type_order:
            if t in type_counts:
                f.write(f"  {t}: {type_counts[t]}\n")
        for t, count in sorted(type_counts.items()):
            if t not in type_order:
                f.write(f"  {t}: {count}\n")
        f.write(f"\n  总计: {total_count}\n")
        f.write("\n" + "=" * 80 + "\n\n")

        # 输出普通参数（按分组排序，空分组最先）
        current_group = None
        for param in normal_params:
            group_display = param['group'] if param['group'] else "未分组 (None)"
            
            if group_display != current_group:
                current_group = group_display
                f.write(f"\n{'=' * 60}\n")
                f.write(f"分组: {current_group}\n")
                f.write(f"{'=' * 60}\n")

            f.write(f"\n参数名: {param['name']}\n")
            f.write(f"类型: {param['type']}\n")

            if param.get('description'):
                f.write(f"描述: {param['description']}\n")

            if param.get('default') is not None:
                f.write(f"默认值: {param['default']}\n")
            if param.get('default_texture'):
                f.write(f"默认贴图: {param['default_texture']}\n")
            if param.get('curve'):
                f.write(f"曲线资源: {param['curve']}\n")
            if param.get('collection'):
                f.write(f"参数集: {param['collection']}\n")

            if param.get('sort_priority') is not None:
                f.write(f"排序优先级: {param['sort_priority']}\n")

        # 输出材质参数集（CollectionParameter）排最下面
        if collection_params:
            f.write(f"\n\n{'=' * 80}\n")
            f.write("材质参数集 (CollectionParameter)\n")
            f.write(f"{'=' * 80}\n")

            for param in collection_params:
                f.write(f"\n参数名: {param['name']}\n")
                f.write(f"类型: {param['type']}\n")

                if param.get('description'):
                    f.write(f"描述: {param['description']}\n")

                if param.get('collection'):
                    f.write(f"参数集: {param['collection']}\n")

                if param.get('sort_priority') is not None:
                    f.write(f"排序优先级: {param['sort_priority']}\n")


def write_output_md(parameters, output_file, input_filename, material_name):
    """将提取的参数写入 Markdown 输出文件"""
    # 统计各类型数量
    type_counts = {}
    for param in parameters:
        type_counts[param['type']] = type_counts.get(param['type'], 0) + 1

    total_count = len(parameters)

    # 分离 CollectionParameter 和普通参数
    collection_params = [p for p in parameters if p['type'] == 'CollectionParameter']
    normal_params = [p for p in parameters if p['type'] != 'CollectionParameter']

    # 按分组排序，空分组（未分组）排在最先
    def sort_key(x):
        priority = x.get('sort_priority', 9999)
        is_empty_group = x['group'] == ""
        return (not is_empty_group, x['group'], priority, x['name'])

    normal_params.sort(key=sort_key)

    # 收集普通参数分组信息
    groups = {}
    for param in normal_params:
        group_name = param['group'] if param['group'] else "未分组 (None)"
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(param)

    # 确保 "未分组 (None)" 在最前面
    sorted_groups = sorted(groups.keys(), key=lambda x: (x != "未分组 (None)", x))

    report_title = f"{material_name} 材质参数统计报告" if material_name else f"{input_filename.replace('.txt', '')} 材质参数统计报告"

    md_lines = []
    md_lines.append(f"# {report_title}")
    md_lines.append("")
    md_lines.append(f"> **源文件**: `{input_filename}` &nbsp;&nbsp;&nbsp;&nbsp;**生成日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append("")
    md_lines.append("## 参数统计")
    md_lines.append("")
    md_lines.append("| 类型 | 数量 |")
    md_lines.append("|------|------|")

    type_order = ['Scalar', 'Vector4', 'Texture2D', 'StaticSwitch', 'Curve', 'CollectionParameter']
    for t in type_order:
        if t in type_counts:
            md_lines.append(f"| {t} | {type_counts[t]} |")
    for t, count in sorted(type_counts.items()):
        if t not in type_order:
            md_lines.append(f"| {t} | {count} |")

    md_lines.append(f"| **总计** | **{total_count}** |")
    md_lines.append("")
    md_lines.append("## 目录")
    md_lines.append("")

    def readable_anchor(name):
        slug = name.lower()
        slug = slug.replace(' ', '-')
        slug = slug.replace('(', '')
        slug = slug.replace(')', '')
        slug = re.sub(r'[^\w\-]', '', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        return slug

    idx = 1
    for group_name in sorted_groups:
        anchor = readable_anchor(group_name)
        md_lines.append(f"{idx}. [{group_name}](#{anchor})")
        idx += 1

    if collection_params:
        anchor = readable_anchor("材质参数集")
        md_lines.append(f"{idx}. [材质参数集 (CollectionParameter)](#{anchor})")

    md_lines.append("")

    # 各分组详情（按排序后的分组顺序）
    for group_name in sorted_groups:
        anchor = readable_anchor(group_name)
        md_lines.append(f'<a name="{anchor}"></a>')
        md_lines.append("")
        md_lines.append(f"## {group_name}")
        md_lines.append("")

        for param in groups[group_name]:
            md_lines.append(f"### `{param['name']}`")
            md_lines.append("")

            props = []
            props.append(f"类型: {param['type']}")
            if param.get('description'):
                props.append(f"描述: {param['description']}")
            if param.get('default') is not None:
                props.append(f"默认值: {param['default']}")
            if param.get('default_texture'):
                tex = param['default_texture']
                if "'" in tex:
                    tex = tex.split("'")[-2] if len(tex.split("'")) > 1 else tex
                props.append(f"默认贴图: {tex}")
            if param.get('curve'):
                props.append(f"曲线资源: {param['curve']}")
            if param.get('collection'):
                props.append(f"参数集: {param['collection']}")
            if param.get('sort_priority') is not None:
                props.append(f"排序优先级: {param['sort_priority']}")

            for prop in props:
                md_lines.append(f"{prop}  ")

            md_lines.append("")

    # 材质参数集详情（排最下面）
    if collection_params:
        anchor = readable_anchor("材质参数集")
        md_lines.append(f'<a name="{anchor}"></a>')
        md_lines.append("")
        md_lines.append("## 材质参数集 (CollectionParameter)")
        md_lines.append("")

        for param in collection_params:
            md_lines.append(f"### `{param['name']}`")
            md_lines.append("")

            props = []
            props.append(f"类型: {param['type']}")
            if param.get('description'):
                props.append(f"描述: {param['description']}")
            if param.get('collection'):
                props.append(f"参数集: {param['collection']}")
            if param.get('sort_priority') is not None:
                props.append(f"排序优先级: {param['sort_priority']}")

            for prop in props:
                md_lines.append(f"{prop}  ")

            md_lines.append("")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))


def write_output_html(parameters, output_file, input_filename, material_name):
    """将提取的参数写入 HTML 输出文件（三栏布局，参考 extract_material_params.html 优化）"""
    # 统计各类型数量
    type_counts = {}
    for param in parameters:
        type_counts[param['type']] = type_counts.get(param['type'], 0) + 1

    total_count = len(parameters)

    # 分离 CollectionParameter 和普通参数
    collection_params = [p for p in parameters if p['type'] == 'CollectionParameter']
    normal_params = [p for p in parameters if p['type'] != 'CollectionParameter']

    # 按分组排序，空分组（未分组）排在最先
    def sort_key(x):
        priority = x.get('sort_priority', 9999)
        is_empty_group = x['group'] == ""
        return (not is_empty_group, x['group'], priority, x['name'])

    normal_params.sort(key=sort_key)

    # 收集普通参数分组信息
    groups = {}
    for param in normal_params:
        group_name = param['group'] if param['group'] else "未分组 (None)"
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(param)

    # 确保 "未分组 (None)" 在最前面
    sorted_groups = sorted(groups.keys(), key=lambda x: (x != "未分组 (None)", x))

    report_title = f"{material_name} 材质参数统计报告" if material_name else f"{input_filename.replace('.txt', '')} 材质参数统计报告"

    # 辅助函数：生成安全的锚点 ID
    def make_anchor(text):
        slug = text.lower()
        slug = slug.replace(' ', '-')
        slug = slug.replace('(', '')
        slug = slug.replace(')', '')
        slug = re.sub(r'[^\w\-]', '', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        return slug

    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 构建 HTML
    html_lines = []
    html_lines.append('<!DOCTYPE html>')
    html_lines.append('<html lang="zh-CN">')
    html_lines.append('<head>')
    html_lines.append('    <meta charset="UTF-8">')
    html_lines.append(f'    <title>{html_module.escape(report_title)}</title>')
    html_lines.append('    <style>')
    html_lines.append('''
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body {
            height: 100%; overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 16px; line-height: 1.6; color: #24292e; background-color: #fff;
        }
        .main-layout { display: flex; height: 100vh; width: 100vw; }
        .sidebar {
            width: 320px; min-width: 320px; height: 100vh;
            overflow-y: auto; overflow-x: hidden;
            background-color: #f6f8fa; border-right: 1px solid #e1e4e8;
            padding: 20px 16px; flex-shrink: 0; transition: width 0.2s ease;
        }
        .sidebar-title {
            font-size: 1.1em; font-weight: 600; margin-bottom: 12px;
            padding-bottom: 8px; border-bottom: 1px solid #e1e4e8; color: #1f2328;
        }
        .sidebar ul { list-style: none; }
        .sidebar li { margin-bottom: 4px; }
        .sidebar a {
            display: block; color: #24292e; text-decoration: none;
            padding: 4px 8px; border-radius: 4px; font-size: 0.9em;
            transition: background-color 0.15s; white-space: nowrap; cursor: pointer;
        }
        .sidebar a:hover { background-color: #e1e4e8; color: #0969da; }
        .sidebar .group-item { font-weight: 500; }
        .sidebar .toc-highlight {
            background-color: rgba(9, 105, 218, 0.12);
            transition: background-color 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .center-panel {
            flex: 1; height: 100vh; overflow-y: auto; overflow-x: hidden; position: relative;
        }
        .center-panel-inner { max-width: 900px; margin: 0 auto; width: 100%; padding: 20px 40px; }
        .right-panel {
            width: 320px; min-width: 320px; height: 100vh;
            overflow-y: auto; overflow-x: hidden;
            background-color: #f6f8fa; border-left: 1px solid #e1e4e8;
            padding: 20px 16px; flex-shrink: 0; display: flex; flex-direction: column;
        }
        .right-panel-section { margin-bottom: 20px; }
        .right-panel-label {
            font-size: 0.85em; font-weight: 600; color: #57606a;
            margin-bottom: 8px; letter-spacing: 0.5px;
        }
        .generate-date {
            font-size: 0.95em; color: #24292e;
            font-family: "SF Mono", "Monaco", "Consolas", monospace;
        }
        .divider { height: 1px; background-color: #e1e4e8; margin: 8px 0; }
        .quick-nav-section { margin-top: auto; padding-top: 16px; border-top: 1px solid #e1e4e8; }
        .quick-nav-buttons { display: flex; gap: 8px; }
        .btn-quick-nav {
            flex: 1; padding: 8px 12px; font-size: 0.85em; font-weight: 500;
            color: #24292e; background-color: #fff; border: 1px solid #d0d7de;
            border-radius: 6px; cursor: pointer; transition: all 0.15s; text-align: center;
        }
        .btn-quick-nav:hover { background-color: #f3f4f6; border-color: #b0b7bf; }
        .btn-quick-nav:active { background-color: #e1e4e8; }
        h1 {
            font-size: 2em; border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em; margin-bottom: 0.5em;
        }
        h2 {
            font-size: 1.5em; border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em; margin-top: 24px; margin-bottom: 16px;
            transition: background-color 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            border-radius: 4px; padding-left: 8px; padding-right: 8px;
            margin-left: -8px; margin-right: -8px;
            display: flex; align-items: center; gap: 12px; position: relative;
        }
        h2.highlight-scroll { background-color: rgba(9, 105, 218, 0.12); }
        a { color: #0366d6; text-decoration: none; }
        a:hover { text-decoration: underline; }
        code {
            font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Code", monospace;
            font-size: 85%; background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px;
        }
        .stats-table { border-collapse: collapse; width: 100%; margin: 8px 0; }
        .stats-table th, .stats-table td {
            border: 1px solid #dfe2e5; padding: 6px 10px; text-align: left; font-size: 0.9em;
        }
        .stats-table th { background-color: #fff; font-weight: 600; }
        .stats-table tr:nth-child(even) { background-color: #fff; }
        .stats-table tr:last-child { font-weight: bold; background-color: #e1e4e8; }
        .param-block {
            background-color: #f6f8fa; padding: 12px 16px;
            margin-bottom: 16px; border-radius: 6px;
        }
        .param-header { display: flex; align-items: center; margin-bottom: 8px; gap: 12px; }
        .param-name {
            font-weight: 600; font-size: 1.1em; word-break: break-all;
        }
        .param-name code {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 1em; background-color: #e1e4e8; padding: 0.2em 0.4em; border-radius: 3px;
        }
        .btn-copy {
            padding: 4px 12px; font-size: 0.8em; font-weight: 500; color: #57606a;
            background-color: #e1e4e8; border: 1px solid #d0d7de; border-radius: 4px;
            cursor: pointer; transition: background-color 0.15s, color 0.15s, border-color 0.15s;
            flex-shrink: 0; width: fit-content; min-width: 100px; text-align: center; white-space: nowrap;
        }
        .btn-copy:hover { background-color: #d0d7de; color: #24292e; }
        .btn-copy:active { background-color: #c1c1c1; }
        .btn-copy.copied { background-color: #2da44e; color: #fff; border-color: #2da44e; }
        .btn-copy.copied:hover { background-color: #2da44e; color: #fff; border-color: #2da44e; }
        .group-actions { display: flex; gap: 8px; align-items: center; font-size: 1rem; }
        .group-info {
            font-size: 0.95em; font-weight: 500; color: #57606a;
            margin-bottom: 12px; margin-top: -8px; padding-left: 8px;
        }
        .btn-group-action {
            padding: 4px 12px; font-size: 0.8em; font-weight: 500; color: #57606a;
            background-color: #e1e4e8; border: 1px solid #d0d7de; border-radius: 4px;
            cursor: pointer; transition: background-color 0.15s, color 0.15s, border-color 0.15s;
            flex-shrink: 0; width: fit-content; min-width: 110px; text-align: center; white-space: nowrap;
        }
        .btn-group-action.copied { background-color: #2da44e; color: #fff; border-color: #2da44e; }
        .btn-group-action.copied:hover { background-color: #2da44e; color: #fff; border-color: #2da44e; }
        .btn-group-action:hover { background-color: #d0d7de; color: #24292e; }
        .btn-group-action:active { background-color: #c1c1c1; }
        .param-prop {
            margin-left: 0; margin-bottom: 4px; font-size: 0.95em; color: #24292e;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }
        .footer {
            font-size: 0.85em; color: #6a737d; text-align: center;
            margin-top: 40px; border-top: 1px solid #eaecef; padding-top: 20px;
        }
        .sidebar::-webkit-scrollbar, .center-panel::-webkit-scrollbar, .right-panel::-webkit-scrollbar { width: 8px; }
        .sidebar::-webkit-scrollbar-track, .center-panel::-webkit-scrollbar-track, .right-panel::-webkit-scrollbar-track { background: transparent; }
        .sidebar::-webkit-scrollbar-thumb, .center-panel::-webkit-scrollbar-thumb, .right-panel::-webkit-scrollbar-thumb { background-color: #c1c1c1; border-radius: 4px; }
        .sidebar::-webkit-scrollbar-thumb:hover, .center-panel::-webkit-scrollbar-thumb:hover, .right-panel::-webkit-scrollbar-thumb:hover { background-color: #a8a8a8; }
    ''')
    html_lines.append('    </style>')
    html_lines.append('</head>')
    html_lines.append('<body>')
    html_lines.append('<div class="main-layout">')

    # ===== 左侧目录栏 =====
    html_lines.append('    <div class="sidebar" id="sidebar">')
    html_lines.append('        <div class="sidebar-title">目录</div>')
    html_lines.append('        <ul id="toc-list">')
    
    # 各分组目录
    for group_name in sorted_groups:
        anchor = make_anchor(group_name)
        html_lines.append(f'            <li class="group-item"><a onclick="scrollToSection(\'{anchor}\')">{html_module.escape(group_name)}</a></li>')
    
    # 材质参数集
    if collection_params:
        html_lines.append('            <li class="group-item"><a onclick="scrollToSection(\'collection-params\')">材质参数集</a></li>')
    
    html_lines.append('        </ul>')
    html_lines.append('    </div>')

    # ===== 中间主内容区域 =====
    html_lines.append('    <div class="center-panel" id="center-panel">')
    html_lines.append('        <div class="center-panel-inner">')

    # 标题（中间区域不再放源文件和生成日期）
    html_lines.append(f'<h1>{html_module.escape(report_title)}</h1>')

    # 各组详情
    for group_name in sorted_groups:
        anchor = make_anchor(group_name)
        group_param_count = len(groups[group_name])
        is_ungrouped = group_name == "未分组 (None)"
        html_lines.append(f'<h2 id="{anchor}">{html_module.escape(group_name)}')
        html_lines.append(f'<span class="group-actions">')
        if not is_ungrouped:
            html_lines.append(f'<button class="btn-group-action" onclick="copyGroupName(\'{html_module.escape(group_name)}\', this)">复制分组名</button>')
        html_lines.append(f'<button class="btn-group-action" onclick="locateInToc(\'{anchor}\')">在目录中定位</button>')
        html_lines.append(f'</span></h2>')
        if is_ungrouped:
            html_lines.append(f'<div class="group-info">有 {group_param_count} 个参数未分组</div>')
        else:
            html_lines.append(f'<div class="group-info">分组包括 {group_param_count} 个参数</div>')

        for param in groups[group_name]:
            html_lines.append('<div class="param-block">')
            html_lines.append('<div class="param-header">')
            html_lines.append(f'<div class="param-name"><code>{html_module.escape(param["name"])}</code></div>')
            html_lines.append(f'<button class="btn-copy" onclick="copyParamName(\'{html_module.escape(param["name"])}\', this)">复制参数名</button>')
            html_lines.append('</div>')
            html_lines.append(f'<div class="param-prop">类型: {html_module.escape(param["type"])}</div>')
            if param.get('description'):
                html_lines.append(f'<div class="param-prop">描述: {html_module.escape(param["description"])}</div>')
            if param.get('default') is not None:
                dv = str(param["default"])
                if dv.startswith("'") and dv.endswith("'"):
                    dv = dv[1:-1]
                html_lines.append(f'<div class="param-prop">默认值: {html_module.escape(dv)}</div>')
            if param.get('default_texture'):
                tex = param['default_texture']
                if "'" in tex:
                    tex = tex.split("'")[-2] if len(tex.split("'")) > 1 else tex
                html_lines.append(f'<div class="param-prop">默认贴图: {html_module.escape(tex)}</div>')
            if param.get('curve'):
                html_lines.append(f'<div class="param-prop">曲线资源: {html_module.escape(param["curve"])}</div>')
            if param.get('collection'):
                html_lines.append(f'<div class="param-prop">参数集: {html_module.escape(param["collection"])}</div>')
            if param.get('sort_priority') is not None:
                html_lines.append(f'<div class="param-prop">排序优先级: {param["sort_priority"]}</div>')
            html_lines.append('</div>')

    # 材质参数集
    if collection_params:
        html_lines.append('<h2 id="collection-params">材质参数集</h2>')
        for param in collection_params:
            html_lines.append('<div class="param-block">')
            html_lines.append('<div class="param-header">')
            html_lines.append(f'<div class="param-name"><code>{html_module.escape(param["name"])}</code></div>')
            html_lines.append(f'<button class="btn-copy" onclick="copyParamName(\'{html_module.escape(param["name"])}\', this)">复制参数名</button>')
            html_lines.append('</div>')
            html_lines.append(f'<div class="param-prop">类型: {html_module.escape(param["type"])}</div>')
            if param.get('description'):
                html_lines.append(f'<div class="param-prop">描述: {html_module.escape(param["description"])}</div>')
            if param.get('collection'):
                html_lines.append(f'<div class="param-prop">参数集: {html_module.escape(param["collection"])}</div>')
            if param.get('sort_priority') is not None:
                html_lines.append(f'<div class="param-prop">排序优先级: {param["sort_priority"]}</div>')
            html_lines.append('</div>')

    html_lines.append('<div class="footer">由材质参数提取工具生成</div>')
    html_lines.append('        </div>')
    html_lines.append('    </div>')

    # ===== 右侧信息面板（无"信息面板"标题，源文件在最上面） =====
    html_lines.append('    <div class="right-panel" id="right-panel">')
    
    # 源文件
    html_lines.append('        <div class="right-panel-section" id="source-section">')
    html_lines.append('            <div class="right-panel-label">源文件</div>')
    html_lines.append(f'            <div class="generate-date">{html_module.escape(input_filename)}</div>')
    html_lines.append('        </div>')
    
    html_lines.append('        <div class="divider"></div>')
    
    # 生成日期
    html_lines.append('        <div class="right-panel-section" id="date-section">')
    html_lines.append('            <div class="right-panel-label">生成日期</div>')
    html_lines.append(f'            <div class="generate-date">{gen_time}</div>')
    html_lines.append('        </div>')

    html_lines.append('        <div class="divider"></div>')

    # 参数统计表格
    html_lines.append('        <div class="right-panel-section" id="stats-section">')
    html_lines.append('            <div class="right-panel-label">参数统计</div>')
    html_lines.append('            <table class="stats-table" id="right-stats-table">')
    html_lines.append('                <thead><tr><th>类型</th><th>数量</th></tr></thead>')
    html_lines.append('                <tbody>')
    type_order = ['Scalar', 'Vector4', 'Texture2D', 'StaticSwitch', 'Curve', 'CollectionParameter']
    for t in type_order:
        if t in type_counts:
            html_lines.append(f'                    <tr><td>{html_module.escape(t)}</td><td>{type_counts[t]}</td></tr>')
    for t, count in sorted(type_counts.items()):
        if t not in type_order:
            html_lines.append(f'                    <tr><td>{html_module.escape(t)}</td><td>{count}</td></tr>')
    html_lines.append(f'                    <tr><td><strong>总计</strong></td><td><strong>{total_count}</strong></td></tr>')
    html_lines.append('                </tbody>')
    html_lines.append('            </table>')
    html_lines.append('        </div>')

    # 快速跳转按钮
    html_lines.append('        <div class="quick-nav-section" id="quick-nav-section">')
    html_lines.append('            <div class="quick-nav-buttons">')
    html_lines.append('                <button class="btn-quick-nav" onclick="scrollToTop()">到顶部</button>')
    html_lines.append('                <button class="btn-quick-nav" onclick="scrollToBottom()">到底部</button>')
    html_lines.append('            </div>')
    html_lines.append('        </div>')

    html_lines.append('    </div>')
    html_lines.append('</div>')

    html_lines.append('<script>')
    html_lines.append('''
    // 动态调整目录宽度以匹配最长分组名
    function adjustSidebarWidth() {
        const sidebar = document.querySelector('.sidebar');
        const tocItems = document.querySelectorAll('#toc-list a');
        if (tocItems.length === 0) return;
        
        const measureEl = document.createElement('div');
        measureEl.style.cssText = 'position:fixed;visibility:hidden;white-space:nowrap;font-size:0.9em;font-weight:500;font-family:inherit;padding:4px 8px;';
        document.body.appendChild(measureEl);
        
        let maxWidth = 0;
        tocItems.forEach(item => {
            measureEl.textContent = item.textContent;
            const w = measureEl.offsetWidth;
            if (w > maxWidth) maxWidth = w;
        });
        
        document.body.removeChild(measureEl);
        
        // 加上 sidebar 的 padding (16px * 2) + 滚动条预留 (12px) + 一点边距 (8px)
        const newWidth = Math.max(320, maxWidth + 16 * 2 + 12 + 8);
        sidebar.style.width = newWidth + 'px';
        sidebar.style.minWidth = newWidth + 'px';
    }
    
    // 页面加载完成后调整目录宽度
    window.addEventListener('load', adjustSidebarWidth);

    async function copyParamName(name, btnElement) {
        try {
            await navigator.clipboard.writeText(name);
            btnElement.textContent = "已复制";
            btnElement.classList.add("copied");
            setTimeout(() => { btnElement.textContent = "复制参数名"; btnElement.classList.remove("copied"); }, 1500);
        } catch (err) {
            const textarea = document.createElement("textarea");
            textarea.value = name; textarea.style.position = "fixed"; textarea.style.opacity = "0";
            document.body.appendChild(textarea); textarea.select(); document.execCommand("copy"); document.body.removeChild(textarea);
            btnElement.textContent = "已复制"; btnElement.classList.add("copied");
            setTimeout(() => { btnElement.textContent = "复制参数名"; btnElement.classList.remove("copied"); }, 1500);
        }
    }
    async function copyGroupName(name, btnElement) {
        try {
            await navigator.clipboard.writeText(name);
            btnElement.textContent = "已复制";
            btnElement.classList.add("copied");
            setTimeout(() => { btnElement.textContent = "复制分组名"; btnElement.classList.remove("copied"); }, 1500);
        } catch (err) {
            const textarea = document.createElement("textarea");
            textarea.value = name; textarea.style.position = "fixed"; textarea.style.opacity = "0";
            document.body.appendChild(textarea); textarea.select(); document.execCommand("copy"); document.body.removeChild(textarea);
            btnElement.textContent = "已复制"; btnElement.classList.add("copied");
            setTimeout(() => { btnElement.textContent = "复制分组名"; btnElement.classList.remove("copied"); }, 1500);
        }
    }
    function highlightHeading(el) {
        el.classList.add("highlight-scroll");
        setTimeout(() => { el.classList.remove("highlight-scroll"); }, 1200);
    }
    function locateInToc(anchor) {
        const tocItems = document.querySelectorAll("#toc-list a");
        tocItems.forEach(item => { item.classList.remove("toc-highlight"); });
        const tocItem = Array.from(tocItems).find(item => {
            const onclick = item.getAttribute("onclick") || "";
            return onclick.includes("'" + anchor + "'");
        });
        if (tocItem) {
            tocItem.classList.add("toc-highlight");
            setTimeout(() => { tocItem.classList.remove("toc-highlight"); }, 2000);
            const sidebar = document.getElementById("sidebar");
            const itemTop = tocItem.offsetTop;
            const sidebarHeight = sidebar.clientHeight;
            const scrollTarget = itemTop - sidebarHeight / 2 + tocItem.clientHeight / 2;
            sidebar.scrollTo({ top: Math.max(0, scrollTarget) });
        }
    }
    function scrollToTop() { document.getElementById("center-panel").scrollTo({ top: 0 }); }
    function scrollToBottom() { const panel = document.getElementById("center-panel"); panel.scrollTo({ top: panel.scrollHeight }); }
    function scrollToSection(id) {
        const el = document.getElementById(id);
        if (el) { el.scrollIntoView({ block: "start" }); highlightHeading(el); }
    }
    ''')
    html_lines.append('</script>')
    html_lines.append('</body>')
    html_lines.append('</html>')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(html_lines))


def find_txt_files(directory):
    """查找当前目录下的所有.txt文件"""
    all_txt_files = glob.glob(os.path.join(directory, "*.txt"))
    return sorted(all_txt_files)


def select_file(txt_files):
    """让用户选择要处理的文件（编号从1开始）"""
    print("\n" + "=" * 60)
    print("找到以下 .txt 文件:")
    print("=" * 60)

    for i, filepath in enumerate(txt_files, start=1):
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        size_kb = file_size / 1024
        print(f"  [{i}] {filename} ({size_kb:.1f} KB)")

    if len(txt_files) > 9:
        print(f"\n提示: 共有 {len(txt_files)} 个文件，请输入对应的编号")

    while True:
        try:
            choice = input(f"\n请输入要处理的文件编号 [1-{len(txt_files)}]: ").strip()
            if not choice:
                print("请输入编号")
                continue
            idx = int(choice)
            if 1 <= idx <= len(txt_files):
                return txt_files[idx - 1]
            else:
                print(f"编号超出范围，请输入 1 到 {len(txt_files)} 之间的数字")
        except ValueError:
            print("输入无效，请输入数字编号")
        except KeyboardInterrupt:
            print("\n已取消")
            return None


def select_output_format():
    """询问用户输出格式（新增HTML选项）"""
    print("\n" + "=" * 60)
    print("请选择输出格式:")
    print("=" * 60)
    print("  [1] TXT 格式（纯文本）")
    print("  [2] Markdown 格式（.md）")
    print("  [3] HTML 格式（.html）")

    while True:
        try:
            choice = input("\n请输入选择 [1,2,3]: ").strip()
            if choice == '1':
                return 'txt'
            elif choice == '2':
                return 'md'
            elif choice == '3':
                return 'html'
            else:
                print("请输入 1、2 或 3")
        except KeyboardInterrupt:
            print("\n已取消")
            return None


def check_overwrite(filepath):
    """检查文件是否存在，询问是否覆盖"""
    if os.path.exists(filepath):
        print(f"\n文件已存在: {os.path.basename(filepath)}")
        while True:
            choice = input("是否覆盖？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                return True
            elif choice in ['n', 'no', '否', '']:
                return False
            else:
                print("请输入 y 或 n")
    return True


def read_file_with_encoding(filepath):
    """尝试多种编码读取文件"""
    for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"使用编码: {encoding}")
            return content
        except UnicodeDecodeError:
            continue
    return None


def main():
    """主函数"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 查找所有.txt文件
    txt_files = find_txt_files(script_dir)

    if not txt_files:
        print("错误: 当前目录下没有找到任何 .txt 文件")
        return

    # 让用户选择文件
    input_file = select_file(txt_files)
    if input_file is None:
        return

    # 询问输出格式
    output_format = select_output_format()
    if output_format is None:
        return

    # 读取文件内容（先读取以提取材质名称）
    print(f"\n正在读取文件: {os.path.basename(input_file)}")
    content = read_file_with_encoding(input_file)
    if content is None:
        print("错误: 无法读取文件，请检查文件编码")
        return

    # 提取材质名称
    material_name = extract_material_name(content)
    if material_name:
        print(f"检测到材质名称: {material_name}")
    else:
        print("未检测到材质名称，将使用文件名作为报告标题")

    # 生成输出文件名（以材质名称为准）
    if material_name:
        output_base = material_name
    else:
        output_base = os.path.splitext(os.path.basename(input_file))[0]

    if output_format == 'txt':
        output_file = os.path.join(script_dir, f"{output_base}_material_parameter_report.txt")
    elif output_format == 'md':
        output_file = os.path.join(script_dir, f"{output_base}_material_parameter_report.md")
    else:  # html
        output_file = os.path.join(script_dir, f"{output_base}_material_parameter_report.html")

    # 检查是否覆盖
    if not check_overwrite(output_file):
        print("操作已取消")
        return

    print("正在提取参数...")
    parameters = extract_material_parameters(content)
    print(f"找到 {len(parameters)} 个参数")

    print(f"正在生成输出文件: {os.path.basename(output_file)}")

    # 根据格式输出
    if output_format == 'txt':
        write_output_txt(parameters, output_file, os.path.basename(input_file), material_name)
    elif output_format == 'md':
        write_output_md(parameters, output_file, os.path.basename(input_file), material_name)
    else:
        write_output_html(parameters, output_file, os.path.basename(input_file), material_name)

    print("\n" + "=" * 60)
    print("完成！")
    print(f"参数列表已保存到: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()