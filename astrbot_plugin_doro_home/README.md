# Doro 小窝

一个面向 AstrBot 4.28.x、NapCat 和 OneBot v11 的 Doro 群聊插件。

## 安装

在 AstrBot 插件目录执行：

```powershell
git clone https://github.com/你的用户名/astrbot_plugin_doro_home.git
```

或者在 AstrBot 插件页面使用 GitHub 仓库地址安装。安装后重启 AstrBot，首次使用会自动创建本地数据库。

不要把 QQ 登录信息、DeepSeek API Key、`.runtime/` 或其他本地配置提交到仓库。

面向 AstrBot 4.28.x、NapCat 和 OneBot v11 的轻量整合插件。

## 功能

- 使用 Doro 壁纸生成静态菜单图片，不启动浏览器或 Typst 子进程。
- 每个群、每个 QQ 用户每天抽取一次 Doro 结局。
- 使用 SQLite 记录结局、重复次数和个人图鉴。
- 调用现有 `/jrys` 今日运势入口。
- 从“表情包小偷”的本地收藏随机发送图片。
- 提供稳定的本地“吃点啥”与怪味菜单，不依赖外网食谱 API。
- 支持菜谱搜索、简易做法、分类统计和多道随机推荐。
- 缓存指定来源群的消息 ID，由普通群友使用 `/搬史` 手动随机转发。
- 尝试发送 QQ 原生键盘；不支持时自动保留文字命令入口。

## 命令

```text
菜单
doro今日
doro图鉴
doro运势
随机表情包
吃点啥（吃什么兼容）
怪味菜单
菜谱搜索 <关键词>
怎么做 <菜名>
随机推荐 [数量]
菜谱分类
食谱帮助
食谱统计
重载食谱
搬史
doro帮助
doro状态
```

## 与旧插件的关系

安装并验证后建议关闭以下旧插件，避免同名命令重复响应：

- `astrbot_plugin_doro_today`
- `astrbot_plugin_custom_menu`
- `astrbot_plugin_help_typst`
- `astrbot_sowing_discord`（新插件接管手动搬史缓存后）

不要删除旧 Doro 插件目录，新插件默认从它的 `doro` 文件夹读取结局图片。

## 食谱说明

食谱数据内置在 `content.py`，所以不会因外部网站 SSL、DNS 或 API 故障拖慢 AstrBot。
当前是精简但可扩展的本地菜谱库；可以继续往 `RECIPES` 增加菜名、分类、关键词和做法。

今日运势和表情包小偷继续保持启用。
