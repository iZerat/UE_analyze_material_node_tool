#!/usr/bin/env python3
"""
虚幻材质参数提取工具
支持提取材质参数并输出为 TXT、Markdown 或 HTML 格式
"""

import re
import os
import glob
import sys
import html
from pathlib import Path
from datetime import datetime


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


def write_output_txt(parameters, output_file, input_filename):
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

    with open(output_file, 'w', encoding='utf-8') as f:
        # 文件头
        f.write("=" * 80 + "\n")
        f.write(f"{input_filename.replace('.txt', '')} 材质参数统计报告\n")
        f.write(f"源文件: {input_filename}\n")
        f.write(f"提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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


def write_output_md(parameters, output_file, input_filename):
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

    md_lines = []
    md_lines.append(f"# {input_filename.replace('.txt', '')} 材质参数统计报告")
    md_lines.append("")
    md_lines.append(f"> **源文件**: `{input_filename}` &nbsp;&nbsp;&nbsp;&nbsp;**提取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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


def write_output_html(parameters, output_file, input_filename):
    """将提取的参数写入 HTML 输出文件（左右分栏布局，目录宽度自适应）"""
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

    # 构建 HTML
    html_lines = []
    html_lines.append('<!DOCTYPE html>')
    html_lines.append('<html lang="zh-CN">')
    html_lines.append('<head>')
    html_lines.append('    <meta charset="UTF-8">')
    html_lines.append(f'    <title>{html.escape(input_filename)} 材质参数提取报告</title>')
    html_lines.append('    <style>')
    html_lines.append('''
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        html, body {
            height: 100%;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 16px;
            line-height: 1.6;
            color: #24292e;
            background-color: #fff;
        }
        /* 左右分栏主容器 */
        .main-layout {
            display: flex;
            height: 100vh;
            width: 100vw;
        }
        /* 左侧目录栏 - 宽度自适应最长字符串 */
        .sidebar {
            width: fit-content;
            min-width: 200px;
            max-width: 400px;
            height: 100vh;
            overflow-y: auto;
            overflow-x: hidden;
            background-color: #f6f8fa;
            border-right: 1px solid #e1e4e8;
            padding: 20px 16px;
            flex-shrink: 0;
        }
        .sidebar-title {
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e1e4e8;
            color: #1f2328;
        }
        .sidebar ul {
            list-style: none;
        }
        .sidebar li {
            margin-bottom: 4px;
        }
        .sidebar a {
            display: block;
            color: #24292e;
            text-decoration: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            transition: background-color 0.15s;
            white-space: nowrap;
        }
        .sidebar a:hover {
            background-color: #e1e4e8;
            color: #0969da;
        }
        .sidebar .group-item {
            font-weight: 500;
        }
        .sidebar .sub-item {
            padding-left: 16px;
            font-size: 0.85em;
            color: #57606a;
        }
        /* 右侧内容区 */
        .content {
            flex: 1;
            height: 100vh;
            overflow-y: auto;
            overflow-x: hidden;
            padding: 20px 40px;
        }
        .content-inner {
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            font-size: 2em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
            margin-bottom: 0.5em;
        }
        h2 {
            font-size: 1.5em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
            margin-top: 24px;
            margin-bottom: 16px;
        }
        h3 {
            font-size: 1.25em;
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
        }
        a {
            color: #0366d6;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        /* 统计表格 */
        .stats-table {
            border-collapse: collapse;
            width: auto;
            margin: 16px 0;
            min-width: 200px;
        }
        .stats-table th,
        .stats-table td {
            border: 1px solid #dfe2e5;
            padding: 8px 16px;
            text-align: left;
            white-space: nowrap;
        }
        .stats-table th {
            background-color: #f6f8fa;
            font-weight: 600;
        }
        .stats-table tr:nth-child(even) {
            background-color: #f8f8f8;
        }
        code {
            font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Code", monospace;
            font-size: 85%;
            background-color: #f6f8fa;
            padding: 0.2em 0.4em;
            border-radius: 3px;
        }
        .param-block {
            background-color: #f6f8fa;
            padding: 12px 16px;
            margin-bottom: 16px;
            border-radius: 6px;
        }
        .param-name {
            font-weight: 600;
            font-size: 1.1em;
            margin-bottom: 8px;
        }
        .param-name code {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 1em;
            background-color: #e1e4e8;
            padding: 0.2em 0.4em;
            border-radius: 3px;
        }
        .param-prop {
            margin-left: 0;
            margin-bottom: 4px;
            font-size: 0.95em;
            color: #24292e;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }
        .footer {
            font-size: 0.85em;
            color: #6a737d;
            text-align: center;
            margin-top: 40px;
            border-top: 1px solid #eaecef;
            padding-top: 20px;
        }
        /* 滚动条样式优化 */
        .sidebar::-webkit-scrollbar,
        .content::-webkit-scrollbar {
            width: 8px;
        }
        .sidebar::-webkit-scrollbar-track,
        .content::-webkit-scrollbar-track {
            background: transparent;
        }
        .sidebar::-webkit-scrollbar-thumb,
        .content::-webkit-scrollbar-thumb {
            background-color: #c1c1c1;
            border-radius: 4px;
        }
        .sidebar::-webkit-scrollbar-thumb:hover,
        .content::-webkit-scrollbar-thumb:hover {
            background-color: #a8a8a8;
        }
        @media (max-width: 768px) {
            .sidebar {
                min-width: 180px;
                max-width: 300px;
            }
            .content {
                padding: 10px 20px;
            }
        }
    ''')
    html_lines.append('    </style>')
    html_lines.append('</head>')
    html_lines.append('<body>')
    html_lines.append('<div class="main-layout">')

    # ===== 左侧目录栏 =====
    html_lines.append('    <div class="sidebar">')
    html_lines.append('        <div class="sidebar-title">目录</div>')
    html_lines.append('        <ul>')
    
    # 统计信息锚点
    html_lines.append('            <li class="group-item"><a href="#stats">参数统计</a></li>')
    
    # 各分组目录
    for group_name in sorted_groups:
        anchor = make_anchor(group_name)
        html_lines.append(f'            <li class="group-item"><a href="#{anchor}">{html.escape(group_name)}</a></li>')
    
    # 材质参数集
    if collection_params:
        html_lines.append('            <li class="group-item"><a href="#collection-params">材质参数集</a></li>')
    
    html_lines.append('        </ul>')
    html_lines.append('    </div>')

    # ===== 右侧内容区 =====
    html_lines.append('    <div class="content">')
    html_lines.append('        <div class="content-inner">')

    # 标题和源文件信息
    html_lines.append(f'<h1>{html.escape(input_filename.replace(".txt", ""))} 材质参数统计报告</h1>')
    html_lines.append(f'<p><strong>源文件</strong>: {html.escape(input_filename)}&nbsp;&nbsp;&nbsp;&nbsp;<strong>提取时间</strong>: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')

    # 统计表格
    html_lines.append('<h2 id="stats">参数统计</h2>')
    html_lines.append('<table class="stats-table">')
    html_lines.append('<thead>')
    html_lines.append('<tr>')
    html_lines.append('<th>类型</th>')
    html_lines.append('<th>数量</th>')
    html_lines.append('</tr>')
    html_lines.append('</thead>')
    html_lines.append('<tbody>')
    type_order = ['Scalar', 'Vector4', 'Texture2D', 'StaticSwitch', 'Curve', 'CollectionParameter']
    for t in type_order:
        if t in type_counts:
            html_lines.append('<tr>')
            html_lines.append(f'<td>{html.escape(t)}</td>')
            html_lines.append(f'<td>{type_counts[t]}</td>')
            html_lines.append('</tr>')
    for t, count in sorted(type_counts.items()):
        if t not in type_order:
            html_lines.append('<tr>')
            html_lines.append(f'<td>{html.escape(t)}</td>')
            html_lines.append(f'<td>{count}</td>')
            html_lines.append('</tr>')
    html_lines.append('<tr style="font-weight: bold; background-color: #f6f8fa;">')
    html_lines.append('<td>总计</td>')
    html_lines.append(f'<td>{total_count}</td>')
    html_lines.append('</tr>')
    html_lines.append('</tbody>')
    html_lines.append('</table>')
    html_lines.append('')

    # 各组详情
    for group_name in sorted_groups:
        anchor = make_anchor(group_name)
        html_lines.append(f'<h2 id="{anchor}">{html.escape(group_name)}</h2>')
        for param in groups[group_name]:
            html_lines.append('<div class="param-block">')
            html_lines.append(f'<div class="param-name"><code>{html.escape(param["name"])}</code></div>')
            html_lines.append(f'<div class="param-prop">类型: {html.escape(param["type"])}</div>')
            if param.get('description'):
                html_lines.append(f'<div class="param-prop">描述: {html.escape(param["description"])}</div>')
            if param.get('default') is not None:
                default_value = str(param["default"])
                if default_value.startswith("'") and default_value.endswith("'"):
                    default_value = default_value[1:-1]
                html_lines.append(f'<div class="param-prop">默认值: {html.escape(default_value)}</div>')
            if param.get('default_texture'):
                tex = param['default_texture']
                if "'" in tex:
                    tex = tex.split("'")[-2] if len(tex.split("'")) > 1 else tex
                html_lines.append(f'<div class="param-prop">默认贴图: {html.escape(tex)}</div>')
            if param.get('curve'):
                html_lines.append(f'<div class="param-prop">曲线资源: {html.escape(param["curve"])}</div>')
            if param.get('collection'):
                html_lines.append(f'<div class="param-prop">参数集: {html.escape(param["collection"])}</div>')
            if param.get('sort_priority') is not None:
                html_lines.append(f'<div class="param-prop">排序优先级: {param["sort_priority"]}</div>')
            html_lines.append('</div>')

    # 材质参数集
    if collection_params:
        html_lines.append('<h2 id="collection-params">材质参数集 (CollectionParameter)</h2>')
        for param in collection_params:
            html_lines.append('<div class="param-block">')
            html_lines.append(f'<div class="param-name"><code>{html.escape(param["name"])}</code></div>')
            html_lines.append(f'<div class="param-prop">类型: {html.escape(param["type"])}</div>')
            if param.get('description'):
                html_lines.append(f'<div class="param-prop">描述: {html.escape(param["description"])}</div>')
            if param.get('collection'):
                html_lines.append(f'<div class="param-prop">参数集: {html.escape(param["collection"])}</div>')
            if param.get('sort_priority') is not None:
                html_lines.append(f'<div class="param-prop">排序优先级: {param["sort_priority"]}</div>')
            html_lines.append('</div>')

    html_lines.append('<div class="footer">由材质参数提取工具生成</div>')
    html_lines.append('        </div>')
    html_lines.append('    </div>')
    html_lines.append('</div>')
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

    # 生成输出文件名
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    if output_format == 'txt':
        output_file = os.path.join(script_dir, f"{base_name}_params_extracted.txt")
    elif output_format == 'md':
        output_file = os.path.join(script_dir, f"{base_name}_params_extracted.md")
    else:  # html
        output_file = os.path.join(script_dir, f"{base_name}_params_extracted.html")

    # 检查是否覆盖
    if not check_overwrite(output_file):
        print("操作已取消")
        return

    print(f"\n正在读取文件: {os.path.basename(input_file)}")

    # 读取文件内容
    content = read_file_with_encoding(input_file)
    if content is None:
        print("错误: 无法读取文件，请检查文件编码")
        return

    print("正在提取参数...")
    parameters = extract_material_parameters(content)
    print(f"找到 {len(parameters)} 个参数")

    print(f"正在生成输出文件: {os.path.basename(output_file)}")

    # 根据格式输出
    if output_format == 'txt':
        write_output_txt(parameters, output_file, os.path.basename(input_file))
    elif output_format == 'md':
        write_output_md(parameters, output_file, os.path.basename(input_file))
    else:
        write_output_html(parameters, output_file, os.path.basename(input_file))

    print("\n" + "=" * 60)
    print("完成！")
    print(f"参数列表已保存到: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()