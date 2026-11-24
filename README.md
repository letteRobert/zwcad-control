# 中望 CAD 自动化 · ZWCAD Control for Codex

用自然语言操作正在运行的 **中望 CAD（ZWCAD 2025 x64）**。这个 Codex 技能通过本机 CadBridge 插件读取、绘制和编辑 DWG，适合日常制图、测绘宗地图和图纸信息提取。

A Windows Codex skill for ZWCAD 2025 x64. Read and edit DWG drawings, inspect layers and blocks, extract drawing text, and automate drafting through a local CadBridge REST or MCP interface.

## 可以做什么

| 用途 | 可以这样对 Codex 说 |
| --- | --- |
| DWG 读图与统计 | “读取当前图纸，列出图层、图块和界址点编号。” |
| 测绘制图与坐标定位 | “按给定尺寸画闭合宗地轮廓，把 J8 平移到指定的 CAD X、Y 坐标。” |
| CAD 绘图与编辑 | “画一条闭合多段线，放在指定图层，并添加面积注记。” |
| 图框、布局与标注 | “检查当前布局的图框和视口，列出缺失的标注。” |

## 安装与连接

需要 **Windows、中望 CAD 2025 x64 和 Codex**。使用命令行检查连接或导出时，需要可运行的 Python 3。

1. 下载或克隆本仓库，将整个 `zwcad-control` 文件夹放进 Codex 能识别的技能目录，例如项目下的 `.agents/skills/`。保留 [SKILL.md](SKILL.md)、`assets/`、`scripts/` 和 `references/` 的相对位置。
2. 在中望 CAD 打开目标图纸。按[桥接插件加载说明](references/bundled-dll.md)核对 DLL 的 SHA256，然后在 CAD 命令行输入 `NETLOAD`，选择 `assets/zwcad2025/CadBridge-Compat.Dev64.dll`。
3. 在技能目录中运行下面的命令，核对实际加载的插件和连接状态。配置改过端口时，用实际端口替换 `9879`。

```powershell
python scripts/cad_bridge.py --port 9879 check
```

连接成功后，先让 Codex “查看当前 DWG 的名称、单位和图层”，确认目标图纸，再发出绘图或编辑指令。CadBridge 本身不需要模型 API Key。

## 只读提取图纸信息

```powershell
python scripts/cad_readout.py --port 9879 --out readout.json
```

输出包含文字、图层和图块的结构化结果。查询范围和截断规则见[图纸读出说明](references/readout.md)。

当前随附的 Dev64 桥接组件在中望 CAD 2025 x64 上完成了文字、图层、图块和对象属性四类结构化查询的实机验证。其他 CAD 版本和全量命令兼容性以[构建记录](assets/zwcad2025/build-info.json)为准。

- [完整技能说明](SKILL.md)
- [参数化绘图示例](references/parametric-recipes.md)
- [图框与属性标题栏](references/frames-titleblocks.md)
