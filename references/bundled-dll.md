# 随附 DLL 的使用

插件目录相对于技能根目录为 `assets/zwcad2025/`：

- `CadBridge-Compat.Dev64.dll`：独立开发的插件快照，仅验证中望 CAD 2025 x64。
- `build-info.json`：DLL 文件名、SHA256、来源源码摘要及验收范围。随附文件按 `assembly_file` 在当前目录定位。
- `CadBridge.config.json`：当前副本的配置，默认端口 9879。没有复制项目测试日志路径或原版配置。

## 加载

1. 先按 `build-info.json` 核对随附 DLL 的 SHA256。只迁移副本，不覆盖 CAD 已加载的 DLL。
2. 检查配置端口。已有相同插件服务时核实实际加载路径；端口被其他服务占用时选空闲端口并修改本目录配置，不按端口猜服务身份。
3. 在用户要操作的中望 CAD 会话中执行 `NETLOAD`，选择本技能 `assets/zwcad2025/CadBridge-Compat.Dev64.dll`。用户已要求操作 CAD 即可连接该会话；不要为日常操作自动创建验收测试图。安全加载提示由用户处理，不修改安全配置。
4. 按配置端口读取 `/api/health` 和 `/api/diagnostics`。默认地址分别为 `http://127.0.0.1:9879/api/health` 和 `http://127.0.0.1:9879/api/diagnostics`。新加载时确认 `assemblyPath` 是当前技能内的文件路径，且磁盘摘要匹配；复用其他目录同一构建时比较实际文件与随附摘要并记录路径，不重复加载。可用 `python scripts/cad_bridge.py --port PORT check` 核对。

同名程序集已在当前进程加载时，重复 NETLOAD 不保证切换到技能副本。需要验证新位置时使用新的独立测试会话；不关闭用户图纸强制切换。

REST 命令入口为 `/api/execute`，MCP 入口为 `/api/mcp`，参数通过 `/api/help?command=工具名` 查询。插件本身不需要模型 API Key，不打开聊天设置侧栏，也不依赖 VS Code 或旧 TmAgent 插件。

Python 类工具仍需可用 Python。优先读取环境变量 `CADBRIDGE_PYTHON`，其次读取本目录配置的 `python` 字段；默认尝试本机 `C:/ProgramData/anaconda3/python.exe`，否则使用 PATH 中的 `python.exe`。迁移机器时按实际环境配置。中望 CAD 自身的托管程序集由宿主提供，不随技能复制其他 CAD 的 DLL。

## 验收范围

Dev64 增加只读结构化 `/api/query`，四类查询通过 17 项真实 CAD 用例；脚本 10 项单测、旧 REST/MCP 协议 12 项回归通过。测试服务的程序集路径、SHA256 与源码摘要已核实，记录见项目 `.cad-skill-update/structured-v3/native-live.json`。测试 CAD 因宿主启动机制驻留旧 Dev62 程序集，本次请求全部由已验证 Dev64 服务执行；不宣称纯净进程验收或 98 工具全部兼容。

已打开的 Dev62 会话通过 build-info.json 的精确 compatible_builds 哈希兼容，保留原 DLL；自动加载脚本已指向 Dev64，重启后核实 diagnostics.implementation 与 source=native。脚本不会自行关闭用户图纸或在当前会话热切换插件。完整源码与后续全套兼容验收仍在项目目录。
