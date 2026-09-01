"""
Upstash Redis 数据库封装
使用 Upstash REST API，无需额外 Redis 客户端库
"""

import json
import time
import requests
import config


class UpstashDB:
    """Upstash Redis 数据库操作"""

    def __init__(self):
        self.url = config.UPSTASH_REDIS_REST_URL.rstrip("/")
        self.token = config.UPSTASH_REDIS_REST_TOKEN
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.enabled = bool(self.url and self.token)
        # 使用Session连接池，避免频繁创建连接
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20, pool_maxsize=20, max_retries=3
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _exec(self, *args, retries=3):
        """执行 Redis 命令（POST 方式，支持中文等任意字符），带重试"""
        if not self.enabled:
            return None
        payload = json.dumps(list(args))
        for attempt in range(retries):
            try:
                resp = self.session.post(
                    self.url, data=payload, timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("result")
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                print(f"[Upstash] 命令失败 {args[0]}: {e}")
                return None

    def _exec_pipeline(self, commands: list):
        """批量执行多个Redis命令（Upstash pipeline），commands为命令列表的列表"""
        if not self.enabled or not commands:
            return None
        payload = json.dumps(commands)
        for attempt in range(3):
            try:
                resp = self.session.post(
                    self.url, data=payload, timeout=30,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                print(f"[Upstash] pipeline失败 ({len(commands)}条命令): {e}")
                return None

    # ---- 用户集合 ----
    def add_user(self, user_id: int):
        self._exec("SADD", "bot:users", str(user_id))

    def get_users(self) -> list:
        result = self._exec("SMEMBERS", "bot:users")
        return result if result else []

    # ---- 封禁集合 ----
    def ban_user(self, user_id):
        self._exec("SADD", "bot:banned", str(user_id))

    def unban_user(self, user_id):
        self._exec("SREM", "bot:banned", str(user_id))

    def get_banned(self) -> list:
        result = self._exec("SMEMBERS", "bot:banned")
        return result if result else []

    def is_banned(self, user_id: int) -> bool:
        result = self._exec("SISMEMBER", "bot:banned", str(user_id))
        return bool(result)

    # ---- 欢迎语 ----
    def get_welcome(self) -> str:
        result = self._exec("GET", "bot:welcome")
        return result if result else ""

    def set_welcome(self, text: str):
        self._exec("SET", "bot:welcome", text)

    def reset_welcome(self):
        self._exec("DEL", "bot:welcome")

    # ---- 统计 ----
    def incr_search(self):
        self._exec("HINCRBY", "bot:stats", "total_searches", 1)

    def incr_play(self):
        self._exec("HINCRBY", "bot:stats", "total_plays", 1)

    def get_stats(self) -> dict:
        result = self._exec("HGETALL", "bot:stats")
        if result and isinstance(result, list):
            return {result[i]: int(result[i + 1]) for i in range(0, len(result), 2)}
        return {"total_searches": 0, "total_plays": 0}

    # ---- Cookie 存储（运行时可更新） ----
    def get_cookie(self) -> str:
        result = self._exec("GET", "bot:cookie")
        return result if result else ""

    def set_cookie(self, cookie: str):
        self._exec("SET", "bot:cookie", cookie)
        self._exec("SET", "bot:cookie_updated_at", str(int(time.time())))

    def get_cookie_updated_at(self) -> int:
        result = self._exec("GET", "bot:cookie_updated_at")
        return int(result) if result else 0

    # ---- 音质设置 ----
    def get_quality(self) -> str:
        """获取当前音质设置，默认standard"""
        result = self._exec("GET", "bot:quality")
        return result if result else "standard"

    def set_quality(self, quality: str):
        """设置音质（standard/higher）"""
        self._exec("SET", "bot:quality", quality)

    # ---- Bot 配置（从 Database 加载，减少环境变量配置）----
    def get_bot_token(self) -> str:
        """获取 Telegram Bot Token"""
        result = self._exec("GET", "bot:token")
        return result if result else ""

    def set_bot_token(self, token: str):
        """设置 Telegram Bot Token"""
        self._exec("SET", "bot:token", token)

    def get_admin_id(self) -> int:
        """获取主管理员 ID"""
        result = self._exec("GET", "bot:admin_id")
        return int(result) if result else 0

    def set_admin_id(self, admin_id: int):
        """设置主管理员 ID"""
        self._exec("SET", "bot:admin_id", str(admin_id))

    def get_cf_proxy_url(self) -> str:
        """获取 CF 代理 URL"""
        result = self._exec("GET", "bot:cf_proxy_url")
        return result if result else ""

    def set_cf_proxy_url(self, url: str):
        """设置 CF 代理 URL"""
        self._exec("SET", "bot:cf_proxy_url", url)

    # ---- 歌单播放开关（管理员控制）----
    def is_playlist_enabled(self) -> bool:
        """检查歌单播放功能是否启用（默认启用）"""
        result = self._exec("GET", "bot:playlist_enabled")
        if result is None or result == "":
            return True
        return result == "1" or result.lower() == "true"

    def set_playlist_enabled(self, enabled: bool):
        """设置歌单播放功能开关"""
        self._exec("SET", "bot:playlist_enabled", "1" if enabled else "0")

    # ---- Cookie检测时间（重启后继续检测周期）----
    def get_last_cookie_check(self) -> int:
        """获取上次Cookie检测时间戳"""
        result = self._exec("GET", "bot:last_cookie_check")
        return int(result) if result else 0

    def set_last_cookie_check(self, ts: int):
        """设置上次Cookie检测时间戳"""
        self._exec("SET", "bot:last_cookie_check", str(ts))

    # ---- 歌单播放状态（重启后继续播放）----
    def save_active_playlist(self, user_id: int, playlist_id: int, songs: list, current_index: int = 0):
        """保存用户正在播放的歌单状态"""
        data = {
            "playlist_id": playlist_id,
            "current_index": current_index,
            "total": len(songs),
            "songs": songs,
            "start_time": int(time.time())
        }
        self._exec("SET", f"playlist:active:{user_id}", json.dumps(data, ensure_ascii=False), "EX", 86400)
        self._exec("SADD", "playlist:active_users", str(user_id))

    def get_active_playlist(self, user_id: int) -> dict:
        """获取用户正在播放的歌单状态"""
        result = self._exec("GET", f"playlist:active:{user_id}")
        if not result:
            return {}
        try:
            return json.loads(result)
        except Exception:
            return {}

    def update_playlist_index(self, user_id: int, current_index: int):
        """更新歌单播放进度"""
        data = self.get_active_playlist(user_id)
        if not data:
            return
        data["current_index"] = current_index
        self._exec("SET", f"playlist:active:{user_id}", json.dumps(data, ensure_ascii=False), "EX", 86400)

    def remove_active_playlist(self, user_id: int):
        """移除用户的歌单播放状态（播放完成或被停止）"""
        self._exec("DEL", f"playlist:active:{user_id}")
        self._exec("SREM", "playlist:active_users", str(user_id))

    def get_active_playlist_users(self) -> list:
        """获取所有正在播放歌单的用户ID列表"""
        result = self._exec("SMEMBERS", "playlist:active_users")
        return [int(x) for x in result] if result else []

    def set_playlist_stop_flag(self, user_id: int):
        """设置停止歌单播放的标志（管理员停止用户播放）"""
        self._exec("SET", f"playlist:stop:{user_id}", "1", "EX", 60)

    # ---- 歌单排队队列（重启后恢复）----
    def save_playlist_queue(self, user_id: int, queue: list):
        """保存用户的歌单排队队列（queue: [(playlist_id, songs), ...]）"""
        if not queue:
            self._exec("DEL", f"playlist:queue:{user_id}")
            return
        # 只保存 playlist_id 和 songs，songs 可能很大，但 Upstash 支持
        data = [{"playlist_id": item[0], "songs": item[1]} for item in queue]
        self._exec("SET", f"playlist:queue:{user_id}", json.dumps(data, ensure_ascii=False), "EX", 86400)

    def get_playlist_queue(self, user_id: int) -> list:
        """获取用户的歌单排队队列，返回 [(playlist_id, songs), ...]"""
        result = self._exec("GET", f"playlist:queue:{user_id}")
        if not result:
            return []
        try:
            data = json.loads(result)
            return [(item["playlist_id"], item["songs"]) for item in data]
        except Exception:
            return []

    def clear_playlist_queue(self, user_id: int):
        """清空用户的歌单排队队列"""
        self._exec("DEL", f"playlist:queue:{user_id}")

    def check_playlist_stop_flag(self, user_id: int) -> bool:
        """检查是否有停止标志，并清除"""
        exists = self._exec("EXISTS", f"playlist:stop:{user_id}")
        if exists:
            self._exec("DEL", f"playlist:stop:{user_id}")
            return True
        return False

    # ---- Telegram file_id 缓存（避免重复上传音频） ----
    def get_file_id(self, song_id: int) -> str:
        result = self._exec("GET", f"cache:file_id:{song_id}")
        return result if result else ""

    def get_file_ids_batch(self, song_ids: list) -> dict:
        """批量获取file_id，返回 {song_id: file_id} 字典"""
        if not song_ids:
            return {}
        keys = [f"cache:file_id:{sid}" for sid in song_ids]
        results = self._exec("MGET", *keys)
        if not results:
            return {sid: "" for sid in song_ids}
        return {sid: (results[i] if i < len(results) and results[i] else "") for i, sid in enumerate(song_ids)}

    def set_file_id(self, song_id: int, file_id: str):
        self._exec("SET", f"cache:file_id:{song_id}", file_id)
        # 维护索引集合，用于快速统计数量
        self._exec("SADD", "cache:file_id:index", str(song_id))

    def delete_file_id(self, song_id: int):
        """删除file_id缓存（用于标题不正确的缓存自动清理）"""
        self._exec("DEL", f"cache:file_id:{song_id}")
        self._exec("SREM", "cache:file_id:index", str(song_id))

    # ---- 用户搜索历史（用于闲时缓存扩展） ----
    def add_searched_song(self, song_id: int):
        """记录用户搜索过的歌曲ID"""
        self._exec("SADD", "cache:searched_songs", str(song_id))

    def get_uncached_searched_songs(self, limit: int = 100) -> list:
        """获取用户搜索过但未缓存的歌曲ID列表"""
        all_searched = self._exec("SMEMBERS", "cache:searched_songs") or []
        uncached = []
        for sid_str in all_searched:
            try:
                sid = int(sid_str)
                if not self.get_file_id(sid):
                    uncached.append(sid)
                    if len(uncached) >= limit:
                        break
            except (ValueError, TypeError):
                continue
        return uncached

    def clear_all_file_ids(self) -> int:
        """清除所有file_id缓存，返回删除数量"""
        keys = self.scan_keys("cache:file_id:*")
        if not keys:
            return 0
        count = 0
        for k in keys:
            self._exec("DEL", k)
            count += 1
        return count

    def scan_keys(self, pattern: str, count: int = 500) -> list:
        """使用SCAN命令获取所有匹配的键（替代KEYS命令，Upstash REST API的KEYS有bug）"""
        all_keys = []
        cursor = "0"
        while True:
            result = self._exec("SCAN", cursor, "MATCH", pattern, "COUNT", str(count))
            if not result:
                break
            # SCAN返回 [next_cursor, [key1, key2, ...]]
            if isinstance(result, list) and len(result) >= 2:
                cursor = str(result[0])
                batch_keys = result[1] if isinstance(result[1], list) else []
                all_keys.extend(batch_keys)
                if cursor == "0":
                    break
            else:
                break
        return all_keys

    def count_file_ids(self) -> int:
        """统计已缓存的file_id数量（使用SCARD，O(1)复杂度）"""
        result = self._exec("SCARD", "cache:file_id:index")
        if result is not None:
            return int(result)
        # 回退：如果索引集合不存在，使用SCAN统计（慢）
        keys = self.scan_keys("cache:file_id:*")
        # 排除索引集合本身
        return len([k for k in keys if k != "cache:file_id:index"])

    def get_all_cached_song_ids(self) -> list:
        """获取所有已缓存的歌曲ID列表（从索引集合）"""
        result = self._exec("SMEMBERS", "cache:file_id:index")
        if result:
            return [int(x) for x in result]
        # 回退：使用SCAN
        keys = self.scan_keys("cache:file_id:*")
        ids = []
        for k in keys:
            if k == "cache:file_id:index":
                continue
            try:
                ids.append(int(k.replace("cache:file_id:", "")))
            except ValueError:
                pass
        return ids

    # ---- 同名补全任务持久化（重启后继续）----
    def init_cachesameall(self, unique_songs: dict):
        """初始化同名补全任务，存储所有待搜索的歌曲（批量HSET，每批100首）"""
        # 清除旧数据
        self._exec("DEL", "cachesameall:keys", "cachesameall:pending", "cachesameall:stats")
        # 批量存储：每100首歌一个HSET命令
        items = list(unique_songs.items())
        for i in range(0, len(items), 100):
            batch = items[i:i+100]
            hset_args = ["HSET", "cachesameall:keys"]
            for key, info in batch:
                hset_args.extend([key, json.dumps(info, ensure_ascii=False)])
            self._exec(*hset_args)
        # 初始化统计
        self._exec("HSET", "cachesameall:stats",
                   "total", str(len(unique_songs)),
                   "searched", "0",
                   "total_new", "0",
                   "success", "0",
                   "failed", "0")
        self._exec("SET", "cachesameall:active", "1", "EX", 86400)

    def pop_next_search_key(self) -> tuple:
        """取出下一个待搜索的歌曲（非原子，但可接受重复），返回 (key, info_dict) 或 None"""
        # 随机取一个key
        result = self._exec("HRANDFIELD", "cachesameall:keys")
        if not result:
            return None
        key = result
        # 获取info
        info_json = self._exec("HGET", "cachesameall:keys", key)
        if not info_json:
            return None
        # 删除该key（标记为已取出）
        self._exec("HDEL", "cachesameall:keys", key)
        try:
            return key, json.loads(info_json)
        except Exception:
            return None

    def get_remaining_search_count(self) -> int:
        """获取剩余待搜索数量"""
        result = self._exec("HLEN", "cachesameall:keys")
        return int(result) if result else 0

    def add_pending_song(self, song: dict):
        """添加待缓存歌曲到队列"""
        self._exec("RPUSH", "cachesameall:pending", json.dumps(song, ensure_ascii=False))

    def pop_pending_song(self) -> dict:
        """取出下一个待缓存歌曲，返回 dict 或 None"""
        result = self._exec("LPOP", "cachesameall:pending")
        if not result:
            return None
        try:
            return json.loads(result)
        except Exception:
            return None

    def get_pending_count(self) -> int:
        """获取待缓存队列长度"""
        result = self._exec("LLEN", "cachesameall:pending")
        return int(result) if result else 0

    def incr_cachesameall_stat(self, field: str, amount: int = 1):
        """增加统计计数"""
        self._exec("HINCRBY", "cachesameall:stats", field, str(amount))

    def get_cachesameall_stats(self) -> dict:
        """获取任务统计"""
        result = self._exec("HGETALL", "cachesameall:stats")
        if not result:
            return {}
        # HGETALL 返回 flat array [key1, val1, key2, val2, ...]
        stats = {}
        for i in range(0, len(result), 2):
            stats[result[i]] = int(result[i+1]) if i+1 < len(result) else 0
        return stats

    def is_cachesameall_active(self) -> bool:
        """检查是否有未完成的同名补全任务"""
        exists = self._exec("EXISTS", "cachesameall:active")
        return bool(exists)

    def touch_cachesameall(self):
        """刷新任务活跃标志（防止过期）"""
        self._exec("SET", "cachesameall:active", "1", "EX", 86400)

    def clear_cachesameall(self):
        """清除同名补全任务数据"""
        self._exec("DEL", "cachesameall:keys", "cachesameall:pending",
                   "cachesameall:stats", "cachesameall:active")

    # ---- 用户播放自动缓存（播放歌曲后自动缓存前20个版本，持久化重启续传）----
    def add_autocache_song(self, song_name: str, artist: str = ""):
        """添加歌曲到自动缓存队列（去重，SET保证不重复）"""
        member = song_name if not artist else f"{song_name}||{artist}"
        self._exec("SADD", "autocache:song:queue", member)
        self._exec("SET", "autocache:song:active", "1", "EX", 86400)

    def add_autocache_song_raw(self, member: str):
        """将原始member（'歌名||歌手'格式）放回自动缓存队列"""
        if member:
            self._exec("SADD", "autocache:song:queue", member)
            self._exec("SET", "autocache:song:active", "1", "EX", 86400)

    def add_autocache_song_raw(self, member: str):
        """直接添加原始member到自动缓存队列（用于暂停时放回队列）"""
        self._exec("SADD", "autocache:song:queue", member)
        self._exec("SET", "autocache:song:active", "1", "EX", 86400)

    def pop_autocache_song(self) -> str:
        """随机取出一个待自动缓存的歌曲，返回 '歌名||歌手' 或 None"""
        result = self._exec("SRANDMEMBER", "autocache:song:queue")
        if not result:
            return None
        self._exec("SREM", "autocache:song:queue", result)
        return result

    def get_autocache_queue_count(self) -> int:
        """获取自动缓存队列长度"""
        result = self._exec("SCARD", "autocache:song:queue")
        return int(result) if result else 0

    def get_autocache_song_enabled(self) -> bool:
        """获取自动缓存其他版本开关状态（默认开启）"""
        result = self._exec("GET", "autocache:song:enabled")
        if result is None:
            return True
        return str(result).lower() in ("1", "true", "yes", "on")

    def set_autocache_song_enabled(self, enabled: bool):
        """设置自动缓存其他版本开关状态（持久化）"""
        self._exec("SET", "autocache:song:enabled", "1" if enabled else "0")

    def is_autocache_active(self) -> bool:
        """检查自动缓存任务是否活跃"""
        exists = self._exec("EXISTS", "autocache:song:active")
        return bool(exists)

    def touch_autocache(self):
        """刷新自动缓存活跃标志"""
        self._exec("SET", "autocache:song:active", "1", "EX", 86400)

    def clear_autocache(self):
        """清除自动缓存任务数据"""
        self._exec("DEL", "autocache:song:queue", "autocache:song:active")

    # ---- 管理员管理（主管理员来自环境变量，附加管理员存Redis） ----
    def get_admins(self) -> list:
        """获取所有附加管理员ID列表"""
        result = self._exec("SMEMBERS", "bot:admins")
        return [int(x) for x in result] if result else []

    def add_admin(self, user_id: int):
        """添加管理员"""
        self._exec("SADD", "bot:admins", str(user_id))

    def remove_admin(self, user_id: int):
        """移除管理员"""
        self._exec("SREM", "bot:admins", str(user_id))

    def is_admin(self, user_id: int) -> bool:
        """检查是否为管理员（含主管理员）"""
        if user_id == config.ADMIN_ID:
            return True
        result = self._exec("SISMEMBER", "bot:admins", str(user_id))
        return bool(result)


# 全局实例
db = UpstashDB()
