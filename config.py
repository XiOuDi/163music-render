"""
配置文件 - Render 云部署版
全部从环境变量读取。Render 会自动注入 RENDER_EXTERNAL_URL 和 PORT。
"""

import os

# Telegram Bot Token（也可存储在 Upstash，由数据库读取覆盖）
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# 网易云 MUSIC_U cookie（也可通过 /setcookie 存储在 Upstash）
NETEASE_COOKIE = os.environ.get("NETEASE_COOKIE", "")

# 管理员用户数字 ID（也可存储在 Upstash）
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# 歌曲音质等级: standard / higher / exhigh / lossless / hires
MUSIC_QUALITY = os.environ.get("MUSIC_QUALITY", "standard")

# 内联搜索返回结果数量
INLINE_RESULTS_LIMIT = int(os.environ.get("INLINE_RESULTS_LIMIT", "25"))

# 普通搜索返回数量
SEARCH_RESULTS_LIMIT = int(os.environ.get("SEARCH_RESULTS_LIMIT", "10"))

# 访问 Telegram 的代理（Render 服务器在境外，通常留空直连即可）
PROXY_URL = os.environ.get("PROXY_URL", "")

# Cloudflare Workers 代理（可选，保留兼容；Render 版默认由服务器直接转发音频）
CF_PROXY_URL = os.environ.get("CF_PROXY_URL", "")

# 兼容保留字段
LOCAL_AUDIO_PROXY = os.environ.get("LOCAL_AUDIO_PROXY", "")
AUDIO_PROXY_URL = os.environ.get("AUDIO_PROXY_URL", "")
INLINE_PROXY_URL = os.environ.get("INLINE_PROXY_URL", "")

# Webhook 模式配置
# Render 自动设置 RENDER_EXTERNAL_URL（形如 https://xxx.onrender.com）
# 也可显式设置 WEBHOOK_URL 覆盖
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", os.environ.get("RENDER_EXTERNAL_URL", ""))
# Render 自动注入 PORT，本地调试默认 8080
PORT = int(os.environ.get("PORT", "8080"))

# Upstash Redis（数据持久化：file_id、cookie、歌单进度、配置等）
UPSTASH_REDIS_REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

# 数据库类型：固定使用 upstash（云端 Redis）
DB_TYPE = os.environ.get("DB_TYPE", "upstash")

# 默认欢迎语（可通过管理员 /setwelcome 运行时修改，持久化到 Upstash）
DEFAULT_WELCOME = os.environ.get("DEFAULT_WELCOME", """👋 你好，{username}

此bot由西欧帝制作 @XiOuDi_A 
有任何建议可以给我留言

📖 使用方法：
1.   /play 关键词 — 搜索歌曲
2.  内联搜索：在任意聊天输入 @XiOuDi163_bot 歌曲名
3.  /playlist 歌单ID/链接 — 播放网易云歌单（仅限私聊）

例如 
/play 邓紫棋 泡沫
@XiOuDi163_bot 邓紫棋 泡沫""")
