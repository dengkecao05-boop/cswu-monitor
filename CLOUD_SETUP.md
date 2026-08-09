# 电脑关机也能自动监控的部署方法

要在电脑关机时仍然每 10 分钟检查一次，需要把监控器放到云端运行。这里推荐用 GitHub Actions：不需要买服务器，适合这种轻量定时检查。

## 你需要做一次的准备

1. 注册或登录 GitHub：https://github.com
2. 新建一个仓库，例如 `cqc-official-monitor`。
3. 把这个文件夹里的内容上传到仓库。
4. 打开仓库的 `Settings`。
5. 进入 `Secrets and variables` -> `Actions`。
6. 在 `Secrets` 里新增：

```text
Name: SERVERCHAN_SENDKEY
Value: 你的 Server酱 SendKey
```

7. 打开仓库的 `Actions` 页面，启用 workflows。
8. 找到 `Monitor official new content`，点 `Run workflow` 手动运行一次。

第一次运行只记录已有内容，不会把历史内容都推送给你。之后每 10 分钟自动检查，有新内容才微信通知。

## 定时频率

当前已经配置为每 10 分钟运行一次：

```text
*/10 * * * *
```

GitHub Actions 的定时任务不是秒级准时，实际可能延迟几分钟，但电脑关机不影响。

## 如果你使用自建 RSSHub

在 GitHub 仓库里进入：

```text
Settings -> Secrets and variables -> Actions -> Variables
```

新增：

```text
Name: RSSHUB_BASE
Value: https://你的-rsshub域名
```

然后在 `config.github.json` 里启用微信公众号、抖音等来源。

## 当前能直接运行的来源

目前 `config.github.json` 默认只启用了官方微博，因为它有公开 RSSHub 路由。

微信公众号、抖音号、视频号因为平台限制，需要你拿到可用 RSSHub/第三方订阅源后再启用。启用方法是在 `config.github.json` 中把对应来源的：

```json
"enabled": false
```

改成：

```json
"enabled": true
```
