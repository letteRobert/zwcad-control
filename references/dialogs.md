# 命令对话框操作

使用当前已核实的 CadBridge 服务，先缓存 CAD 进程和窗口身份；只操作同一个 CAD 的命令弹窗。进入模态后不要同步读取 COM `app.HWND` / `ActiveDocument`，这些调用可能等待对话框关闭。

## 当前控件清单

命令已弹窗时先调用：

```json
{"command":"simulate_keys","action":"list","target":"dialog"}
```

核对目标标题、可见性、窗口归属，并记录响应中的当前 HWND。多个同名弹窗无法唯一确定时先定位，不选第一个窗口。后续优先使用 `target="hwnd=0x当前句柄"` 固定已观察目标；关闭或重开弹窗后重新取清单，不复用旧句柄、控件序号或坐标。

下列示例中 `0x123456` 只是占位值，必须替换为本轮窗口句柄。每次动作返回后检查结果，再决定下一步：

```json
{"command":"simulate_keys","target":"hwnd=0x123456","control":"edit[0]","action":"set_text","text":"设施用地"}
{"command":"simulate_keys","target":"hwnd=0x123456","control":"edit[0]","action":"get_text"}
{"command":"simulate_keys","target":"hwnd=0x123456","control":"checkbox[0]","action":"check"}
{"command":"simulate_keys","target":"hwnd=0x123456","control":"combo[0]","action":"get_items"}
{"command":"simulate_keys","target":"hwnd=0x123456","control":"combo[0]","action":"select","index":1}
{"command":"simulate_keys","target":"hwnd=0x123456","action":"click_default"}
```

列表序号从 0 开始。`Button` 包含普通按钮、复选框和单选框，不把第一个 Button 当复选框。支持 `edit[0]`、`checkbox[0]`、`radio[0]`、`combo[0]`、`list[0]`、`text=标签`、`id=当前ID` 等选择器；使用前核对其唯一性和当前清单。取消用 `click_cancel`，不假定取消按钮 ID=2。

## 键盘、鼠标及结果

- 控件直投优先于按键，可以在后台和模态框中工作；没有可识别控件时才转键盘或鼠标。
- `key="A",modifiers="CTRL"` 表示 Ctrl+A。不要无意添加 Shift；第三方全局快捷键可能接收明确发送的快捷键。
- 原始 SendKeys 字母输入受输入法模式影响。中文填写优先 `set_text`；测试或操作中切换输入法后恢复原模式，不把输入法组成态当插件成功。
- 鼠标仅操作已观察到的 CAD 窗口。150% 缩放时统一物理像素核对目标和真实指针，不能将逻辑坐标直接当屏幕像素。窗口状态改变后重新观察，不盲用旧坐标。
- 控件显示变化不等于命令完成。点确定后验证弹窗关闭、CAD 命令结束，以及目标文字、图元、设置或输出文件实际发生变化。特殊控件读回与业务结果不符时记录问题，不伪造回调文件。
- 用户停止或工具返回停止信号时停止当前交互。先记录已发生的修改；就绪文件、旧截图和接口“已发送”不能作为继续输入的授权。
