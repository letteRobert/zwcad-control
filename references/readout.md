# 图纸概况、文字与统计

用户要“读这张图、图里有什么、提取编号、统计图层图块”时使用。数据取自中望原生查询；截图用于判断排版、重叠和缺图，不用于数对象或抄文字。仅查询不保存或修改图纸。

## 汇总入口

在技能根目录执行，端口以配置为准：

```powershell
python scripts/cad_readout.py --port 9879 --out readout.json
```

`--plan` 只打印请求，不连接 CAD。`--text-limit 500` 调整单行与多行文字合计返回上限（默认合计 200，允许范围 1–10000）。已有输出文件不覆盖。入口复用 `cad_bridge.py` 的 DLL 身份校验，发出一个只读批次，不启动 CAD、不加载插件、不自动重试。

输出保留 `requests` 和 `native_response`，不假设不同版本返回字段相同，不自动把某个数组长度当作总数。`completeness=unverified` 是收集状态；退出码 0 表示结构化分项成功且图纸身份稳定；仍需检查各分项的 scope、truncated 和原始批次结果，不代表覆盖全部空间。首尾两次 `get_dwg_info` 用于核对目标图纸；不一致时舍弃该批统计，确认目标后重新查询。

输出版本为 `zwcad-readout/3`，保留 `text_limit_total`、`requests` 和 `native_response`，新增 `structured`、`success`、`document_id`、`document_stable` 和 `errors`。优先读取 `structured.texts/layers/blocks` 的明确字段；不要再从原始文字报告抄坐标和数行。重复传入 `--handle HEX` 可在 `structured.entities` 中取得指定对象属性。

需要额外参数或字段时先读实时 help，离线查 `tools.json`。本入口是现有接口的组合，不是新增 DLL 命令。

## 结构化查询接口

新版 Dev64 提供只读 `POST /api/query`，kind 仅允许 `texts`、`layers`、`blocks`、`entity`，不会执行绘图或修改命令。旧版 98 个工具、`/api/execute` 与 MCP 返回格式不变。调用示例：

```powershell
python scripts/cad_query.py texts --port 9879 --limit 200
python scripts/cad_query.py entity --port 9879 --handle 35E8
python scripts/cad_readout.py --port 9879 --handle 35E8 --out readout-v3.json
```

每项返回 `schema=zwcad-query/1`、`success`、`source`、`kind`、`document`、`scope`、`total`、`returned`、`truncated`、`items`、`errors`。失败的 total/truncated 为 null，不伪装为空结果；原生正常空查询是 success=true、total=0。`truncated` 只说明当前声明范围内是否受 limit 截断，不证明覆盖嵌套块或所有布局。错误数组含 code、message。原生 XYZ 坐标使用 position.x/y/z，保留双精度；MTEXT 同时保留纯文字 text 和格式原文 raw_text。

文字与图层图元计数使用当前空间的顶层对象；原生 document.space/space_handle 明确空间。图块列表是数据库中非布局、非匿名的命名块定义，entity_count 是定义内对象数，reference_count 是数据库直接插入引用数，不等于当前空间设备数量，也不自动合并动态匿名块。entity 查询可按整图句柄取得对象，owner_handle 指明实际归属空间或块。

Dev62 兼容：只有新路由明确返回 Unknown endpoint 时才启用回退。文字、图层、对象属性复用已有原生 JSON 诊断；图块使用严格解析与数量核对，并保留 raw 原文。source 标为 legacy-native 或 legacy-text-parser；旧版 MTEXT 的 text 是格式原文，text_format=mtext-contents，不冒充新接口纯文字。旧版逐节前后读取 CTAB/CVPORT 核对布局与视口，并跨节比较 space_key；空间名缺失用 null 明示，图块引用按旧接口范围说明，不与新版混加。其他原生错误不触发回退。兼容诊断可能一次返回该空间全部对象，大图优先重启切换 Dev64 的限量接口。

当前进程仍加载 Dev62 时，允许复用 build-info.json 中精确登记的兼容哈希；不自动加载旧 DLL。新启动脚本加载 Dev64，重启后查询 source 应为 native。默认端口使用实际配置。

## 报告顺序与证据

1. **目标**：图名/路径、当前空间和布局；无法确认的范围写“未确认”。图纸类型只能根据提取到的图名、标题和注记判断，并说明依据。
2. **概况**：图元总数及类型、图层数、坐标范围和单位；单位未确认时不换算米、平方米，不把包围盒面积当作地块面积。
3. **图层**：区分定义数、有对象的层数、关闭/冻结层；没有定义的计数口径不推断。隐藏层不等于空层，块内使用的层不能据模型空间直接对象数认定为空。
4. **图块**：分别说明块定义与插入引用次数，顶层与嵌套引用、外部参照、模型空间与布局；不得把定义数当构件数量。
5. **文字与编号**：内容、类型、图层、句柄、位置及出现次数（以实际字段为准）；缺失字段写未返回。完整文字和去重汇总分开保留，不能因去重丢失不同位置的重复编号。
6. **缺失与限制**：逐项查询失败、条数上限、未覆盖空间/对象、代理实体等；只确认已取得的内容，不宣称整图完整。

同一报告中的数字只能在目标图、空间、过滤条件和嵌套范围一致时相互比较。默认各接口空间范围未验证，不直接合并。

## 文字完整性

`find_text` 默认限制 30 条，`query_entities` 默认限制 50 条。返回条数达到请求上限时按可能截断处理；少于上限也不能单凭数组长度证明覆盖全图。冻结定义没有分页参数，不杜撰 offset/page。

用户要求“全部文字”时：确认接口是否支持所需空间、块内文字和属性；按图层或已确认范围分批查询，以“图纸+空间+句柄”去重。单一分组仍达到上限时继续细分，或明确报告未完整提取。TEXT/MTEXT 不自动覆盖 ATTRIB/ATTDEF、块内文字、尺寸显示文字或第三方对象；按实时帮助选择 `block_attr`、`get_entity` 或经用户任务授权的只读 Lisp 补取。模糊查找的匹配数与精确编号出现次数分开；精确重复检查应在取得完整结果后按原文匹配，不擅自清洗合并编号。

## 动态匿名块

只有原生接口确实返回有效块名/原始定义关联时，才将 `*U...` 实例归并到原始块名。保留原名、有效名、句柄、来源映射与归并次数；同一插入实例只计一次。先查 `block_query` / `get_entity` 的实时帮助和实际结果；现有接口不返回关联就标“来源未确认”，不能仅凭匿名名称猜测。表格、标注、填充生成的匿名块不自动当设备计数。

## 特殊对象、预览与工具选择

代理对象/天正对象能否显示和读取取决于中望环境及对象支持；成功打开不等于内容完整。保留已返回的类名、警告及未覆盖数量；没有检测结果就写未检查，不把天正图一律判成缺失或一律要求转 T3。

数据问题优先查接口；只有用户要看图或需检查外观时才缩放/截图。需要导出时按实时帮助选择实际支持的格式，不承诺本桥接已具备 CADViewer 的 PDF/SVG/JSON 等价导出。未启动 CAD 且只需读磁盘 DWG/DXF 时，可选已安装的 `cadviewer`；读取中望未保存的修改必须使用当前会话。两条路径的统计先统一范围再比较。

本流程借鉴 CADViewer 的结构化读图与统计口径，独立编写；未移植其 AGPL 源码。上游参考：https://github.com/NewbimAI/NewbimAI-CADViewer
