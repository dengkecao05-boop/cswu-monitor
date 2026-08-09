# 重庆城市管理职业大学新内容监控

这个小工具用于定时检查学校官方新媒体账号，只要发现新内容，就通过微信推送提醒你。

推荐组合：

- 内容来源：RSSHub 或其他能把平台内容转换成 RSS/Atom 的服务
- 去重监控：本文件夹里的 `monitor.py`
- 微信提醒：Server酱 Turbo，或 PushPlus
- 定时运行：Windows 任务计划程序

## 为什么用这种方式

微信公众号、视频号、抖音、微博的开放程度不一样：

- 微博：通常可以通过 RSSHub 的微博用户路由监控。
- 微信公众号：没有官方公开 RSS，常见做法是用 RSSHub 的新榜微信公众号路由，需要自建 RSSHub 并配置新榜 Cookie。
- 抖音：反爬较严格，RSSHub 路由通常需要 Puppeteer，建议自建 RSSHub 或使用稳定的第三方监控服务。
- 视频号：没有稳定公开网页订阅源，通常需要第三方监控服务、人工提供可订阅源，或用登录态自动化方案。

所以这里把“监控与通知”做成通用底座：只要某个平台能提供 RSS/Atom 地址，就能统一监控并微信提醒。

## 第一步：准备微信推送

### 方式 A：Server酱 Turbo

1. 打开 https://sct.ftqq.com
2. 用微信扫码登录。
3. 复制 SendKey。
4. 在系统环境变量里设置：

```powershell
$env:SERVERCHAN_SENDKEY="你的_SENDKEY"
```

Server酱 Turbo 免费会员通常每天有免费额度，适合个人提醒。

### 方式 B：PushPlus

1. 打开 https://www.pushplus.plus
2. 登录后复制 token。
3. 在系统环境变量里设置：

```powershell
$env:PUSHPLUS_TOKEN="你的_TOKEN"
```

## 第二步：配置监控源

复制配置模板：

```powershell
Copy-Item config.example.json config.json
```

然后编辑 `config.json`：

- `enabled: true` 表示启用这个来源。
- `url` 填 RSS/Atom 地址。
- `poll_limit` 表示每次最多检查几条。

默认模板里已经放入：

- 微博 UID：`2795108742`
- 微信公众号微信号：`cswucq`

抖音和视频号需要你先拿到可订阅源后再填入。

## 第三步：测试运行

```powershell
.\run_once.ps1
```

第一次运行只会记录已有内容，默认不会把历史内容全部推给你。之后发现新内容才推送。

如果想测试微信推送是否通：

```powershell
C:\Users\38956\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe monitor.py --config config.json --test-push
```

## 第四步：设置定时检查

推荐直接运行这个脚本。它会保存 Server酱 SendKey，并创建每 10 分钟运行一次的任务：

```powershell
.\setup_serverchan_10min.ps1
```

创建后，它会每 10 分钟检查一次；没有新内容不通知，发现新内容才通过微信通知。

如果你想手动创建任务，也可以使用：

```powershell
$TaskPath = (Resolve-Path .\run_once.ps1).Path
schtasks /Create /SC MINUTE /MO 10 /TN "CQC官方新内容监控" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File `"$TaskPath`"" /F
```

如果电脑关机，任务不会运行。想要 24 小时监控，可以把本文件夹放到云服务器、NAS、青龙面板或 GitHub Actions 上。

## 获取各平台源的建议

### 微博

可先使用：

```text
https://rsshub.app/weibo/user/2795108742
```

如果公共 RSSHub 不稳定，建议自建 RSSHub，然后把 `RSSHUB_BASE` 改为自建地址。

### 微信公众号

学校官方微信号可先按 `cswucq` 配置。RSSHub 新榜路由格式：

```text
https://你的-rsshub/newrank/wechat/cswucq
```

这个路由需要自建 RSSHub，并配置 `NEWRANK_COOKIE`。

### 抖音

RSSHub 抖音用户路由格式：

```text
https://你的-rsshub/douyin/user/抖音UID
```

抖音 UID 需要从账号主页分享链接或 RSSHub Radar 获取。抖音反爬严格，建议自建 RSSHub 并启用 Puppeteer。

### 视频号

视频号没有稳定公开 RSS。建议优先考虑：

- 第三方视频号监控服务提供的 RSS/Webhook。
- 已登录微信环境下的自动化监控。
- 如果学校把视频号内容同步到公众号、抖音或微博，可监控这些同步渠道作为近似替代。

## 文件说明

- `monitor.py`：监控和推送程序。
- `config.example.json`：配置模板。
- `run_once.ps1`：给 Windows 任务计划程序调用。
- `state.json`：自动生成，用来记录已提醒过的内容。
