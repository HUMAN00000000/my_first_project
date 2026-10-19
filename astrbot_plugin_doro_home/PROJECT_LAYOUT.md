# Doro QQ 群聊机器人项目整理说明

## 目录职责

- `plugin-source/`：插件源码，后续开发只修改这里。
- `release/`：可上传 GitHub 的压缩包。
- `docs/`：部署和使用教程。
- `config-reference/`：插件配置参考，不保存 QQ 登录信息或 API 密钥。

## 当前运行路径

AstrBot 会从下面的目录加载插件，不能直接移动：

`C:\Users\HUMAN\.astrbot\data\plugins\astrbot_plugin_doro_home`

NapCat 和 AstrBot 客户端也继续使用原来的安装目录。修改源码后，将源码文件复制到上面的运行目录，再重启 AstrBot。

## 开发同步

```powershell
Copy-Item -LiteralPath .\plugin-source\* `
  -Destination 'C:\Users\HUMAN\.astrbot\data\plugins\astrbot_plugin_doro_home' `
  -Recurse -Force
```

不要复制 `.runtime/`、`__pycache__/` 或数据库到 GitHub。
