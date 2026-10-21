# 🌈 아라초 아롱다롱 프로젝트

**아**까운 **Wrong**, **多**(많을 다) **Wrong**! — 아까운 실패가 많을수록, 우리는 더 많이 배워요.

학생들이 매일의 실패를 기록하고, 친구들의 '좋은 실패'에 투표하고, 발표회에서 그대로 발표하는 Streamlit 앱입니다.

---

## 무엇을 할 수 있나요?

| 화면 | 하는 일 |
|---|---|
| ✏️ 실패 쓰기 | 날짜 · 실패 제목 · **육하원칙** · **그림판**(색깔/굵기/지우개/기분 스탬프/되돌리기) · **해결 방법** · **배느실** · 사진/그림 파일(최대 3장, 카메라 촬영 가능) · 발표 준비도 막대 |
| 📒 내 실패 노트 | 내 기록 모아 보기, 고치기, 지우기, ⭐ 대표 실패 뽑기, **내 발표 링크** 복사 |
| 🖼️ 실패 갤러리 | 우리 반 기록을 날짜·친구별로 보기, **💛 좋은 실패 투표** (한 기록에 한 표, 내 것은 투표 불가, 다시 누르면 취소) |
| 🏆 좋은 실패 순위 | 좋은 실패 TOP 10, 응원을 많이 받은 친구, 꾸준히 기록한 친구 |
| 🎤 발표 모드 | 표지(첫인사 대본) → 실패 한 장씩 → 실천 다짐(마무리 대본). **링크 하나로 바로 열림**, ⭐ 대표 실패만 골라 보기, 한눈에 보기(인쇄·PDF) |
| 🔒 선생님 | 학생 비밀번호 초기화, 기록 지우기, 반 전체 기록 CSV(엑셀) 내려받기, 저장소 연결 점검, 반별 링크 |

- 반 선택: 1학년 1반, 2학년 1반, 2학년 2반, 3학년 1반, 4학년 1반, 4학년 2반, 5학년 1반, 6학년 1반 (기본: 5학년 1반)
- 학생은 **이름 + 나만 아는 숫자 4개**로 들어옵니다. 처음 들어올 때 자동으로 등록돼요. 잊어버리면 선생님 화면에서 초기화합니다.

---

## 설치하기 (약 20분, 모두 무료)

Streamlit 무료 서버는 한동안 안 쓰면 잠들고, 깨어날 때 서버 안의 파일이 지워집니다. 그래서 기록·그림·사진·투표는 **Supabase(무료 클라우드 데이터베이스)**에 저장합니다.

### 1단계 · Supabase 준비

1. [supabase.com](https://supabase.com) → **Start your project** → GitHub 계정으로 가입
2. **New project** → 이름 `arongdarong`, Database Password는 아무거나(따로 적어 두기), Region은 **Northeast Asia (Seoul)** → Create
3. 만들어지면 왼쪽 메뉴 **SQL Editor** → **New query** → 이 폴더의 `supabase_setup.sql` 내용을 전부 붙여 넣고 **Run** → "Success" 확인
4. 두 가지 값을 복사해 둡니다.
   - **Project URL**: 프로젝트 화면 위쪽 **Connect** 버튼, 또는 Project Settings → Data API (`https://….supabase.co`)
   - **Secret key**: Project Settings → **API Keys** → Secret keys (`sb_secret_…`로 시작. 예전 프로젝트는 Legacy 탭의 `service_role` 키도 됩니다)
   - ⚠️ Secret key는 학생이나 다른 사람에게 보여 주지 마세요.

### 2단계 · GitHub에 올리기

1. [github.com](https://github.com) → **New repository** → 이름 `arongdarong` → **Private** 권장 → Create
2. **uploading an existing file** 링크 → 압축을 푼 폴더 안의 파일과 폴더를 모두 끌어다 놓기 → **Commit changes**
3. **`.streamlit/config.toml`이 올라갔는지 꼭 확인**하세요. 점(.)으로 시작하는 폴더는 컴퓨터에서 숨겨져 빠지기 쉽습니다.
   없으면 **Add file → Create new file** → 파일 이름에 `.streamlit/config.toml` → 아래 내용 붙여 넣기 → Commit

   ```toml
   [theme]
   base = "light"
   primaryColor = "#f26b5b"
   backgroundColor = "#fffbf3"
   secondaryBackgroundColor = "#fff1de"
   textColor = "#2d2a32"

   [server]
   maxUploadSize = 20
   ```

### 3단계 · Streamlit에 배포

1. [share.streamlit.io](https://share.streamlit.io) → **Create app** → GitHub 저장소 `arongdarong`, Branch `main`, Main file `app.py`
2. App URL에 원하는 주소 (예: `ara-arongdarong`)
3. **Advanced settings → Secrets** 칸에 `.streamlit/secrets.toml.example`의 내용을 붙여 넣고 값을 바꿉니다.

   ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "sb_secret_..."
   TEACHER_PASSWORD = "선생님만-아는-비밀번호"
   # ACCESS_CODE = "0507"   # (선택) 넣으면 링크를 연 사람이 입장 코드를 넣어야 들어와요
   # APP_URL = "https://ara-arongdarong.streamlit.app"   # (선택) 공유 링크 주소 고정
   ```
4. **Deploy** → 앱이 열리면 **🔒 선생님 → 🔧 연결 상태·링크**에서 ✅ 네 개가 뜨는지 확인합니다.

> Secrets를 넣기 전에도 앱은 **임시 저장 모드**로 돌아갑니다(연습용). 이때 선생님 화면 임시 비밀번호는 `arong1234`입니다.

---

## 학생들에게 나눠 줄 링크

- 우리 반 바로가기: `https://앱주소.streamlit.app/?class=5-1`
- 한 학생의 발표 화면: `https://앱주소.streamlit.app/?class=5-1&view=show&student=김민준`
  (학생은 **📒 내 실패 노트 → 🔗 내 발표 화면 링크**에서, 선생님은 발표 모드에서 복사할 수 있어요)
- 반 코드: `1-1` `2-1` `2-2` `3-1` `4-1` `4-2` `5-1` `6-1`

## 수업 흐름 예시

1. **첫날**: 링크 접속 → 이름과 숫자 4개 정하기
2. **매일**: ✏️ 실패 쓰기 — 꼭 쓸 칸은 *실패 제목 · 무엇을 · 해결 방법*. 나머지는 '발표 준비도' 막대를 보며 채워요.
3. **친구 실패 읽기**: 🖼️ 갤러리에서 읽고 배울 점이 있는 실패에 💛
4. **발표회 준비**: 📒 내 실패 노트에서 ⭐ 대표 실패 2~3개 고르기 → 🎤 발표 모드에서 '⭐ 대표 실패만' 켜고 연습
5. **발표회**: 내 발표 링크 열기 → F11(전체 화면) → ◀ ▶로 넘기며 화면에 나온 대본과 순서대로 발표

## 알아두면 좋은 점

- **개인정보**: 쓰기 화면에 "얼굴이 크게 나온 사진은 올리지 않기" 안내가 있습니다. 사진 보관함은 비공개이고, 학생 비밀번호는 암호화해서 저장합니다. 외부인이 보는 것이 걱정되면 Secrets에 `ACCESS_CODE`를 넣으세요.
- **무료 한도**: Supabase 무료 플랜은 데이터베이스 500MB, 파일 1GB입니다. 사진은 자동으로 줄여서 저장하므로 한 반이 한 학기 쓰기에 넉넉합니다.
- **방학 중 일시정지**: Supabase 무료 프로젝트는 1주일 넘게 아무도 안 쓰면 일시정지됩니다. 기록은 지워지지 않고, Supabase 대시보드에서 **Restore**를 누르면 다시 켜집니다.
- **앱이 잠들었을 때**: Streamlit 앱도 오래 안 쓰면 잠듭니다. 첫 접속 때 나오는 깨우기 버튼을 누르면 1분 안에 다시 열리고, 기록은 Supabase에 있어서 그대로입니다.
- **학교 이름·반 목록 바꾸기**: `app.py` 맨 위 `SCHOOL_SHORT`, `CLASSES` 값을 고치면 됩니다.

## 파일 구성

```
app.py                     앱 화면 전체
arong/store.py             저장소 (Supabase / 임시 저장)
arong/media.py             사진 줄이기·그림 변환
arong/theme.py             화면 꾸미기
drawing_canvas/index.html  그림판
supabase_setup.sql         Supabase 준비용 SQL
requirements.txt           필요한 패키지
.streamlit/config.toml     색깔 테마
.streamlit/secrets.toml.example  비밀 값 예시
```
