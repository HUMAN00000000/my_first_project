# Doro QQ 群聊机器人：新对话交接文档

这是一份给新的 AI 对话使用的项目上下文。开始修改前先阅读本文件和 `README.md`。

## 项目目标

这是一个运行在 AstrBot 4.28.x + NapCat + OneBot v11 上的 QQ 群 Doro 小号插件。目标是提供 Doro 风格菜单、每日结局、个人图鉴、运势、随机表情包、本地食谱和手动搬史。

## 本机路径

- GitHub 本地仓库：`C:\git`
- GitHub 项目插件目录：`C:\git\astrbot_plugin_doro_home`
- 开发项目备份：`C:\study_project\school\boot\DoroBot_Project`
- AstrBot 实际数据目录：`C:\Users\HUMAN\.astrbot`
- AstrBot 实际插件目录：`C:\Users\HUMAN\.astrbot\data\plugins\astrbot_plugin_doro_home`
- Doro SQLite 数据：`C:\Users\HUMAN\.astrbot\data\plugin_data\astrbot_plugin_doro_home\doro_home.db`
- 插件配置目录：`C:\Users\HUMAN\.astrbot\data\config`
- AstrBot 客户端：`C:\astrboot\QQ\AstrBot`
- NapCat/QQ：`C:\astrboot\QQ\NapCat`

`C:\astrboot\QQ\.astrbot` 不使用；不要重新创建。AstrBot 数据已经恢复到 `C:\Users\HUMAN\.astrbot`。

## 当前功能

- `/菜单`：Doro 小窝菜单。
- `/今日`：每个群、每个 QQ 用户每天抽一次 Doro 结局。
- `/图鉴`：查看当前群内该用户收集的结局和重复次数。
- `/运势`：调用现有今日运势插件。
- `/随机表情包`：从表情包小偷的本地收藏随机发送图片。
- `/吃点啥`、`/吃什么`：本地离线菜谱和怪味菜单。
- `/菜谱搜索 <关键词>`、`/怎么做 <菜名>`、`/随机推荐 [数量]`、`/菜谱分类`。
- `/搬史`：从配置的来源群缓存中手动转发一条消息。
- `/帮助`、`/状态`：帮助和状态。
- QQ 原生键盘失败时会自动退回文字命令。

## 关键代码

- `main.py`：AstrBot 事件、命令、图片发送、菜单和食谱逻辑。
- `content.py`：普通食物、怪味食物、本地 `RECIPES` 和菜品简介。
- `storage.py`：SQLite 每日抽取、图鉴重复次数和搬史缓存。
- `renderer.py`：菜单图片和个人图鉴图片渲染。
- `_conf_schema.json`：插件配置项。
- `metadata.yaml`：AstrBot 插件元数据。

## 开发规则

1. 优先修改 Git 仓库中的源码：`C:\git\astrbot_plugin_doro_home`。
2. 修改后先做 Python 语法检查。
3. 需要让本机 AstrBot 生效时，把源码复制到实际插件目录，然后重启 AstrBot。
4. 不要删除或重置 `doro_home.db`，否则会丢失个人图鉴和重复次数。
5. 不要提交 QQ 账号、NapCat 登录文件、OneBot Token、DeepSeek API Key、`.astrbot`、`.runtime` 或表情包运行数据。
6. 不要重新启用已经产生冲突的旧插件：`astrbot_plugin_cook`、`astrbot_plugin_doro_today`、旧菜单插件和旧搬史插件。
7. `Self Learning`、`livingmemory` 等资源消耗较大的插件默认不参与 Doro 核心功能，除非用户明确要求。
8. 食谱必须优先使用本地数据，不要重新依赖 `cook.aiursoft.cn`，它曾导致 SSL 重试和启动变慢。
9. 全局流式输出可以保持开启；表情包自动发送失败时优先检查 `meme_manager` 的自动发送和 NapCat `retcode=1200` 超时。

## 发布流程

```powershell
cd C:\git
git add astrbot_plugin_doro_home
git commit -m "说明本次修改"
git push origin main
```

远程仓库：`https://github.com/HUMAN00000000/my_first_project.git`

## 给新 AI 的安全提示

先读取本文件、`README.md` 和相关源码，再修改。不要因为“整理目录”而移动 AstrBot 数据目录，不要删除数据库，不要直接覆盖配置。涉及删除、移动、重启或推送 GitHub 时，先向用户说明影响并确认。
