# UE Extract Material Params

虚幻引擎材质参数提取与可视化工具集。在虚幻引擎材质编辑器中全选所有节点（Ctrl+A）并复制（Ctrl+C），将剪贴板中的纯文本粘贴到本工具，即可生成结构化的参数统计报告或节点运算关系伪代码。

&gt; ⚠️ 虚幻材质资产本身是 `.uasset` 二进制文件，无法直接读取，必须通过编辑器复制节点获取纯文本内容。

## 功能特性

### 1. 参数提取与可视化（原有功能）
- **参数提取**：自动识别 Scalar、Vector4、Texture2D、StaticSwitch、Curve、CollectionParameter 等材质参数类型
- **分组展示**：按材质参数分组（Group）组织，未分组参数单独归类
- **参数统计**：统计各类型参数数量
- **剪贴板读取**：支持直接从剪贴板粘贴虚幻材质文本并生成报告（需通过本地服务器访问）
- **一键复制**：支持复制参数名、分组名到剪贴板
- **目录导航**：左侧目录栏支持点击跳转，自动高亮当前位置
- **中英双语**：支持中文 / English 一键切换

### 2. 节点运算关系提取（新增功能）
- **节点图解析**：从 UE 材质复制文本中解析所有 MaterialGraphNode 节点
- **运算关系追踪**：递归追踪节点输入连接，构建完整的运算树
- **分支节点处理**：正确处理 StaticSwitchParameter、StaticSwitch、Switch、Lerp、ShadingPathSwitch 等分支/选择节点
- **材质函数展开**：完整展开 MaterialFunctionCall 的输入输出关系
- **伪代码生成**：将节点连接关系转换为人类可读的伪代码，便于分析材质计算逻辑
- **NamedReroute 支持**：将 NamedRerouteDeclaration 提取为变量声明，使用时以变量名引用

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `extract_material_params.html` | **主文件**，浏览器打开即可使用，纯前端实现，无需后端。提供参数统计报告的可视化界面 |
| `extract_material_params.py` | Python 脚本版，支持批量处理由虚幻材质节点文本保存的 `.txt` 文件，输出 TXT / Markdown / HTML 三种格式 |
| `extract_material_math.py` | **新增脚本**，从同一来源的 UE 材质复制文本中提取节点运算关系，输出为伪代码（`.txt` 格式），便于分析材质计算逻辑 |
| `start_server.bat` | Windows 批处理脚本，一键启动本地 HTTP 服务器（解决浏览器剪贴板权限问题） |

## 使用方法

### 方法一：浏览器直接打开（参数统计）

1. 双击打开 `extract_material_params.html`
2. 在虚幻引擎 **材质编辑器** 中，按 **Ctrl+A** 全选所有节点，再按 **Ctrl+C** 复制
3. 将剪贴板中的文本粘贴到右侧「操作面板」的输入框中
4. 点击 **从输入栏中重新生成**，即可查看报告

&gt; 直接双击打开（ `file://` 协议）时，「粘贴并重新生成」按钮因浏览器安全限制无法自动读取剪贴板，需要在弹窗里允许浏览器查看剪切板的内容。

### 方法二：本地服务器启动（解锁剪贴板自动读取）

1. 确保已安装 Python 3
2. 双击运行 `start_server.bat`
3. 脚本会自动打开浏览器访问 `http://localhost:8080/extract_material_params.html`
4. 点击 **粘贴并重新生成**，浏览器可能会询问剪贴板权限，首次允许剪贴板权限后，后续不再弹窗

&gt; 终端窗口即为服务器进程，使用期间请勿关闭。

### 方法三：Python 脚本批量处理 — 参数统计

适用于需要批量处理历史保存的节点文本文件，生成参数统计报告。

```bash
# 1. 在虚幻材质编辑器中复制节点文本（Ctrl+A → Ctrl+C）
# 2. 粘贴到新建的空白 .txt 文件中保存
# 3. 将该 .txt 文件放入脚本同级目录

python extract_material_params.py

# 按提示选择文件 → 选择输出格式（TXT / Markdown / HTML）→ 完成