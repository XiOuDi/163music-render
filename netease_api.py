"""
网易云音乐 API 封装模块
实现 weapi 加密接口，支持搜索、获取歌曲播放地址、歌曲详情等
"""

import json
import base64
import random
import string
import hashlib
import logging
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


# ============================================================
# weapi 加密相关
# ============================================================

# 网易云固定 AES 密钥和 IV
_AES_KEY = "0CoJUm6Qyw8W8jud"
_AES_IV = b"0102030405060708"

# 网易云 RSA 公钥模数 (十六进制)
_RSA_PUB_KEY = int(
    "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725"
    "152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312"
    "ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424"
    "d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7",
    16,
)
_RSA_EXP = 65537


def _rand_str(length: int = 16) -> str:
    """生成指定长度的随机字符串（字母+数字）"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _aes_encrypt(text: str, key: str) -> str:
    """AES-CBC 加密，返回 base64"""
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, _AES_IV)
    encrypted = cipher.encrypt(pad(text.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


def _rsa_encrypt(text: str) -> str:
    """网易云 RSA 加密（反转文本后做模幂）"""
    text = text[::-1]
    rs = int(text.encode("utf-8").hex(), 16)
    return format(pow(rs, _RSA_EXP, _RSA_PUB_KEY), "x").zfill(256)


def _weapi(data: dict) -> dict:
    """将 dict 编码为 weapi 所需的 params + encSecKey"""
    text = json.dumps(data, ensure_ascii=False)
    secret = _rand_str(16)
    params = _aes_encrypt(_aes_encrypt(text, _AES_KEY), secret)
    enc_sec_key = _rsa_encrypt(secret)
    return {"params": params, "encSecKey": encSecKey}


# ============================================================
# API 客户端
# ============================================================

_BASE_URL = "https://music.163.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://music.163.com/",
    "Content-Type": "application/x-www-form-urlencoded",
}


class NeteaseAPI:
    """网易云音乐 API 客户端"""

    def __init__(self, cookie: str = ""):
        self.session = requests.Session()
        self.session.headers.update(_HEADERS)
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=50,
            max_retries=3,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        if cookie:
            self.session.cookies.set("MUSIC_U", cookie, domain=".music.163.com")
        self.session.cookies.set("__remember_me", "true", domain=".music.163.com")
        self.session.cookies.set("NMTID", self._gen_nmtid(), domain=".music.163.com")

        # 无cookie会话（cookie被限流时降级使用）
        self._nocookie_session = requests.Session()
        self._nocookie_session.headers.update(_HEADERS)
        self._nocookie_session.mount("https://", requests.adapters.HTTPAdapter(
            pool_connections=20, pool_maxsize=20, max_retries=2))
        self._nocookie_session.mount("http://", requests.adapters.HTTPAdapter(
            pool_connections=20, pool_maxsize=20, max_retries=2))

    @staticmethod
    def _gen_nmtid() -> str:
        return hashlib.md5(random.randbytes(16)).hexdigest()

    def _post(self, path: str, data: dict) -> dict:
        """发送 weapi POST 请求，带3次重试"""
        url = f"{_BASE_URL}{path}"
        payload = _weapi(data)
        last_error = None
        for attempt in range(3):
            try:
                resp = self.session.post(url, data=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_error = e
                if attempt < 2:
                    import time
                    time.sleep(1 * (attempt + 1))
        raise last_error

    # ----------------------------------------------------------
    # 搜索
    # ----------------------------------------------------------
    def search(self, keyword: str, limit: int = 30, offset: int = 0) -> dict:
        """
        搜索歌曲
        返回: {"songs": [...], "songCount": N}
        cookie被限流(code=405)时自动降级为无cookie搜索
        """
        path = "/weapi/search/get"
        data = {
            "s": keyword,
            "type": 1,       # 1=单曲
            "limit": limit,
            "offset": offset,
        }
        result = self._post(path, data)
        _code = result.get("code", -1)
        _songs = result.get("result", {}).get("songs", [])
        logging.getLogger(__name__).info(
            f"搜索API: keyword='{keyword}' limit={limit} code={_code} 返回{len(_songs)}首"
        )
        if _songs:
            _first = _songs[0]
            _first_name = _first.get("name", "?")
            _first_artists = "/".join(a.get("name","") for a in _first.get("artists",[]))
            logging.getLogger(__name__).info(
                f"搜索API: 首条结果='{_first_name}' by {_first_artists}"
            )
        # cookie被限流时降级为无cookie搜索
        if result.get("code") == 405:
            logging.getLogger(__name__).warning("搜索cookie被限流(405)，降级为无cookie搜索")
            result = self._post_nocookie(path, data)
        return result

    def _post_nocookie(self, path: str, data: dict) -> dict:
        """使用无cookie会话发送请求（cookie被限流时降级）"""
        url = f"{_BASE_URL}{path}"
        payload = _weapi(data)
        for attempt in range(3):
            try:
                resp = self._nocookie_session.post(url, data=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except Exception:
                if attempt < 2:
                    import time
                    time.sleep(1 * (attempt + 1))
        return {"code": -1, "result": {"songs": [], "songCount": 0}}

    # ----------------------------------------------------------
    # 获取歌曲播放地址
    # ----------------------------------------------------------
    def get_song_url(self, song_ids: list, level: str = "standard") -> dict:
        """
        获取歌曲播放直链
        level: standard / higher / exhigh / lossless / hires / jyeffect / sky / jymaster
        """
        path = "/weapi/song/enhance/player/url/v1"
        data = {
            "ids": json.dumps(song_ids),
            "level": level,
            "encodeType": "mp3",
        }
        return self._post(path, data)

    # ----------------------------------------------------------
    # 获取歌曲详情（名称、歌手、专辑、封面）
    # ----------------------------------------------------------
    def get_song_detail(self, song_ids: list) -> dict:
        """获取歌曲详情"""
        path = "/weapi/v3/song/detail"
        c = json.dumps([{"id": sid} for sid in song_ids])
        data = {"c": c, "ids": json.dumps(song_ids)}
        return self._post(path, data)

    def get_songs_detail_simple(self, song_ids: list) -> list:
        """批量获取歌曲详情，返回精简列表（同 search_songs_simple 格式）"""
        result = self.get_song_detail(song_ids)
        songs = result.get("songs", [])
        simple_list = []
        for s in songs:
            artists = "/".join(a.get("name", "") for a in s.get("ar", []))
            album = s.get("al", {}).get("name", "")
            cover = s.get("al", {}).get("picUrl", "")
            simple_list.append({
                "id": s.get("id"),
                "name": s.get("name", ""),
                "artist": artists,
                "album": album,
                "cover": cover,
                "duration": s.get("dt", 0),
            })
        return simple_list

    # ----------------------------------------------------------
    # 歌词
    # ----------------------------------------------------------
    def get_lyric(self, song_id: int) -> dict:
        """获取歌词"""
        path = "/weapi/song/lyric"
        data = {"id": song_id, "lv": -1, "kv": -1, "tv": -1}
        return self._post(path, data)

    # ----------------------------------------------------------
    # 便捷方法：搜索并返回精简列表
    # ----------------------------------------------------------
    def search_songs_simple(self, keyword: str, limit: int = 20) -> list:
        """
        搜索歌曲，返回精简列表：
        [{"id": int, "name": str, "artist": str, "album": str, "cover": str, "duration": int}, ...]
        """
        result = self.search(keyword, limit=limit)
        songs = result.get("result", {}).get("songs", [])
        simple_list = []
        for s in songs:
            artists = "/".join(a.get("name", "") for a in s.get("artists", []))
            album = s.get("album", {}).get("name", "")
            cover = s.get("album", {}).get("picUrl", "")
            simple_list.append({
                "id": s.get("id"),
                "name": s.get("name", ""),
                "artist": artists,
                "album": album,
                "cover": cover,
                "duration": s.get("duration", 0),  # 毫秒
            })
        return simple_list

    def get_first_song_url(self, song_id: int, level: str = "standard") -> str:
        """获取单首歌的播放直链，失败返回空字符串"""
        result = self.get_song_url([song_id], level=level)
        data_list = result.get("data", [])
        if data_list:
            return data_list[0].get("url", "") or ""
        return ""

    # ----------------------------------------------------------
    # 排行榜
    # ----------------------------------------------------------
    def get_toplist_songs(self, playlist_id: int = 3778678, limit: int = 100) -> list:
        """
        获取排行榜/歌单歌曲（默认云音乐热歌榜 3778678）
        超过500首时分批获取歌曲详情，避免API超时
        返回精简列表，同 search_songs_simple 格式
        """
        path = "/weapi/v6/playlist/detail"
        data = {"id": playlist_id, "n": 10000, "s": 0}
        result = self._post(path, data)
        playlist = result.get("playlist", {})
        track_ids = [t["id"] for t in playlist.get("trackIds", [])][:limit]
        if not track_ids:
            return []

        BATCH_SIZE = 500
        all_songs = []
        for i in range(0, len(track_ids), BATCH_SIZE):
            batch_ids = track_ids[i:i + BATCH_SIZE]
            try:
                detail = self.get_song_detail(batch_ids)
                songs = detail.get("songs", [])
                all_songs.extend(songs)
            except Exception as e:
                print(f"[NeteaseAPI] 歌单详情分批获取失败 (batch {i//BATCH_SIZE + 1}): {e}")
            if i + BATCH_SIZE < len(track_ids):
                import time
                time.sleep(0.1)

        simple_list = []
        for s in all_songs:
            artists = "/".join(a.get("name", "") for a in s.get("ar", []))
            album = s.get("al", {}).get("name", "")
            cover = s.get("al", {}).get("picUrl", "")
            simple_list.append({
                "id": s.get("id"),
                "name": s.get("name", ""),
                "artist": artists,
                "album": album,
                "cover": cover,
                "duration": s.get("dt", 0),
            })
        return simple_list

    async def get_toplist_songs_async(self, playlist_id: int = 3778678, limit: int = 10000, max_concurrent: int = 2) -> list:
        """异步并发获取歌单歌曲"""
        import asyncio
        path = "/weapi/v6/playlist/detail"
        data = {"id": playlist_id, "n": 10000, "s": 0}
        result = await asyncio.to_thread(self._post, path, data)
        playlist = result.get("playlist", {})
        track_ids = [t["id"] for t in playlist.get("trackIds", [])][:limit]
        if not track_ids:
            return []

        BATCH_SIZE = 500
        batches = [track_ids[i:i + BATCH_SIZE] for i in range(0, len(track_ids), BATCH_SIZE)]
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_batch(batch_ids, batch_idx):
            async with semaphore:
                try:
                    detail = await asyncio.to_thread(self.get_song_detail, batch_ids)
                    songs = detail.get("songs", [])
                    return songs
                except Exception as e:
                    print(f"[NeteaseAPI] 并发获取歌单详情失败: {e}")
                    return []

        tasks = [fetch_batch(batch, idx) for idx, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks)

        all_songs = []
        for songs in results:
            all_songs.extend(songs)

        simple_list = []
        for s in all_songs:
            artists = "/".join(a.get("name", "") for a in s.get("ar", []))
            album = s.get("al", {}).get("name", "")
            cover = s.get("al", {}).get("picUrl", "")
            simple_list.append({
                "id": s.get("id"),
                "name": s.get("name", ""),
                "artist": artists,
                "album": album,
                "cover": cover,
                "duration": s.get("dt", 0),
            })
        return simple_list

    # ----------------------------------------------------------
    # 用户歌单
    # ----------------------------------------------------------
    def get_user_playlists(self, uid: int, limit: int = 30, offset: int = 0) -> list:
        path = "/weapi/user/playlist"
        data = {"uid": uid, "limit": limit, "offset": offset, "includeVideo": True}
        result = self._post(path, data)
        playlists = result.get("playlist", [])
        simple_list = []
        for p in playlists:
            simple_list.append({
                "id": p.get("id"),
                "name": p.get("name", ""),
                "trackCount": p.get("trackCount", 0),
                "cover": p.get("coverImgUrl", ""),
                "creator": p.get("creator", {}).get("nickname", ""),
            })
        return simple_list

    def get_user_playlist_songs(self, uid: int, max_per_playlist: int = 100) -> list:
        all_songs = []
        seen_ids = set()
        try:
            playlists = self.get_user_playlists(uid, limit=100)
            for pl in playlists:
                try:
                    songs = self.get_toplist_songs(pl["id"], limit=max_per_playlist)
                    for s in songs:
                        if s["id"] not in seen_ids:
                            seen_ids.add(s["id"])
                            all_songs.append(s)
                except Exception:
                    continue
        except Exception:
            pass
        return all_songs

    # ----------------------------------------------------------
    # Cookie 管理
    # ----------------------------------------------------------
    def update_cookie(self, cookie: str):
        """动态更新 MUSIC_U cookie — 先清除所有旧MUSIC_U避免冲突"""
        # 清除所有已存在的 MUSIC_U cookie（包括NetEase Set-Cookie设置的）
        for dom in (".music.163.com", "music.163.com"):
            for pth in ("/", "/weapi", "/api"):
                try:
                    self.session.cookies.clear(domain=dom, path=pth, name="MUSIC_U")
                except Exception:
                    pass
        # 也遍历cookie jar清除所有MUSIC_U
        try:
            to_remove = [c for c in self.session.cookies if c.name == "MUSIC_U"]
            for c in to_remove:
                try:
                    self.session.cookies.clear(domain=c.domain, path=c.path, name="MUSIC_U")
                except Exception:
                    pass
        except Exception:
            pass
        # 设置新cookie
        self.session.cookies.set("MUSIC_U", cookie, domain=".music.163.com", path="/")
        logging.getLogger(__name__).info(
            f"update_cookie: 新cookie前缀={cookie[:12]}... 长度={len(cookie)}"
        )

    def get_cookie(self) -> str:
        for c in self.session.cookies:
            if c.name == "MUSIC_U":
                return c.value
        return ""

    def refresh_cookie(self) -> str:
        try:
            url = f"{_BASE_URL}/weapi/login/token/refresh"
            payload = _weapi({})
            resp = self.session.post(url, data=payload, timeout=30)
            new_cookie = ""
            for c in resp.cookies:
                if c.name == "MUSIC_U" and c.value:
                    new_cookie = c.value
                    break
            if new_cookie:
                self.update_cookie(new_cookie)
                return new_cookie
        except Exception as e:
            print(f"[NeteaseAPI] 刷新cookie失败: {e}")
        return ""

    def check_cookie_valid(self) -> bool:
        try:
            result = self.search("test", limit=1)
            return result.get("code") == 200
        except Exception:
            return False

    def get_current_user_id(self) -> int:
        try:
            path = "/weapi/nuser/account/get"
            result = self._post(path, {})
            profile = result.get("profile", {})
            return profile.get("userId", 0)
        except Exception:
            return 0

    def get_playlist_songs(self, playlist_id: int, limit: int = 1000) -> list:
        return self.get_toplist_songs(playlist_id, limit=limit)
