"""아롱다롱 프로젝트 저장소.

- SupabaseStore : Supabase(무료 클라우드 DB)에 영구 저장. 실제 수업용.
- LocalStore    : 컴퓨터 안의 SQLite 파일에 저장. 연습·시험용
                  (Streamlit 무료 서버에서는 서버가 잠들면 지워질 수 있음).

두 저장소는 같은 함수 이름을 쓰므로 화면 코드(app.py)는 어느 쪽이든 그대로 동작합니다.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

import requests

ENTRY_TEXT_FIELDS = [
    "title", "w_who", "w_when", "w_where", "w_what", "w_how", "w_why",
    "solution", "learned", "felt", "action",
]


class StoreError(Exception):
    """저장소 작업이 실패했을 때."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_image_path(class_id: str, ext: str) -> str:
    safe_class = "".join(ch for ch in class_id if ch.isalnum() or ch == "-") or "class"
    return f"{safe_class}/{uuid.uuid4().hex}.{ext}"


def normalize_entry(row: dict) -> dict:
    e = dict(row)
    photos = e.get("photo_paths")
    if isinstance(photos, str):
        try:
            photos = json.loads(photos)
        except ValueError:
            photos = []
    e["photo_paths"] = [p for p in (photos or []) if p]
    e["featured"] = bool(e.get("featured"))
    e["id"] = int(e["id"])
    d = e.get("entry_date")
    e["entry_date"] = str(d)[:10] if d else ""
    for f in ENTRY_TEXT_FIELDS:
        e[f] = e.get(f) or ""
    return e


# ---------------------------------------------------------------------------
# Supabase (REST API 직접 호출 — 추가 패키지 없이 requests만 사용)
# ---------------------------------------------------------------------------
class SupabaseStore:
    mode = "supabase"
    PAGE = 1000

    def __init__(self, url: str, key: str, bucket: str = "arongdarong", timeout: int = 20):
        self.url = url.strip().rstrip("/")
        self.key = key.strip()
        self.bucket = bucket
        self.timeout = timeout
        self.session = requests.Session()

    # -- 공통 --------------------------------------------------------------
    def _headers(self, extra: dict | None = None) -> dict:
        h = {"apikey": self.key}
        # 예전 방식 키(JWT, eyJ...)는 Authorization 헤더도 함께 보낸다.
        # 새 방식 키(sb_secret_...)는 apikey 헤더만 보내면 된다.
        if not self.key.startswith("sb_"):
            h["Authorization"] = f"Bearer {self.key}"
        if extra:
            h.update(extra)
        return h

    def _rest(self, method: str, table: str, params=None, body=None, prefer: str | None = None):
        extra = {"Prefer": prefer} if prefer else None
        try:
            return self.session.request(
                method, f"{self.url}/rest/v1/{table}", params=params, json=body,
                headers=self._headers(extra), timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise StoreError(f"저장소에 연결하지 못했어요: {exc}") from exc

    @staticmethod
    def _check(resp, what: str):
        if resp.status_code >= 400:
            raise StoreError(f"{what} 실패 ({resp.status_code}): {resp.text[:300]}")

    def _select_all(self, table: str, params: dict) -> list[dict]:
        rows_all: list[dict] = []
        offset = 0
        while True:
            p = dict(params)
            p["limit"] = self.PAGE
            p["offset"] = offset
            r = self._rest("GET", table, params=p)
            self._check(r, f"{table} 불러오기")
            rows = r.json()
            if not rows:
                break
            rows_all.extend(rows)
            offset += len(rows)
        return rows_all

    # -- 상태 점검 ----------------------------------------------------------
    def health(self) -> list[tuple[str, bool, str]]:
        checks = []
        for table in ("students", "entries", "votes"):
            try:
                r = self._rest("GET", table, params={"select": "id", "limit": 1})
                ok = r.status_code < 400
                checks.append((f"표 '{table}'", ok, "" if ok else r.text[:200]))
            except StoreError as exc:
                checks.append((f"표 '{table}'", False, str(exc)))
        try:
            r = self.session.get(f"{self.url}/storage/v1/bucket/{self.bucket}",
                                 headers=self._headers(), timeout=self.timeout)
            ok = r.status_code < 400
            checks.append((f"사진 보관함 '{self.bucket}'", ok, "" if ok else r.text[:200]))
        except requests.RequestException as exc:
            checks.append((f"사진 보관함 '{self.bucket}'", False, str(exc)))
        return checks

    # -- 기록(entries) -------------------------------------------------------
    def list_entries(self, class_id: str) -> list[dict]:
        rows = self._select_all("entries", {
            "select": "*", "class_id": f"eq.{class_id}", "order": "entry_date.desc,id.desc",
        })
        return [normalize_entry(r) for r in rows]

    def get_entry(self, entry_id: int) -> dict | None:
        r = self._rest("GET", "entries", params={"select": "*", "id": f"eq.{int(entry_id)}"})
        self._check(r, "기록 불러오기")
        rows = r.json()
        return normalize_entry(rows[0]) if rows else None

    def add_entry(self, data: dict) -> dict:
        r = self._rest("POST", "entries", body=data, prefer="return=representation")
        self._check(r, "기록 저장")
        return normalize_entry(r.json()[0])

    def update_entry(self, entry_id: int, data: dict) -> None:
        r = self._rest("PATCH", "entries", params={"id": f"eq.{int(entry_id)}"}, body=data,
                       prefer="return=minimal")
        self._check(r, "기록 고치기")

    def delete_entry(self, entry_id: int) -> None:
        r = self._rest("DELETE", "entries", params={"id": f"eq.{int(entry_id)}"})
        self._check(r, "기록 지우기")

    # -- 투표(votes) ---------------------------------------------------------
    def list_votes(self, class_id: str) -> list[dict]:
        return self._select_all("votes", {
            "select": "entry_id,voter_name", "class_id": f"eq.{class_id}", "order": "id.asc",
        })

    def add_vote(self, entry_id: int, class_id: str, voter: str) -> bool:
        r = self._rest("POST", "votes", body={
            "entry_id": int(entry_id), "class_id": class_id, "voter_name": voter,
        }, prefer="return=minimal")
        if r.status_code == 409:
            return False
        self._check(r, "투표")
        return True

    def remove_vote(self, entry_id: int, voter: str) -> None:
        r = self._rest("DELETE", "votes", params={
            "entry_id": f"eq.{int(entry_id)}", "voter_name": f"eq.{voter}",
        })
        self._check(r, "투표 취소")

    # -- 학생(students) -------------------------------------------------------
    def list_students(self, class_id: str) -> list[dict]:
        return self._select_all("students", {
            "select": "id,class_id,name,created_at", "class_id": f"eq.{class_id}", "order": "name.asc",
        })

    def get_student(self, class_id: str, name: str) -> dict | None:
        r = self._rest("GET", "students", params={
            "select": "*", "class_id": f"eq.{class_id}", "name": f"eq.{name}",
        })
        self._check(r, "학생 확인")
        rows = r.json()
        return rows[0] if rows else None

    def add_student(self, class_id: str, name: str, pin_hash: str) -> bool:
        r = self._rest("POST", "students", body={
            "class_id": class_id, "name": name, "pin_hash": pin_hash,
        }, prefer="return=minimal")
        if r.status_code == 409:
            return False
        self._check(r, "학생 등록")
        return True

    def delete_student(self, class_id: str, name: str) -> None:
        r = self._rest("DELETE", "students", params={
            "class_id": f"eq.{class_id}", "name": f"eq.{name}",
        })
        self._check(r, "비밀번호 초기화")

    # -- 그림·사진(storage) -----------------------------------------------------
    def put_image(self, path: str, data: bytes, content_type: str) -> None:
        try:
            r = self.session.post(
                f"{self.url}/storage/v1/object/{self.bucket}/{path}", data=data,
                headers=self._headers({"Content-Type": content_type, "x-upsert": "true",
                                       "cache-control": "3600"}),
                timeout=60,
            )
        except requests.RequestException as exc:
            raise StoreError(f"사진을 올리지 못했어요: {exc}") from exc
        self._check(r, "사진 올리기")

    def get_image(self, path: str) -> bytes | None:
        try:
            r = self.session.get(f"{self.url}/storage/v1/object/{self.bucket}/{path}",
                                 headers=self._headers(), timeout=30)
        except requests.RequestException:
            return None
        if r.status_code >= 400:
            return None
        return r.content

    def delete_images(self, paths: list[str]) -> None:
        paths = [p for p in paths if p]
        if not paths:
            return
        try:
            self.session.delete(f"{self.url}/storage/v1/object/{self.bucket}",
                                json={"prefixes": paths}, headers=self._headers(), timeout=30)
        except requests.RequestException:
            pass  # 사진 정리는 실패해도 기록 작업은 계속한다.


# ---------------------------------------------------------------------------
# 로컬 SQLite (연습용)
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  class_id TEXT NOT NULL,
  name TEXT NOT NULL,
  pin_hash TEXT NOT NULL,
  created_at TEXT,
  UNIQUE (class_id, name)
);
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  class_id TEXT NOT NULL,
  student_name TEXT NOT NULL,
  entry_date TEXT NOT NULL,
  title TEXT, w_who TEXT, w_when TEXT, w_where TEXT, w_what TEXT, w_how TEXT, w_why TEXT,
  solution TEXT, learned TEXT, felt TEXT, action TEXT,
  drawing_path TEXT,
  photo_paths TEXT DEFAULT '[]',
  featured INTEGER DEFAULT 0,
  created_at TEXT,
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS votes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  class_id TEXT NOT NULL,
  voter_name TEXT NOT NULL,
  created_at TEXT,
  UNIQUE (entry_id, voter_name)
);
CREATE INDEX IF NOT EXISTS entries_class_idx ON entries (class_id, entry_date);
CREATE INDEX IF NOT EXISTS votes_class_idx ON votes (class_id);
"""


class LocalStore:
    mode = "local"

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.img_root = os.path.join(self.root, "images")
        os.makedirs(self.img_root, exist_ok=True)
        self.db_path = os.path.join(self.root, "arongdarong.db")
        self.lock = threading.Lock()
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        return c

    def health(self) -> list[tuple[str, bool, str]]:
        return [("이 컴퓨터 안의 임시 저장소", True, self.root)]

    # -- 기록 ------------------------------------------------------------------
    def list_entries(self, class_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM entries WHERE class_id=? ORDER BY entry_date DESC, id DESC", (class_id,)
            ).fetchall()
        return [normalize_entry(dict(r)) for r in rows]

    def get_entry(self, entry_id: int) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM entries WHERE id=?", (int(entry_id),)).fetchone()
        return normalize_entry(dict(r)) if r else None

    @staticmethod
    def _prep(data: dict) -> dict:
        d = dict(data)
        if "photo_paths" in d:
            d["photo_paths"] = json.dumps(list(d["photo_paths"] or []), ensure_ascii=False)
        if "featured" in d:
            d["featured"] = 1 if d["featured"] else 0
        return d

    def add_entry(self, data: dict) -> dict:
        d = self._prep(data)
        d.setdefault("created_at", now_iso())
        cols = ", ".join(d.keys())
        qs = ", ".join("?" for _ in d)
        with self.lock, self._conn() as c:
            cur = c.execute(f"INSERT INTO entries ({cols}) VALUES ({qs})", list(d.values()))
            new_id = cur.lastrowid
        return self.get_entry(new_id)

    def update_entry(self, entry_id: int, data: dict) -> None:
        d = self._prep(data)
        if not d:
            return
        sets = ", ".join(f"{k}=?" for k in d)
        with self.lock, self._conn() as c:
            c.execute(f"UPDATE entries SET {sets} WHERE id=?", list(d.values()) + [int(entry_id)])

    def delete_entry(self, entry_id: int) -> None:
        with self.lock, self._conn() as c:
            c.execute("DELETE FROM votes WHERE entry_id=?", (int(entry_id),))
            c.execute("DELETE FROM entries WHERE id=?", (int(entry_id),))

    # -- 투표 ------------------------------------------------------------------
    def list_votes(self, class_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT entry_id, voter_name FROM votes WHERE class_id=? ORDER BY id", (class_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def add_vote(self, entry_id: int, class_id: str, voter: str) -> bool:
        try:
            with self.lock, self._conn() as c:
                c.execute(
                    "INSERT INTO votes (entry_id, class_id, voter_name, created_at) VALUES (?,?,?,?)",
                    (int(entry_id), class_id, voter, now_iso()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_vote(self, entry_id: int, voter: str) -> None:
        with self.lock, self._conn() as c:
            c.execute("DELETE FROM votes WHERE entry_id=? AND voter_name=?", (int(entry_id), voter))

    # -- 학생 ------------------------------------------------------------------
    def list_students(self, class_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, class_id, name, created_at FROM students WHERE class_id=? ORDER BY name",
                (class_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_student(self, class_id: str, name: str) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM students WHERE class_id=? AND name=?", (class_id, name)).fetchone()
        return dict(r) if r else None

    def add_student(self, class_id: str, name: str, pin_hash: str) -> bool:
        try:
            with self.lock, self._conn() as c:
                c.execute(
                    "INSERT INTO students (class_id, name, pin_hash, created_at) VALUES (?,?,?,?)",
                    (class_id, name, pin_hash, now_iso()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_student(self, class_id: str, name: str) -> None:
        with self.lock, self._conn() as c:
            c.execute("DELETE FROM students WHERE class_id=? AND name=?", (class_id, name))

    # -- 그림·사진 ---------------------------------------------------------------
    def _img_file(self, path: str) -> str:
        full = os.path.abspath(os.path.join(self.img_root, path))
        if not full.startswith(self.img_root + os.sep):
            raise StoreError("잘못된 사진 경로예요.")
        return full

    def put_image(self, path: str, data: bytes, content_type: str) -> None:
        full = self._img_file(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)

    def get_image(self, path: str) -> bytes | None:
        try:
            with open(self._img_file(path), "rb") as f:
                return f.read()
        except (OSError, StoreError):
            return None

    def delete_images(self, paths: list[str]) -> None:
        for p in paths:
            if not p:
                continue
            try:
                os.remove(self._img_file(p))
            except (OSError, StoreError):
                pass
