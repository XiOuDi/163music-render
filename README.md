# 🎵 网易云音乐 Telegram Bot — Render 部署版

[![Release](https://img.shields.io/github/v/release/XiOuDi/163music-render?label=Release)](https://github.com/XiOuDi/163music-render/releases)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Render](https://img.shields.io/badge/Deploy-Render-46e3b9)](https://render.com/)

部署在 [Render](https://render.com/) 上的网易云音乐 Telegram Bot。**音频由 Render 服务器直接转发**：服务器从网易云下载 → 写入 ID3 标签与封面 → 上传 Telegram → 删除临时文件。使用 Upstash Redis 持久化配置与缓存。

---

## ✨ 功能特性

- 🔍 搜索、播放网易云音乐（`/play` 命令 + 内联搜索 `@XiOuDi163_bot`）
- 🔢 支持歌曲数字 ID 直接搜索/播放
- 📦 file_id 缓存：已发送过的音频秒发，零下载流量
- 🏷️ ID3 标签嵌入（标题、艺术家、专辑、封面），并自动校验/修复错误标题
- 📋 歌单播放（仅私聊）：支持队列排队、分批加载（超 1000 首分批）、5 秒去重、断点续播
- 🎧 用户播放后自动缓存同名歌曲的其他版本（前 20 首），队列与进度持久化到 Upstash
- ⏰ 每日 0 点 / 12 点自动刷新闲时缓存歌单
- 👮 管理员功能：开关歌单、缓存管理、Cookie 管理、封禁、广播、统计等
- 🧵 完整支持话题群组：在对应话题内回复，其他成员点击结果也不会串话题
- 💾 Upstash Redis 持久化（file_id、Cookie、歌单进度、开关状态、配置）
- ☁️ Render Webhook 模式，音频全部由服务器转发，不依赖 CF/Netlify 等外部代理

---

## 🧭 音频转发架构

```
用户点歌
  │
  ├─ 有 file_id 缓存 ──► 直接用 file_id 发送（秒发，零流量）
  │
  └─ 无缓存
        │
        ▼
   Render 服务器向网易云请求播放地址
        │
        ▼
   服务器下载 MP3（临时文件）
        │
        ▼
   写入 ID3 标签 + 专辑封面
        │
        ▼
   上传到 Telegram，拿到 file_id 并存入 Upstash
        │
        ▼
   立即删除服务器临时文件（不保留音频缓存）
```

内联搜索未缓存歌曲时，使用 Render 的 `/audio/<song_id>` 端点，由 Telegram 直接从 Render 拉取已写入 ID3 的音频。

---

## 🚀 Render 部署步骤

### 1. 准备 Upstash Redis

1. 打开 [upstash.com](https://upstash.com) 注册并创建一个 Redis 数据库
2. 在数据库详情页复制：
   - **REST URL**（形如 `https://xxx.upstash.io`）
   - **REST TOKEN**

### 2. 创建 Telegram Bot

在 [@BotFather](https://t.me/BotFather) 创建 Bot，获取 **BOT_TOKEN**；用 [@userinfobot](https://t.me/userinfobot) 获取你的 **管理员数字 ID**。

### 3. 在 Render 创建服务

**方式 A — Blueprint（推荐）**

1. Fork / 推送本仓库到你的 GitHub
2. Render Dashboard → **New +** → **Blueprint**
3. 选择本仓库，Render 会读取 `render.yaml` 自动创建 Web Service
4. 按提示填写 `sync: false` 的环境变量（见下表）

**方式 B — 手动创建 Web Service**

| 配置项 | 值 |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python bot_v6.2.py` |
| Health Check Path | `/` |
| Instance Type | Free（免费实例） |

### 4. 配置环境变量（Environment）

| 变量 | 必填 | 说明 |
|---|---|---|
| `UPSTASH_REDIS_REST_URL` | ✅ | Upstash REST URL |
| `UPSTASH_REDIS_REST_TOKEN` | ✅ | Upstash REST Token |
| `BOT_TOKEN` | ✅* | Telegram Bot Token（也可存入 Upstash） |
| `ADMIN_ID` | ✅* | 管理员数字 ID（也可存入 Upstash） |
| `NETEASE_COOKIE` | 否 | 网易云 MUSIC_U，推荐部署后用 `/setcookie` 设置 |
| `MUSIC_QUALITY` | 否 | 音质：standard/higher/exhigh/lossless/hires，默认 standard |
| `PROXY_URL` | 否 | 访问 Telegram 的代理，Render 在境外通常留空 |

> `RENDER_EXTERNAL_URL` 与 `PORT` 由 Render **自动注入**，无需手动配置。程序会自动用 `RENDER_EXTERNAL_URL` 注册 Webhook 和内联音频端点。

### 5. 部署并初始化

1. 等待 Build & Deploy 完成，日志出现 `✅ 服务器已启动，等待请求...`
2. 在 Bot 私聊发送 `/setcookie <MUSIC_U>` 设置网易云 Cookie
3. 发送 `/play 邓紫棋 泡沫` 测试

---

## 📖 获取网易云 Cookie

1. 浏览器登录 [music.163.com](https://music.163.com)（付费歌曲需 VIP 账号）
2. F12 → **Application** → **Cookies** → `https://music.163.com`
3. 复制 `MUSIC_U` 的 **Value**
4. 在 Bot 中发送 `/setcookie 复制的值`
5. `/cookie` 查看状态，`/refreshcookie` 刷新

> 免费歌曲（fee=8）无需 Cookie 即可播放；付费/VIP 歌曲（fee=1）需要有效且含 VIP 的 MUSIC_U。

---

## 🎛️ 命令一览

### 普通命令
| 命令 | 说明 |
|---|---|
| `/start` | 开始 / 欢迎 |
| `/play 关键词` | 搜索歌曲（群组返回 10 条，私聊 25 条，每页 5 条） |
| `/play 数字ID` | 直接按歌曲 ID 播放 |
| `/playlist 歌单ID/链接` | 播放歌单（仅私聊） |
| `/music` | 已弃用，提示改用 /play |
| 内联 `@XiOuDi163_bot 关键词` | 任意聊天内联搜索 |

### 管理员命令
| 命令 | 说明 |
|---|---|
| `/admin` | 管理员菜单 |
| `/setcookie` `/refreshcookie` `/cookie` | Cookie 管理 |
| `/setquality` `/quality` | 音质管理 |
| `/cachetop` | 缓存榜单 |
| `/autocache` | 闲时缓存控制 |
| `/togglesongcache` | 开关「播放后自动缓存其他版本」（状态持久化，重启保持） |
| `/cachestatus` | 缓存状态 |
| `/cacheplaylist` `/cachesame` `/cachesameall` `/cacheuser` | 各类缓存任务 |
| `/playliststop` | 停止歌单播放 |
| `/toggleplaylist` | 全局开关歌单播放功能 |
| `/addadmin` `/removeadmin` `/admins` | 子管理员管理 |
| `/ban` `/unban` `/banned` | 封禁管理 |
| `/broadcast` | 广播 |
| `/stats` `/users` | 统计 |

---

## 🗂️ 项目结构

```
.
├── bot_v6.2.py        # 主程序：命令、内联、回调、Webhook、音频转发
├── config.py          # 环境变量配置（自动识别 RENDER_EXTERNAL_URL/PORT）
├── netease_api.py     # 网易云 weapi 加密接口封装
├── database.py        # Upstash Redis 数据层
├── downloader.py      # 音频下载模块（重试/进度/超时）
├── logger_utils.py    # 日志美化
├── requirements.txt   # Python 依赖
├── render.yaml        # Render Blueprint 配置
└── .env.example       # 环境变量示例
```

---

## 🔧 本地调试（可选）

```bash
pip install -r requirements.txt
cp .env.example .env   # 填写本地 WEBHOOK_URL（需公网回调地址）
python bot_v6.2.py
```

> Render 版默认使用 Webhook 模式，需要可公网访问的回调地址。Render 部署时由平台自动提供。

---

## ❓ 常见问题

**Q：付费歌曲提示「无法获取播放地址」？**
A：该歌曲 `fee=1` 需要 VIP。确认 MUSIC_U 对应账号会员有效，且 Cookie 未过期（会员未到期 ≠ Cookie 未过期，必要时重新登录获取）。

**Q：内联音频加载慢？**
A：未缓存歌曲首次需要 Render 服务器从网易云下载并写入 ID3，属正常；发送成功后会存 file_id，之后秒发。

**Q：免费实例会休眠吗？**
A：Render 免费实例 15 分钟无请求会休眠，下次请求有冷启动延迟。Webhook 收到请求会自动唤醒。

---

## 📄 License

仅供学习交流使用。
