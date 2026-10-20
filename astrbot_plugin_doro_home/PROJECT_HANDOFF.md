# Doro QQ 群聊机器人项目交接文档

给新的 AI 对话或维护者使用。开始修改前先阅读本文件和 `README.md`。

## 项目目标

这是 Windows 上运行的 QQ 群机器人：QQ 小号 -> NapCat -> OneBot v11/aiocqhttp -> AstrBot 4.28.x -> Doro 和其他插件。Doro 的风格是可爱、抽象、理直气壮、偶尔发疯；普通闲聊要短，明确命令优先由插件处理，技术问题要清楚回答。

## 三个目录

- GitHub 唯一推荐开发源：`C:\git\astrbot_plugin_doro_home`
- 本地整理和同步中转：`C:\study_project\school\boot\DoroBot_Project\plugin-source`
- AstrBot 实际运行插件：`C:\Users\HUMAN\.astrbot\data\plugins\astrbot_plugin_doro_home`

当前同步脚本读取 `plugin-source`，不是直接读取 `C:\git`。不要同时修改两份源码。当前流程是：修改 Git 源码，复制到 `plugin-source`，运行同步脚本，再重启 AstrBot。

## 其他路径

- AstrBot 数据根目录：`C:\Users\HUMAN\.astrbot`
- 插件配置：`C:\Users\HUMAN\.astrbot\data\config`
- 插件运行数据：`C:\Users\HUMAN\.astrbot\data\plugin_data`
- Doro 数据库：`C:\Users\HUMAN\.astrbot\data\plugin_data\astrbot_plugin_doro_home\doro_home.db`
- Doro 结局图片：`C:\Users\HUMAN\.astrbot\data\plugins\astrbot_plugin_doro_today\doro`
- AstrBot 客户端：`C:\astrboot\QQ\AstrBot`
- NapCat/QQ：`C:\astrboot\QQ\NapCat`
- 不使用：`C:\astrboot\QQ\.astrbot`，不要手动创建或覆盖。

## 当前功能

命令包括：`/菜单`、`/今日`、`/图鉴`、`/运势`、`/随机表情包`、`/吃点啥`、`/吃什么`、`/菜谱搜索 <关键词>`、`/怎么做 <菜名>`、`/随机推荐 [数量]`、`/菜谱分类`、`/食谱帮助`、`/食谱统计`、`/重载食谱`、`/怪味菜单`、`/搬史`、`/帮助`、`/状态`。

- `/今日`：每群每用户每天抽一次 Doro 结局。
- `/图鉴`：按群、按用户记录收集种类和重复次数。
- `/运势`：调用现有今日运势插件。
- `/随机表情包`：从本地收藏随机发送图片。
- `/吃点啥`：使用 `content.py` 的本地菜谱，不访问外网 API。
- `/搬史`：手动从可信来源缓存转发一条消息。

## 关键文件

- `main.py`：命令、事件、菜单、图片、搬史和食谱。
- `content.py`：普通食物、怪味食物、`RECIPES` 和菜品简介。
- `storage.py`：SQLite 抽取、图鉴、重复次数、搬史缓存。
- `renderer.py`：菜单图和图鉴图。
- `_conf_schema.json`：插件配置。
- `metadata.yaml`：插件元数据。
- `assets/menu_background.jpg`：菜单背景，不能随意删除。

## 插件状态

建议保留：`astrbot_plugin_doro_home`、`astrbot_plugin_jrys`、`astrbot_plugin_parser`、`astrbot_plugin_qq_tools`、`astrbot_plugin_stealer`、`meme_manager`。

建议关闭：`astrbot_plugin_cook`、旧 `astrbot_plugin_doro_today`、`custom_menu`、`help_typst`、DIY/自动菜单、`astrbot_sowing_discord`。`self_learning` 和 `livingmemory` 不是核心功能，可能拖慢启动和干扰人格，默认关闭。

`astrbot_plugin_stealer` 负责收集和识别表情包；`meme_manager` 负责管理和语义匹配；Doro Home 负责随机发送。全局流式输出可以开启。若出现 `retcode=1200` 或 `sendMsg Timeout`，优先关闭 `meme_manager` 自动发图，只保留 `/随机表情包`。

## 标准开发流程

修改 `C:\git\astrbot_plugin_doro_home` -> 复制到 `C:\study_project\school\boot\DoroBot_Project\plugin-source` -> 关闭 AstrBot -> 双击 `C:\study_project\school\boot\DoroBot_Project\同步插件到AstrBot.bat` -> 启动 AstrBot -> 测试。

语法检查可使用 AstrBot 自带 Python：`cd C:\git\astrbot_plugin_doro_home`，然后执行 `& 'C:\Users\HUMAN\AppData\Local\AstrBot\backend\python\python.exe' -m py_compile main.py content.py storage.py renderer.py`。

GitHub 远程仓库：`https://github.com/HUMAN00000000/my_first_project.git`。提交流程：在 `C:\git` 执行 `git status`，确认后执行 `git add astrbot_plugin_doro_home`、`git commit -m "说明本次修改"`、`git push origin main`。网络失败时本地提交仍保留。

## 数据和安全规则

绝对不要删除、重置或覆盖 `C:\Users\HUMAN\.astrbot\data\plugin_data\astrbot_plugin_doro_home\doro_home.db`，否则会丢失图鉴和重复次数。

不要上传 `.astrbot`、`.runtime`、数据库、表情包运行数据、QQ/NapCat 登录文件、二维码、OneBot Token、DeepSeek API Key 或私人日志。不要使用 `git reset --hard`，不要覆盖用户未提交的修改。涉及删除、移动、重启、改配置或推送 GitHub，先说明影响并确认。

## 故障判断

- 完全不回复：检查 AstrBot、NapCat 登录和日志中的 `aiocqhttp(OneBot v11) 适配器已连接`。
- 菜谱 SSL 报错：关闭旧 `astrbot_plugin_cook`，使用本地菜谱。
- 表情包偶发失败：检查 `retcode=1200`，关闭 `meme_manager` 自动发图。
- 新代码不生效：确认已经从 `C:\git` 复制到 `plugin-source`，运行同步脚本并重启 AstrBot。

## 新对话开场提示

这是我的 AstrBot Doro QQ 群聊机器人项目。请先完整阅读 `C:\study_project\school\boot\DoroBot_Project\PROJECT_HANDOFF.md` 和 `C:\git\astrbot_plugin_doro_home\README.md`。请遵守其中的路径、数据库保护、插件冲突和 Git 规则。开始前先检查 Git 状态和相关文件，不要直接修改 AstrBot 运行目录，不要删除 `doro_home.db`，不要移动 `C:\Users\HUMAN\.astrbot`，不要上传密钥或 QQ 登录数据。如需修改，先说明改哪些文件，修改后做语法检查并说明同步和测试步骤。
