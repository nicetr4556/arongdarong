"""아라초 아롱다롱 프로젝트 — 아까운 Wrong, 多 Wrong!

매일의 실패를 육하원칙 · 그림 · 해결 방법 · 배느실(배운 점, 느낀 점, 실천할 점)로 기록하고,
친구들의 '좋은 실패'에 투표하고, 발표회에서 그대로 발표하는 Streamlit 앱입니다.
"""
from __future__ import annotations

import csv
import hashlib
import html
import inspect
import io
import os
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps

from arong.media import bytes_to_dataurl, dataurl_to_png, process_photo
from arong.store import (
    ENTRY_TEXT_FIELDS, LocalStore, StoreError, SupabaseStore, new_image_path, now_iso,
)
from arong.theme import CSS, hero_html

# =============================================================================
# 기본 설정 — 학교 이름이나 반 목록을 바꾸려면 여기만 고치면 됩니다.
# =============================================================================
SCHOOL_SHORT = "아라초"
SCHOOL_FULL = "아라초등학교"
CLASSES = ["1-1", "2-1", "2-2", "3-1", "4-1", "4-2", "5-1", "6-1"]
DEFAULT_CLASS = "5-1"
MAX_PHOTOS = 3
PER_PAGE = 12
LOCAL_TEACHER_PASSWORD = "arong1234"  # 임시 저장 모드에서만 쓰는 임시 비밀번호

KST = timezone(timedelta(hours=9))
WEEKDAYS = "월화수목금토일"
APP_DIR = os.path.dirname(os.path.abspath(__file__))

PAGES = [
    ("write", "✏️ 실패 쓰기"),
    ("note", "📒 내 실패 노트"),
    ("gallery", "🖼️ 실패 갤러리"),
    ("rank", "🏆 좋은 실패 순위"),
    ("show", "🎤 발표 모드"),
    ("teacher", "🔒 선생님"),
]
PAGE_LABEL = dict(PAGES)
LABEL_PAGE = {label: key for key, label in PAGES}

# 육하원칙 (필드, 제목, 예시)
W_FIELDS = [
    ("w_who", "👤 누가", "예) 나, 나와 동생"),
    ("w_when", "🕐 언제", "예) 오늘 아침 등교 전"),
    ("w_where", "📍 어디서", "예) 우리 집 부엌"),
    ("w_what", "📦 무엇을", "예) 우유가 가득 든 컵을"),
    ("w_how", "💥 어떻게", "예) 팔꿈치로 쳐서 바닥에 쏟았다"),
    ("w_why", "❓ 왜", "예) 서두르다가 컵이 있는 걸 못 봐서"),
]
# 배느실 (필드, 제목, 예시, 꾸밈 클래스)
BNS_FIELDS = [
    ("learned", "📘 배운 점", "예) 서두르면 실수가 더 많아진다는 걸 배웠어요.", "learned"),
    ("felt", "💗 느낀 점", "예) 엄마께 죄송했지만 직접 닦고 나니 뿌듯했어요.", "felt"),
    ("action", "🏃 실천할 점", "예) 컵은 식탁 안쪽에 두고, 5분 일찍 일어날래요.", "action"),
]
FIELD_NAMES = {"title": "실패 제목", "solution": "해결 방법", "drawing": "그림이나 사진"}
FIELD_NAMES.update({f: label.split(" ", 1)[1] for f, label, _ in W_FIELDS})
FIELD_NAMES.update({f: label.split(" ", 1)[1] for f, label, _, _ in BNS_FIELDS})
REQUIRED = ["title", "w_what", "solution"]


def class_label(cid: str) -> str:
    grade, room = cid.split("-")
    return f"{grade}학년 {room}반"


# set_page_config는 화면에 무엇이든 그리기 전에 불러야 합니다.
_qp_class = st.query_params.get("class", DEFAULT_CLASS)
if _qp_class not in CLASSES:
    _qp_class = DEFAULT_CLASS
st.set_page_config(
    page_title=f"{SCHOOL_SHORT} {class_label(_qp_class)} 아롱다롱 프로젝트",
    page_icon="🌈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ss = st.session_state


# =============================================================================
# 버전 호환 도우미 (Streamlit 버전이 바뀌어도 버튼이 꽉 차게)
# =============================================================================
def _stretch_kwargs(fn) -> dict:
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return {}
    if "width" in params:
        return {"width": "stretch"}
    if "use_container_width" in params:
        return {"use_container_width": True}
    return {}


WIDE_BTN = _stretch_kwargs(st.button)
WIDE_SUBMIT = _stretch_kwargs(st.form_submit_button)
WIDE_DL = _stretch_kwargs(st.download_button)


def secret(name: str, default=None):
    try:
        value = st.secrets.get(name, default)
    except Exception:  # secrets 파일이 아예 없을 때
        return default
    return value if value not in ("", None) else default


# =============================================================================
# 저장소
# =============================================================================
@st.cache_resource
def get_store():
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_KEY")
    if url and key:
        return SupabaseStore(str(url), str(key), bucket=str(secret("SUPABASE_BUCKET", "arongdarong")))
    return LocalStore(os.path.join(APP_DIR, "arong_data"))


store = get_store()


@st.cache_data(ttl=15, show_spinner=False)
def cached_entries(class_id: str) -> list[dict]:
    return store.list_entries(class_id)


@st.cache_data(ttl=15, show_spinner=False)
def cached_votes(class_id: str) -> list[dict]:
    return store.list_votes(class_id)


@st.cache_data(ttl=3600, max_entries=400, show_spinner=False)
def cached_image(path: str) -> bytes | None:
    return store.get_image(path)


@st.cache_data(ttl=3600, max_entries=600, show_spinner=False)
def cached_thumb(path: str) -> bytes | None:
    raw = cached_image(path)
    if not raw:
        return None
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        resample = getattr(Image, "Resampling", Image).LANCZOS
        img = ImageOps.fit(img, (480, 300), method=resample)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=82)
        return out.getvalue()
    except Exception:
        return None


def refresh_data():
    cached_entries.clear()
    cached_votes.clear()


# =============================================================================
# 작은 도우미들
# =============================================================================
def today_kst() -> date:
    return datetime.now(KST).date()


def fmt_date(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def fmt_short(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{d.month}.{d.day}"


def esc(text) -> str:
    return html.escape(str(text or "")).replace("\n", "<br>").replace("$", "&#36;")


def md(markup: str):
    st.markdown(markup, unsafe_allow_html=True)


def clean_name(name: str) -> str:
    return "".join((name or "").split())[:10]


def pin_hash(class_id: str, name: str, pin: str) -> str:
    return hashlib.sha256(f"arongdarong|{class_id}|{name}|{pin}".encode("utf-8")).hexdigest()


def empty_draft() -> dict:
    d = {f: "" for f in ENTRY_TEXT_FIELDS}
    d.update(entry_date=today_kst(), drawing=None, drawing_changed=False,
             new_photos=[], keep_photos=[], orig_photos=[], orig_drawing=None)
    return d


def vote_index(votes: list[dict]):
    counts = Counter(int(v["entry_id"]) for v in votes)
    by_voter = defaultdict(set)
    for v in votes:
        by_voter[v["voter_name"]].add(int(v["entry_id"]))
    return counts, by_voter


def base_url() -> str:
    url = secret("APP_URL")
    if url:
        return str(url).split("?")[0].rstrip("/")
    try:
        ctx_url = getattr(st.context, "url", None)
        if ctx_url:
            return ctx_url.split("?")[0].replace("/~/+", "").rstrip("/")
    except Exception:
        pass
    try:
        host = st.context.headers.get("host")
        if host:
            scheme = "http" if host.startswith(("localhost", "127.")) else "https"
            return f"{scheme}://{host}"
    except Exception:
        pass
    return ""


def make_link(**params) -> str:
    query = urlencode({k: v for k, v in params.items() if v})
    base = base_url()
    return f"{base}/?{query}" if base else f"?{query}"


def flash(kind: str, msg: str):
    ss.flashes.append((kind, msg))


def toast(msg: str, icon: str = "✅"):
    ss.toasts.append((msg, icon))


# =============================================================================
# 상태 준비와 콜백
# =============================================================================
def init_state():
    if ss.get("_boot"):
        return
    ss._boot = True
    qp = st.query_params
    cid = qp.get("class", DEFAULT_CLASS)
    ss.class_id = cid if cid in CLASSES else DEFAULT_CLASS
    ss.class_sel = ss.class_id
    student = qp.get("student")
    view = qp.get("view", "show" if student else "write")
    ss.nav = PAGE_LABEL.get(view, PAGE_LABEL["write"])
    ss.show_student = student
    ss.me = None
    ss.pending_reg = None
    ss.form_v = 0
    ss.canvas_n = 0
    ss.canvas_base = None
    ss.canvas_last_t = None
    ss.up_n = 0
    ss.draft = empty_draft()
    ss.edit_id = None
    ss.slide = 0
    ss.gal_page = 0
    ss.last_page = None
    ss.teacher_ok = False
    ss.access_ok = False
    ss.confirm = None
    ss.flashes = []
    ss.toasts = []
    ss.celebrate = False


def go(page_key: str):
    ss.nav = PAGE_LABEL[page_key]


def reset_form():
    ss.draft = empty_draft()
    ss.form_v += 1
    ss.canvas_n += 1
    ss.canvas_base = None
    ss.up_n += 1
    ss.edit_id = None


def logout():
    ss.me = None
    ss.pending_reg = None
    ss.confirm = None
    reset_form()


def on_class_change():
    ss.class_id = ss.class_sel
    logout()
    ss.show_student = None
    ss.pop("show_sel", None)
    ss.slide = 0
    ss.gal_page = 0
    ss.teacher_ok = False


def start_edit(entry: dict):
    reset_form()
    d = ss.draft
    for f in ENTRY_TEXT_FIELDS:
        d[f] = entry.get(f) or ""
    try:
        d["entry_date"] = date.fromisoformat(entry["entry_date"])
    except ValueError:
        pass
    if entry.get("drawing_path"):
        raw = cached_image(entry["drawing_path"])
        d["drawing"] = bytes_to_dataurl(raw, "image/png") if raw else None
    d["orig_drawing"] = entry.get("drawing_path")
    d["keep_photos"] = list(entry.get("photo_paths") or [])
    d["orig_photos"] = list(entry.get("photo_paths") or [])
    ss.edit_id = entry["id"]
    ss.canvas_base = d["drawing"]
    go("write")


def do_vote(entry_id: int, owner: str, add: bool):
    if not ss.me or owner == ss.me:
        return
    try:
        if add:
            ok = store.add_vote(entry_id, ss.class_id, ss.me)
            toast("좋은 실패에 💛를 보냈어요!" if ok else "이미 💛를 보냈어요.", "💛")
        else:
            store.remove_vote(entry_id, ss.me)
            toast("투표를 취소했어요.", "🤍")
    except StoreError as exc:
        flash("error", f"투표하지 못했어요. {exc}")
    refresh_data()


def toggle_featured(entry: dict):
    try:
        store.update_entry(entry["id"], {"featured": not entry["featured"], "updated_at": now_iso()})
        toast("대표 실패로 뽑았어요!" if not entry["featured"] else "대표 실패에서 뺐어요.", "⭐")
    except StoreError as exc:
        flash("error", f"바꾸지 못했어요. {exc}")
    refresh_data()


def ask_confirm(kind: str, target):
    ss.confirm = (kind, target)


def clear_confirm():
    ss.confirm = None


def delete_entry(entry: dict):
    ss.confirm = None
    try:
        store.delete_entry(entry["id"])
        store.delete_images([entry.get("drawing_path")] + list(entry.get("photo_paths") or []))
    except StoreError as exc:
        flash("error", f"지우지 못했어요. {exc}")
        return
    if ss.edit_id == entry["id"]:
        reset_form()
    refresh_data()
    toast("기록을 지웠어요.", "🗑️")


def reset_student_pin(name: str):
    ss.confirm = None
    try:
        store.delete_student(ss.class_id, name)
        toast(f"{name} 학생의 비밀번호를 초기화했어요. 다음에 들어올 때 새 비밀번호를 정해요.", "🔑")
    except StoreError as exc:
        flash("error", f"초기화하지 못했어요. {exc}")


def remove_new_photo(i: int):
    photos = ss.draft["new_photos"]
    if 0 <= i < len(photos):
        photos.pop(i)


def remove_keep_photo(path: str):
    if path in ss.draft["keep_photos"]:
        ss.draft["keep_photos"].remove(path)


def open_detail(entry_id: int):
    ss.open_detail = entry_id


def step_slide(delta: int):
    ss.slide = max(0, ss.slide + delta)


def reset_gallery_page():
    ss.gal_page = 0


# =============================================================================
# 화면 조각
# =============================================================================
def render_header(compact: bool = False):
    md(hero_html(SCHOOL_FULL, SCHOOL_SHORT, class_label(ss.class_id), compact=compact))


def gate_access():
    code = secret("ACCESS_CODE")
    if not code or ss.access_ok:
        return
    render_header()
    with st.container(border=True):
        st.markdown("#### 🔑 우리 반 입장 코드를 넣어요")
        with st.form("gate_form"):
            value = st.text_input("입장 코드", type="password")
            if st.form_submit_button("입장하기 👉"):
                if value.strip() == str(code).strip():
                    ss.access_ok = True
                    st.rerun()
                st.error("코드가 달라요. 선생님께 물어봐요.")
    st.stop()


def top_bar():
    c1, c2, c3 = st.columns([1.1, 2.6, 0.9], vertical_alignment="bottom")
    with c1:
        st.selectbox("🏫 우리 반", CLASSES, key="class_sel", format_func=class_label,
                     on_change=on_class_change)
    with c2:
        if ss.me:
            md(f'<span class="me">👋 <b>{esc(ss.me)}</b> 친구, 오늘도 아롱다롱!</span>')
        else:
            md('<span class="me off">🙋 아직 내 이름으로 들어오지 않았어요</span>')
    with c3:
        if ss.me:
            st.button("나가기", on_click=logout, key="logout_btn", **WIDE_BTN)
    st.radio("메뉴", [label for _, label in PAGES], key="nav", horizontal=True,
             label_visibility="collapsed")


def sync_query_params(page: str):
    want = {"class": ss.class_id, "view": page}
    if page == "show" and ss.show_student:
        want["student"] = ss.show_student
    current = {k: st.query_params.get(k) for k in st.query_params.keys()}
    if current != want:
        st.query_params.clear()
        for k, v in want.items():
            st.query_params[k] = v


def show_messages():
    for msg, icon in ss.toasts:
        st.toast(msg, icon=icon)
    ss.toasts = []
    for kind, msg in ss.flashes:
        getattr(st, kind)(msg)
    ss.flashes = []
    if ss.celebrate:
        st.balloons()
        ss.celebrate = False


def login_box(reason: str):
    with st.container(border=True):
        md(f'<div class="sec" style="margin-top:4px"><span class="t">🙋 {esc(reason)}</span></div>')
        st.caption("처음이면 이름과 '나만 아는 숫자 4개'를 정해요. 다음부터는 같은 이름과 숫자로 들어와요.")
        with st.form("login_form", clear_on_submit=False):
            c1, c2, c3 = st.columns([2, 1.4, 1], vertical_alignment="bottom")
            name = c1.text_input("내 이름", max_chars=10, placeholder="예) 김민준")
            pin = c2.text_input("비밀번호 (숫자 4개)", type="password", max_chars=4, placeholder="●●●●")
            submitted = c3.form_submit_button("들어가기 👉", type="primary", **WIDE_SUBMIT)
        if submitted:
            handle_login(name, pin)
        pending = ss.pending_reg
        if pending:
            st.info(f"**'{pending['name']}'** 이름은 처음이에요! 이 이름과 비밀번호로 시작할까요? "
                    "비밀번호 숫자 4개를 꼭 기억해요. 🔐")
            b1, b2, _ = st.columns([1.3, 1.3, 2])
            if b1.button("✅ 네, 시작할래요", type="primary", key="reg_yes"):
                try:
                    created = store.add_student(ss.class_id, pending["name"],
                                                pin_hash(ss.class_id, pending["name"], pending["pin"]))
                except StoreError as exc:
                    st.error(f"등록하지 못했어요. {exc}")
                    return
                ss.pending_reg = None
                if created:
                    ss.me = pending["name"]
                    toast(f"반가워요, {pending['name']}! 첫 아롱다롱을 시작해요.", "🎉")
                else:
                    flash("warning", "방금 같은 이름이 등록됐어요. 비밀번호를 넣고 다시 들어와요.")
                st.rerun()
            if b2.button("✏️ 이름 다시 쓰기", key="reg_no"):
                ss.pending_reg = None
                st.rerun()


def handle_login(raw_name: str, raw_pin: str):
    name, pin = clean_name(raw_name), (raw_pin or "").strip()
    if not name:
        st.error("이름을 써 주세요.")
        return
    if not (pin.isdigit() and len(pin) == 4):
        st.error("비밀번호는 숫자 4개예요. (예: 0715)")
        return
    try:
        student = store.get_student(ss.class_id, name)
    except StoreError as exc:
        st.error(f"확인하지 못했어요. {exc}")
        return
    if student:
        if student.get("pin_hash") == pin_hash(ss.class_id, name, pin):
            ss.me = name
            ss.pending_reg = None
            reset_form()
            toast(f"어서 와요, {name}!", "👋")
            st.rerun()
        else:
            st.error("비밀번호가 달라요. 잊어버렸다면 선생님께 말씀드려요.")
    else:
        ss.pending_reg = {"name": name, "pin": pin}


def sec_header(num: str, title: str, desc: str = ""):
    md(f'<div class="sec"><span class="num">{num}</span><span class="t">{title}</span>'
       f'<span class="d">{desc}</span></div>')


def entry_head_html(e: dict, votes_n: int, number: int | None = None) -> str:
    chips = []
    if number:
        chips.append(f'<span class="chip num">실패 #{number}</span>')
    chips.append(f'<span class="chip">📅 {fmt_date(e["entry_date"])}</span>')
    chips.append(f'<span class="chip">🙋 {esc(e["student_name"])}</span>')
    chips.append(f'<span class="chip heart">💛 {votes_n}</span>')
    if e.get("featured"):
        chips.append('<span class="chip star">⭐ 대표 실패</span>')
    return (f'<div class="ehead"><div class="chips">{"".join(chips)}</div>'
            f'<div class="etitle">{esc(e["title"]) or "(제목 없음)"}</div></div>')


def ww_html(e: dict) -> str:
    cells = "".join(
        f'<div class="ww-cell"><div class="ww-label">{label}</div>'
        f'<div class="ww-text">{esc(e.get(f)) or "<span class=muted>—</span>"}</div></div>'
        for f, label, _ in W_FIELDS
    )
    return f'<div class="ww">{cells}</div>'


def tcard_html(kind: str, label: str, text: str) -> str:
    body = esc(text) or '<span class="muted">—</span>'
    return f'<div class="tcard {kind}"><div class="tlabel">{label}</div><div class="ttext">{body}</div></div>'


def bns_html(e: dict) -> str:
    cards = "".join(tcard_html(cls, label, e.get(f)) for f, label, _, cls in BNS_FIELDS)
    return f'<div class="bns">{cards}</div>'


def show_images(e: dict, empty_note: bool = True):
    shown = False
    if e.get("drawing_path"):
        raw = cached_image(e["drawing_path"])
        if raw:
            st.image(raw, caption="✏️ 내가 그린 그림")
            shown = True
    photos = [p for p in e.get("photo_paths") or [] if p]
    if photos:
        cols = st.columns(max(2, len(photos)))
        for col, path in zip(cols, photos):
            raw = cached_image(path)
            if raw:
                with col:
                    st.image(raw)
                shown = True
    if not shown and empty_note:
        md('<div class="thumb-empty">🖍️<small>그림이나 사진이 없어요</small></div>')


def show_thumb(e: dict):
    path = e.get("drawing_path") or next(iter(e.get("photo_paths") or []), None)
    raw = cached_thumb(path) if path else None
    if raw:
        st.image(raw)
    else:
        md('<div class="thumb-empty">🌈</div>')


def render_entry(e: dict, votes_n: int, number: int | None = None, head: bool = True, big: bool = False):
    def wrap(markup: str) -> str:
        return f'<div class="slide">{markup}</div>' if big else markup

    if head:
        md(wrap(entry_head_html(e, votes_n, number)))
    left, right = st.columns([1.12, 1], gap="large")
    with left:
        show_images(e)
    with right:
        md(wrap(ww_html(e)))
    md(wrap(tcard_html("sol", "🔧 해결 방법 — 다음에는 이렇게 해요", e.get("solution"))))
    md(wrap(bns_html(e)))


def vote_button(e: dict, counts: Counter, my_votes: set, key: str):
    n = counts.get(e["id"], 0)
    if not ss.me:
        st.button(f"💛 {n}", key=key, disabled=True, help="내 이름으로 들어오면 투표할 수 있어요.", **WIDE_BTN)
    elif e["student_name"] == ss.me:
        st.button(f"💛 {n} · 내 실패", key=key, disabled=True, **WIDE_BTN)
    elif e["id"] in my_votes:
        st.button(f"💛 {n} · 투표했어요", key=key, on_click=do_vote,
                  args=(e["id"], e["student_name"], False), help="한 번 더 누르면 투표가 취소돼요.", **WIDE_BTN)
    else:
        st.button(f"🤍 좋은 실패! {n}", key=key, type="primary", on_click=do_vote,
                  args=(e["id"], e["student_name"], True), **WIDE_BTN)


@st.dialog("🔎 아롱다롱 자세히 보기", width="large")
def detail_dialog(entry_id: int):
    entries = cached_entries(ss.class_id)
    counts, by_voter = vote_index(cached_votes(ss.class_id))
    e = next((x for x in entries if x["id"] == entry_id), None)
    if not e:
        st.warning("이 기록을 찾을 수 없어요. 지워졌을 수도 있어요.")
        return
    render_entry(e, counts.get(e["id"], 0))
    c1, c2 = st.columns([1, 1])
    with c1:
        vote_button(e, counts, by_voter.get(ss.me, set()), key=f"dlg_vote_{e['id']}")
    with c2:
        st.link_button("🎤 이 친구 발표 화면 열기",
                       make_link(**{"class": ss.class_id, "view": "show", "student": e["student_name"]}),
                       **_stretch_kwargs(st.link_button))


# =============================================================================
# 그림판 (손으로 그리는 칸)
# =============================================================================
_canvas = components.declare_component("arong_canvas", path=os.path.join(APP_DIR, "drawing_canvas"))


@st.fragment
def drawing_block():
    key = f"canvas_{ss.form_v}_{ss.canvas_n}"
    value = _canvas(initial=ss.canvas_base,
                    hint="손가락·펜·마우스로 그려요. 스탬프로 그때 기분도 표현해 봐요!",
                    key=key, default=None)
    if isinstance(value, dict) and (key, value.get("t")) != ss.canvas_last_t:
        ss.canvas_last_t = (key, value.get("t"))
        ss.draft["drawing"] = None if value.get("empty") else value.get("dataUrl")
        ss.draft["drawing_changed"] = True


def on_enter_write():
    """다른 화면에 갔다가 돌아오면 그리던 그림을 바탕에 다시 깔아 준다."""
    if ss.last_page != "write":
        ss.canvas_n += 1
        ss.canvas_base = ss.draft.get("drawing")


# =============================================================================
# ✏️ 실패 쓰기
# =============================================================================
def bind_text(field: str, label: str, placeholder: str, max_chars: int, area: bool = False,
              height: int | None = None):
    k = f"{field}_{ss.form_v}"
    if k not in ss:
        ss[k] = ss.draft.get(field, "")
    if area:
        value = st.text_area(label, key=k, placeholder=placeholder, max_chars=max_chars, height=height)
    else:
        value = st.text_input(label, key=k, placeholder=placeholder, max_chars=max_chars)
    ss.draft[field] = value


def bind_date():
    k = f"entry_date_{ss.form_v}"
    today = today_kst()
    if k not in ss:
        d = ss.draft.get("entry_date") or today
        ss[k] = min(d, today)
    ss.draft["entry_date"] = st.date_input("📅 날짜", key=k, max_value=today, format="YYYY.MM.DD")


def completeness(d: dict) -> tuple[int, int, list[str]]:
    checks = [("title", d.get("title"))]
    checks += [(f, d.get(f)) for f, _, _ in W_FIELDS]
    checks.append(("drawing", d.get("drawing") or d.get("new_photos") or d.get("keep_photos")))
    checks.append(("solution", d.get("solution")))
    checks += [(f, d.get(f)) for f, _, _, _ in BNS_FIELDS]
    missing = [FIELD_NAMES[f] for f, v in checks if not (v.strip() if isinstance(v, str) else v)]
    return len(checks) - len(missing), len(checks), missing


def photo_block():
    d = ss.draft
    total = len(d["keep_photos"]) + len(d["new_photos"])
    if total < MAX_PHOTOS:
        files = st.file_uploader(
            f"사진이나 그림 파일 올리기 (최대 {MAX_PHOTOS}장, 지금 {total}장)",
            type=["png", "jpg", "jpeg", "webp", "gif"], accept_multiple_files=True, key=f"up_{ss.up_n}",
        )
        cam = None
        if st.toggle("📷 카메라로 바로 찍기", key=f"cam_on_{ss.up_n}"):
            cam = st.camera_input("사진 찍기", key=f"cam_{ss.up_n}", label_visibility="collapsed")
        incoming = list(files or []) + ([cam] if cam is not None else [])
        if incoming:
            for f in incoming:
                if len(d["keep_photos"]) + len(d["new_photos"]) >= MAX_PHOTOS:
                    flash("warning", f"사진은 {MAX_PHOTOS}장까지만 넣을 수 있어요.")
                    break
                try:
                    d["new_photos"].append({"name": f.name, "data": process_photo(f.getvalue())})
                except Exception:
                    flash("warning", f"'{f.name}' 파일은 열 수 없는 사진이에요.")
            ss.up_n += 1
            st.rerun()
    else:
        st.caption(f"사진은 {MAX_PHOTOS}장까지 넣을 수 있어요. 바꾸고 싶으면 아래에서 빼고 다시 올려요.")

    items = [("keep", p) for p in d["keep_photos"]] + [("new", i) for i in range(len(d["new_photos"]))]
    if items:
        cols = st.columns(MAX_PHOTOS)
        for col, (kind, ref) in zip(cols, items):
            with col:
                if kind == "keep":
                    raw = cached_image(ref)
                    if raw:
                        st.image(raw)
                    st.button("✕ 빼기", key=f"rmk_{ss.form_v}_{ref}", on_click=remove_keep_photo, args=(ref,))
                else:
                    st.image(d["new_photos"][ref]["data"])
                    st.button("✕ 빼기", key=f"rmn_{ss.form_v}_{ss.up_n}_{ref}", on_click=remove_new_photo,
                              args=(ref,))


def save_entry():
    d, cid, me = ss.draft, ss.class_id, ss.me
    editing = ss.edit_id is not None
    to_delete: list[str] = []
    try:
        with st.spinner("저장하는 중이에요… 잠깐만요!"):
            drawing_path = d.get("orig_drawing") if editing else None
            if d.get("drawing_changed") or not editing:
                if d.get("drawing"):
                    png = dataurl_to_png(d["drawing"])
                    new_path = new_image_path(cid, "png")
                    store.put_image(new_path, png, "image/png")
                    if drawing_path:
                        to_delete.append(drawing_path)
                    drawing_path = new_path
                elif drawing_path:
                    to_delete.append(drawing_path)
                    drawing_path = None
            photo_paths = list(d["keep_photos"])
            to_delete += [p for p in d.get("orig_photos", []) if p not in photo_paths]
            for ph in d["new_photos"]:
                path = new_image_path(cid, "jpg")
                store.put_image(path, ph["data"], "image/jpeg")
                photo_paths.append(path)
            payload = {f: (d.get(f) or "").strip() for f in ENTRY_TEXT_FIELDS}
            payload.update(entry_date=d["entry_date"].isoformat(), drawing_path=drawing_path,
                           photo_paths=photo_paths, updated_at=now_iso())
            if editing:
                store.update_entry(ss.edit_id, payload)
            else:
                payload.update(class_id=cid, student_name=me, featured=False, created_at=now_iso())
                store.add_entry(payload)
            store.delete_images(to_delete)
    except (StoreError, ValueError) as exc:
        st.error(f"저장하지 못했어요. 다시 눌러 보고, 그래도 안 되면 선생님께 알려 주세요.\n\n{exc}")
        return
    refresh_data()
    reset_form()
    flash("success", "🎉 저장 완료! '🖼️ 실패 갤러리'에서 친구들의 아롱다롱도 구경하고 💛를 보내 봐요."
          if not editing else "✅ 고친 내용을 저장했어요!")
    ss.celebrate = not editing
    st.rerun()


def page_write(entries: list[dict], counts: Counter):
    if not ss.me:
        login_box("먼저 내 이름으로 들어가요")
        return
    on_enter_write()
    d = ss.draft
    editing = ss.edit_id is not None
    mine = [e for e in entries if e["student_name"] == ss.me]
    today = today_kst()

    if editing:
        md(f'<div class="daybar"><span class="big">✏️ {fmt_date(d["entry_date"].isoformat())} 기록을 고치는 중이에요</span>'
           '<span class="small">고친 다음 맨 아래 저장 버튼을 꼭 눌러요.</span></div>')
        st.button("고치기 그만두기", on_click=reset_form, key="cancel_edit")
    else:
        md(f'<div class="daybar"><span class="big">📅 {today.year}년 {fmt_date(today.isoformat())}</span>'
           f'<span class="small">{esc(ss.me)}의 <b>{len(mine) + 1}번째</b> 아롱다롱 · '
           '오늘의 아까운 Wrong은 무엇이었나요?</span></div>')

    sec_header("0", "오늘의 실패에 이름 붙이기", "한 줄로 짧게 말하면?")
    c1, c2 = st.columns([1, 2.6])
    with c1:
        bind_date()
    with c2:
        bind_text("title", "🏷️ 실패 제목", "예) 아침에 우유를 쏟았어요", 40)

    sec_header("1", "육하원칙으로 써요", "누가 · 언제 · 어디서 · 무엇을 · 어떻게 · 왜")
    row1 = st.columns(3)
    for col, (f, label, ph) in zip(row1, W_FIELDS[:3]):
        with col:
            bind_text(f, label, ph, 60)
    row2 = st.columns(3)
    for col, (f, label, ph) in zip(row2, W_FIELDS[3:]):
        with col:
            bind_text(f, label, ph, 200, area=True, height=100)

    sec_header("2", "그림으로 그려요", "실패한 그 장면을 그려 봐요")
    drawing_block()

    sec_header("3", "해결 방법을 찾아요", "다음에 똑같은 일이 생기면 어떻게 할까?")
    bind_text("solution", "🔧 해결 방법", "예) 컵은 식탁 안쪽에 놓고, 아침에는 천천히 움직인다.", 500,
              area=True, height=110)

    sec_header("4", "배느실을 써요", "배운 점 · 느낀 점 · 실천할 점")
    row3 = st.columns(3)
    for col, (f, label, ph, _) in zip(row3, BNS_FIELDS):
        with col:
            bind_text(f, label, ph, 400, area=True, height=130)

    sec_header("5", "사진이나 그림 붙이기", "선택 — 실패와 관련된 사진, 미리 그려 둔 그림")
    md('<div class="tip">🙈 친구 얼굴이나 내 얼굴이 크게 나온 사진은 올리지 않아요. 물건·장소·내 그림 사진이 좋아요!</div>')
    photo_block()

    st.write("")
    done, total, missing = completeness(d)
    plant = "🌱" if done < total * 0.5 else ("🌿" if done < total else "🌳")
    st.progress(done / total, text=f"{plant} 발표 준비도 {done}/{total}")
    if missing:
        st.caption("아직 비어 있는 칸: " + ", ".join(missing))
    need = [FIELD_NAMES[f] for f in REQUIRED if not (d.get(f) or "").strip()]
    label = "💾 고친 내용 저장하기" if editing else "💾 오늘의 아롱다롱 저장하기"
    if st.button(label, type="primary", key="save_btn", **WIDE_BTN):
        if need:
            st.error("꼭 써야 하는 칸이 비어 있어요: " + ", ".join(need))
        else:
            save_entry()


# =============================================================================
# 📒 내 실패 노트
# =============================================================================
def page_note(entries: list[dict], counts: Counter):
    if not ss.me:
        login_box("내 이름으로 들어가면 내 실패 노트를 볼 수 있어요")
        return
    mine = [e for e in entries if e["student_name"] == ss.me]
    hearts = sum(counts.get(e["id"], 0) for e in mine)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📒 실패 기록", f"{len(mine)}개")
    m2.metric("📅 기록한 날", f"{len({e['entry_date'] for e in mine})}일")
    m3.metric("💛 받은 응원", f"{hearts}개")
    m4.metric("⭐ 대표 실패", f"{sum(1 for e in mine if e['featured'])}개")

    with st.expander("🔗 내 발표 화면 링크 (발표회 날 이 링크를 열면 바로 발표 화면이 나와요)"):
        st.code(make_link(**{"class": ss.class_id, "view": "show", "student": ss.me}), language=None)
        st.caption("⭐ 대표 실패로 뽑은 기록만 골라서 발표할 수도 있어요.")

    if not mine:
        st.info("아직 기록이 없어요. '✏️ 실패 쓰기'에서 첫 아롱다롱을 남겨 봐요!")
        st.button("✏️ 첫 실패 쓰러 가기", on_click=go, args=("write",), type="primary")
        return

    for idx, e in enumerate(mine):
        number = len(mine) - idx
        with st.container(border=True):
            c1, c2 = st.columns([1, 2.3], gap="medium")
            with c1:
                show_thumb(e)
            with c2:
                md(entry_head_html(e, counts.get(e["id"], 0), number))
                b1, b2, b3, b4 = st.columns(4)
                b1.button("☆ 대표에서 빼기" if e["featured"] else "⭐ 대표로 뽑기", key=f"feat_{e['id']}",
                          on_click=toggle_featured, args=(e,), **WIDE_BTN)
                b2.button("✏️ 고치기", key=f"edit_{e['id']}", on_click=start_edit, args=(e,), **WIDE_BTN)
                b3.button("🔎 자세히", key=f"ndet_{e['id']}", on_click=open_detail, args=(e["id"],), **WIDE_BTN)
                b4.button("🗑️ 지우기", key=f"del_{e['id']}", on_click=ask_confirm, args=("del", e["id"]),
                          **WIDE_BTN)
                if ss.confirm == ("del", e["id"]):
                    st.warning("정말 지울까요? 지우면 되돌릴 수 없어요.")
                    y, n, _ = st.columns([1, 1, 2])
                    y.button("네, 지울래요", key=f"dely_{e['id']}", on_click=delete_entry, args=(e,), type="primary")
                    n.button("아니요", key=f"deln_{e['id']}", on_click=clear_confirm)


# =============================================================================
# 🖼️ 실패 갤러리
# =============================================================================
def guard_choice(key: str, options: list):
    if key in ss and ss[key] not in options:
        del ss[key]


def page_gallery(entries: list[dict], counts: Counter, by_voter: dict):
    if not ss.me:
        with st.expander("🙋 친구의 실패에 💛 투표하려면 내 이름으로 들어가요"):
            login_box("내 이름으로 들어가기")
    if not entries:
        st.info("아직 우리 반 기록이 없어요. 첫 번째 아롱다롱의 주인공이 되어 볼까요?")
        return
    today_iso = today_kst().isoformat()
    today_writers = {e["student_name"] for e in entries if e["entry_date"] == today_iso}
    md(f'<div class="daybar"><span class="big">🖼️ {class_label(ss.class_id)} 실패 갤러리</span>'
       f'<span class="small">전체 {len(entries)}개 · 오늘 기록한 친구 {len(today_writers)}명 · '
       '마음에 드는 실패에 💛를 눌러 응원해요!</span></div>')

    dates = sorted({e["entry_date"] for e in entries}, reverse=True)
    names = sorted({e["student_name"] for e in entries})
    date_opts = ["전체 날짜"] + dates
    name_opts = ["모든 친구"] + names
    sort_opts = ["🆕 최신순", "💛 응원 많은 순"]
    guard_choice("g_date", date_opts)
    guard_choice("g_name", name_opts)
    f1, f2, f3 = st.columns([1, 1, 1.2], vertical_alignment="bottom")
    pick_date = f1.selectbox("📅 날짜", date_opts, key="g_date", on_change=reset_gallery_page,
                             format_func=lambda x: x if x == "전체 날짜" else
                             fmt_date(x) + (" · 오늘" if x == today_iso else ""))
    pick_name = f2.selectbox("🙋 친구", name_opts, key="g_name", on_change=reset_gallery_page)
    pick_sort = f3.radio("정렬", sort_opts, key="g_sort", horizontal=True, on_change=reset_gallery_page)

    shown = [e for e in entries
             if (pick_date == "전체 날짜" or e["entry_date"] == pick_date)
             and (pick_name == "모든 친구" or e["student_name"] == pick_name)]
    if pick_sort == sort_opts[1]:
        shown.sort(key=lambda e: (counts.get(e["id"], 0), e["entry_date"], e["id"]), reverse=True)
    if not shown:
        st.info("조건에 맞는 기록이 없어요.")
        return

    pages = (len(shown) - 1) // PER_PAGE + 1
    ss.gal_page = min(ss.gal_page, pages - 1)
    chunk = shown[ss.gal_page * PER_PAGE:(ss.gal_page + 1) * PER_PAGE]
    my_votes = by_voter.get(ss.me, set()) if ss.me else set()
    for start in range(0, len(chunk), 3):
        cols = st.columns(3, gap="medium")
        for col, e in zip(cols, chunk[start:start + 3]):
            with col:
                with st.container(border=True):
                    show_thumb(e)
                    md(f'<div class="ctitle">{esc(e["title"]) or "(제목 없음)"}</div>'
                       f'<div class="cmeta">🙋 {esc(e["student_name"])} · 📅 {fmt_date(e["entry_date"])}'
                       f'{" · ⭐" if e["featured"] else ""}</div>')
                    b1, b2 = st.columns([1.35, 1])
                    with b1:
                        vote_button(e, counts, my_votes, key=f"gv_{e['id']}")
                    with b2:
                        st.button("🔎 자세히", key=f"gd_{e['id']}", on_click=open_detail, args=(e["id"],),
                                  **WIDE_BTN)
    if pages > 1:
        p1, p2, p3 = st.columns([1, 2, 1], vertical_alignment="center")
        p1.button("◀ 앞 쪽", key="gal_prev", disabled=ss.gal_page == 0,
                  on_click=lambda: ss.update(gal_page=ss.gal_page - 1), **WIDE_BTN)
        p2.markdown(f'<div class="slidecount">{ss.gal_page + 1} / {pages} 쪽</div>', unsafe_allow_html=True)
        p3.button("다음 쪽 ▶", key="gal_next", disabled=ss.gal_page >= pages - 1,
                  on_click=lambda: ss.update(gal_page=ss.gal_page + 1), **WIDE_BTN)


# =============================================================================
# 🏆 좋은 실패 순위
# =============================================================================
def page_rank(entries: list[dict], counts: Counter):
    if not entries:
        st.info("아직 기록이 없어서 순위가 없어요.")
        return
    voted = [e for e in entries if counts.get(e["id"], 0) > 0]
    voted.sort(key=lambda e: (-counts.get(e["id"], 0), e["entry_date"], e["id"]))
    md('<div class="sec"><span class="t">🏆 친구들이 뽑은 좋은 실패 TOP 10</span>'
       '<span class="d">💛를 많이 받은 실패예요. 무엇을 배웠는지 함께 살펴봐요!</span></div>')
    if not voted:
        st.info("아직 💛 투표가 없어요. 갤러리에서 친구의 좋은 실패를 응원해 봐요!")
    else:
        medals = ["🥇", "🥈", "🥉"]
        podium = st.columns(3, gap="medium")
        for col, medal, e in zip(podium, medals, voted[:3]):
            with col:
                with st.container(border=True):
                    md(f'<div class="medal">{medal}</div>')
                    show_thumb(e)
                    md(f'<div class="ctitle">{esc(e["title"])}</div>'
                       f'<div class="cmeta">🙋 {esc(e["student_name"])} · 💛 {counts.get(e["id"], 0)}</div>')
                    st.button("🔎 자세히", key=f"rk_{e['id']}", on_click=open_detail, args=(e["id"],),
                              **WIDE_BTN)
        for i, e in enumerate(voted[3:10], start=4):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.markdown(f'<div class="rankrow"><span class="n">{i}</span><span class="t"><b>{esc(e["title"])}</b>'
                        f' · {esc(e["student_name"])} · {fmt_short(e["entry_date"])}</span>'
                        f'<span class="v">💛 {counts.get(e["id"], 0)}</span></div>', unsafe_allow_html=True)
            c2.button("🔎", key=f"rk_{e['id']}", help="자세히 보기", on_click=open_detail, args=(e["id"],))

    per = defaultdict(lambda: {"hearts": 0, "count": 0, "days": set()})
    for e in entries:
        s = per[e["student_name"]]
        s["hearts"] += counts.get(e["id"], 0)
        s["count"] += 1
        s["days"].add(e["entry_date"])
    left, right = st.columns(2, gap="large")
    with left:
        md('<div class="sec"><span class="t">💛 응원을 가장 많이 받은 친구</span></div>')
        ranked = sorted(per.items(), key=lambda kv: (-kv[1]["hearts"], kv[0]))[:10]
        rows = "".join(
            f'<div class="rankrow"><span class="n">{i}</span><span class="t">{esc(name)}</span>'
            f'<span class="v">💛 {s["hearts"]}</span></div>'
            for i, (name, s) in enumerate(ranked, start=1) if s["hearts"] > 0
        )
        md(rows or '<div class="cmeta">아직 응원을 받은 친구가 없어요.</div>')
    with right:
        md('<div class="sec"><span class="t">📅 꾸준히 기록한 친구</span></div>')
        ranked = sorted(per.items(), key=lambda kv: (-len(kv[1]["days"]), -kv[1]["count"], kv[0]))[:10]
        rows = "".join(
            f'<div class="rankrow"><span class="n">{i}</span><span class="t">{esc(name)}</span>'
            f'<span class="v">📅 {len(s["days"])}일 · 📒 {s["count"]}개</span></div>'
            for i, (name, s) in enumerate(ranked, start=1)
        )
        md(rows)


# =============================================================================
# 🎤 발표 모드
# =============================================================================
def cover_html(name: str, items: list[dict], hearts: int, featured_only: bool) -> str:
    dates = sorted(e["entry_date"] for e in items)
    span = f"{fmt_short(dates[0])} ~ {fmt_short(dates[-1])}" if dates else ""
    first = date.fromisoformat(dates[0]) if dates else None
    last = date.fromisoformat(dates[-1]) if dates else None
    period = (f"{first.month}월 {first.day}일부터 {last.month}월 {last.day}일까지 " if first and first != last
              else (f"{first.month}월 {first.day}일에 " if first else ""))
    if featured_only:
        middle = f"그중에서 제가 고른 대표 실패 {len(items)}개를 소개할게요!"
    else:
        middle = f"{period}{len(items)}개의 아까운 Wrong을 기록했어요."
    script = (f'안녕하세요! 저는 {class_label(ss.class_id)} <b>{esc(name)}</b>입니다. {middle} '
              '실패는 아깝지만, 많을수록(多) 더 많이 배울 수 있어요. 지금부터 제 실패 이야기를 들려드릴게요!')
    return (
        '<div class="cover">'
        f'<div class="cover-kicker">{SCHOOL_SHORT} {class_label(ss.class_id)} · 아롱다롱 프로젝트 발표회</div>'
        f'<div class="cover-title"><span class="who">{esc(name)}</span>의<br>아까운 Wrong 이야기</div>'
        '<div class="cover-chips">'
        f'<span>📒 실패 기록 {len(items)}개</span><span>💛 받은 응원 {hearts}개</span>'
        f'{f"<span>📅 {span}</span>" if span else ""}'
        '</div>'
        f'<div class="script"><b>🎤 이렇게 시작해요</b><br>"{script}"</div>'
        '</div>'
    )


def ending_html(name: str, items: list[dict]) -> str:
    pledges = [e["action"] for e in sorted(items, key=lambda x: x["entry_date"], reverse=True) if e["action"]][:6]
    lis = "".join(f"<li>🏃 {esc(p)}</li>" for p in pledges) or "<li>🏃 실패해도 다시 도전하기!</li>"
    return (
        '<div class="cover">'
        '<div class="cover-kicker">마무리</div>'
        '<div class="cover-title">나의 실천 다짐</div>'
        f'<ul class="pledges">{lis}</ul>'
        '<div class="script"><b>🎤 이렇게 마무리해요</b><br>"제 실패 이야기를 들어주셔서 감사합니다! '
        '아까운 Wrong도 많이 모이면 우리를 키워 줘요. 여러분도 실패를 두려워하지 마세요!"</div>'
        '</div>'
    )


def render_slide(kind: str, payload, name: str, items: list[dict], counts: Counter, featured_only: bool):
    if kind == "cover":
        md(cover_html(name, items, sum(counts.get(e["id"], 0) for e in items), featured_only))
    elif kind == "end":
        md(ending_html(name, items))
    else:
        number, e = payload
        render_entry(e, counts.get(e["id"], 0), number, big=True)
        md('<div class="speak">🎤 말하는 순서: 제목 → 육하원칙 → 그림 설명 → 해결 방법 → 배느실</div>')


def page_show(entries: list[dict], counts: Counter):
    names = sorted({e["student_name"] for e in entries})
    if not names:
        st.info("아직 발표할 기록이 없어요.")
        return
    default = ss.show_student if ss.show_student in names else (ss.me if ss.me in names else None)
    guard_choice("show_sel", names)
    if "show_sel" not in ss and default:
        ss.show_sel = default

    with st.container(border=True):
        c1, c2, c3 = st.columns([1.3, 1, 1.6], vertical_alignment="bottom")
        name = c1.selectbox("🎤 발표할 친구", names, key="show_sel", index=None,
                            placeholder="이름을 골라요", on_change=lambda: ss.update(slide=0))
        featured_only = c2.toggle("⭐ 대표 실패만", key="show_feat", on_change=lambda: ss.update(slide=0))
        mode = c3.radio("보기 방법", ["📽️ 한 장씩 넘기기", "📜 한눈에 보기 (인쇄용)"], key="show_mode",
                        horizontal=True)
    ss.show_student = name
    if not name:
        st.info("위에서 발표할 친구의 이름을 골라요.")
        return

    mine = sorted([e for e in entries if e["student_name"] == name], key=lambda e: (e["entry_date"], e["id"]))
    numbered = list(enumerate(mine, start=1))
    if featured_only:
        picked = [(n, e) for n, e in numbered if e["featured"]]
        if not picked:
            st.warning("아직 ⭐ 대표 실패가 없어요. '📒 내 실패 노트'에서 대표로 뽑을 수 있어요. 지금은 전체를 보여 줄게요.")
            featured_only = False
        else:
            numbered = picked
    items = [e for _, e in numbered]
    slides = [("cover", None)] + [("entry", ne) for ne in numbered] + [("end", None)]

    with st.expander("🔗 이 발표 화면 바로가기 링크"):
        st.code(make_link(**{"class": ss.class_id, "view": "show", "student": name}), language=None)
        st.caption("이 링크를 열면 이 친구의 발표 화면이 바로 나와요. 화면을 크게 보려면 F11(전체 화면)을 눌러요.")

    if mode.startswith("📽️"):
        ss.slide = min(ss.slide, len(slides) - 1)
        i = ss.slide

        def nav_row(suffix: str):
            n1, n2, n3 = st.columns([1, 2, 1], vertical_alignment="center")
            n1.button("◀ 이전", key=f"prev_{suffix}", disabled=i == 0, on_click=step_slide, args=(-1,), **WIDE_BTN)
            n2.markdown(f'<div class="slidecount">{i + 1} / {len(slides)}</div>', unsafe_allow_html=True)
            n3.button("다음 ▶", key=f"next_{suffix}", disabled=i >= len(slides) - 1, on_click=step_slide,
                      args=(1,), type="primary", **WIDE_BTN)

        nav_row("top")
        kind, payload = slides[i]
        render_slide(kind, payload, name, items, counts, featured_only)
        st.write("")
        nav_row("bottom")
    else:
        st.caption("🖨️ Ctrl+P(맥은 ⌘+P)를 누르면 PDF로 저장하거나 인쇄할 수 있어요.")
        for kind, payload in slides:
            render_slide(kind, payload, name, items, counts, featured_only)
            st.divider()


# =============================================================================
# 🔒 선생님
# =============================================================================
def page_teacher(entries: list[dict], counts: Counter):
    password = secret("TEACHER_PASSWORD")
    if not password and store.mode == "local":
        password = LOCAL_TEACHER_PASSWORD
    if not password:
        st.warning("Secrets에 TEACHER_PASSWORD를 넣으면 선생님 화면을 쓸 수 있어요. (설치 안내서 참고)")
        teacher_health()
        return
    if not ss.teacher_ok:
        with st.container(border=True):
            st.markdown("#### 🔒 선생님 확인")
            if store.mode == "local" and not secret("TEACHER_PASSWORD"):
                st.caption(f"임시 저장 모드의 임시 비밀번호: `{LOCAL_TEACHER_PASSWORD}` — 실제 수업 전에 꼭 바꿔 주세요.")
            with st.form("teacher_form"):
                value = st.text_input("선생님 비밀번호", type="password")
                if st.form_submit_button("확인"):
                    if value == str(password):
                        ss.teacher_ok = True
                        st.rerun()
                    st.error("비밀번호가 달라요.")
        return

    top1, top2 = st.columns([4, 1], vertical_alignment="center")
    top1.markdown(f"#### 👩‍🏫 {class_label(ss.class_id)} 관리")
    top2.button("🔒 잠그기", on_click=lambda: ss.update(teacher_ok=False), **WIDE_BTN)
    t1, t2, t3, t4 = st.tabs(["🙋 학생", "🗂️ 기록 관리", "📥 내려받기", "🔧 연결 상태·링크"])

    with t1:
        try:
            students = store.list_students(ss.class_id)
        except StoreError as exc:
            st.error(str(exc))
            students = []
        registered = {s["name"] for s in students}
        names = sorted(registered | {e["student_name"] for e in entries})
        if not names:
            st.info("아직 들어온 학생이 없어요.")
        st.caption("학생이 비밀번호를 잊어버리면 '비밀번호 초기화'를 눌러요. 기록은 그대로 남고, 다음에 들어올 때 새 비밀번호를 정해요.")
        for nm in names:
            mine = [e for e in entries if e["student_name"] == nm]
            c1, c2, c3 = st.columns([2, 3, 1.6], vertical_alignment="center")
            c1.markdown(f"**{nm}**" + ("" if nm in registered else " · (비밀번호 없음)"))
            c2.caption(f"📒 {len(mine)}개 · 📅 {len({e['entry_date'] for e in mine})}일 · "
                       f"💛 {sum(counts.get(e['id'], 0) for e in mine)}개")
            if nm in registered:
                if ss.confirm == ("pin", nm):
                    y, n = c3.columns(2)
                    y.button("초기화", key=f"piny_{nm}", on_click=reset_student_pin, args=(nm,), type="primary")
                    n.button("취소", key=f"pinn_{nm}", on_click=clear_confirm)
                else:
                    c3.button("🔑 비밀번호 초기화", key=f"pin_{nm}", on_click=ask_confirm, args=("pin", nm))

    with t2:
        if not entries:
            st.info("아직 기록이 없어요.")
        st.caption("알맞지 않은 내용이 있으면 지울 수 있어요. 지운 기록은 되돌릴 수 없어요.")
        for e in entries:
            c1, c2 = st.columns([5, 1.2], vertical_alignment="center")
            c1.markdown(f"{fmt_short(e['entry_date'])} · **{esc(e['student_name'])}** · {esc(e['title'])} "
                        f"· 💛 {counts.get(e['id'], 0)}", unsafe_allow_html=True)
            if ss.confirm == ("tdel", e["id"]):
                y, n = c2.columns(2)
                y.button("삭제", key=f"tdy_{e['id']}", on_click=delete_entry, args=(e,), type="primary")
                n.button("취소", key=f"tdn_{e['id']}", on_click=clear_confirm)
            else:
                c2.button("🗑️ 지우기", key=f"td_{e['id']}", on_click=ask_confirm, args=("tdel", e["id"]))

    with t3:
        buf = io.StringIO()
        writer = csv.writer(buf)
        header = ["날짜", "이름", "제목"] + [label.split(" ", 1)[1] for _, label, _ in W_FIELDS] + \
                 ["해결 방법"] + [label.split(" ", 1)[1] for _, label, _, _ in BNS_FIELDS] + ["받은 응원", "대표 실패"]
        writer.writerow(header)
        for e in sorted(entries, key=lambda x: (x["entry_date"], x["student_name"])):
            writer.writerow([e["entry_date"], e["student_name"], e["title"]] + [e[f] for f, _, _ in W_FIELDS] +
                            [e["solution"]] + [e[f] for f, _, _, _ in BNS_FIELDS] +
                            [counts.get(e["id"], 0), "⭐" if e["featured"] else ""])
        st.download_button("📥 우리 반 기록 전체 (엑셀에서 열리는 CSV)", data=buf.getvalue().encode("utf-8-sig"),
                           file_name=f"아롱다롱_{class_label(ss.class_id)}_{today_kst().isoformat()}.csv",
                           mime="text/csv", **WIDE_DL)
        st.caption("그림과 사진은 각 학생의 발표 화면에서 볼 수 있어요.")

    with t4:
        teacher_health()
        st.markdown("##### 🔗 반별 바로가기 링크")
        st.caption("학생들에게 우리 반 링크를 나눠 주면 반이 미리 골라진 채로 열려요.")
        for cid in CLASSES:
            st.code(f"{class_label(cid)}  {make_link(**{'class': cid, 'view': 'write'})}", language=None)


def teacher_health():
    st.markdown("##### 🔧 저장소 연결 상태")
    if store.mode == "local":
        st.warning("지금은 **임시 저장 모드**예요. 이 컴퓨터(서버) 안에만 저장돼서, Streamlit 무료 서버가 잠들거나 "
                   "다시 시작하면 기록이 사라질 수 있어요. 실제 수업 전에 Supabase를 연결해 주세요.")
    try:
        checks = store.health()
    except Exception as exc:  # noqa: BLE001
        st.error(f"점검하지 못했어요: {exc}")
        return
    for label, ok, detail in checks:
        st.markdown(f"{'✅' if ok else '❌'} {label}" + (f" — `{detail}`" if detail and not ok else ""))
    if store.mode == "supabase" and not all(ok for _, ok, _ in checks):
        st.info("❌ 표시가 있으면 Supabase의 SQL Editor에서 supabase_setup.sql을 실행했는지 확인해 주세요.")


# =============================================================================
# 시작
# =============================================================================
def load_data(page: str):
    try:
        return cached_entries(ss.class_id), cached_votes(ss.class_id)
    except StoreError as exc:
        st.error("저장소에서 기록을 불러오지 못했어요. 선생님께 알려 주세요.")
        with st.expander("자세한 오류 (선생님용)"):
            st.code(str(exc), language=None)
        if page != "teacher":
            st.stop()
        return [], []


def main():
    init_state()
    md(CSS)
    gate_access()
    page = LABEL_PAGE.get(ss.nav, "write")
    render_header(compact=(page == "show"))
    top_bar()
    page = LABEL_PAGE.get(ss.nav, "write")
    sync_query_params(page)
    show_messages()

    entries, votes = load_data(page)
    counts, by_voter = vote_index(votes)

    if page == "write":
        page_write(entries, counts)
    elif page == "note":
        page_note(entries, counts)
    elif page == "gallery":
        page_gallery(entries, counts, by_voter)
    elif page == "rank":
        page_rank(entries, counts)
    elif page == "show":
        page_show(entries, counts)
    else:
        page_teacher(entries, counts)

    if ss.get("open_detail"):
        entry_id = ss.open_detail
        ss.open_detail = None
        detail_dialog(entry_id)

    note = " · 💾 임시 저장 모드" if store.mode == "local" else ""
    md(f'<div class="foot noprint">🌈 {SCHOOL_SHORT} 아롱다롱 프로젝트 — 아까운 Wrong, 多 Wrong!{note}</div>')
    ss.last_page = page


main()
