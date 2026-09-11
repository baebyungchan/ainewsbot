# AI News Bot

GitHub에서 별이 급증하는 AI 저장소, Reddit·Hacker News에서 화제가 된 AI 글, 화제가 된 X 게시물, OpenAI·Anthropic·DeepMind 등의 공식 블로그 새 글을 골라 **텔레그램**으로 보내 주는 개인용 봇입니다.

서버가 없습니다. **GitHub Actions**가 15분마다 이 저장소의 코드를 잠깐 실행하고 끝냅니다. 노트북을 꺼 놔도 돕니다.

```
GitHub Trending ─┐
GitHub 신규 저장소 ─┤
Reddit (6개 서브) ─┼─ 기준 통과 ─ 중복 제거 ─ 처음 보는 것만 ─ 대기열 ─ 최대 12건/회 ─ 텔레그램
Hacker News ──────┤                                                     │
공식 블로그 RSS ──┘                                    state/state.json 에 기록 (자동 커밋)
X: HN/Reddit에 올라온 x.com 링크의 본문을 fxtwitter API로 붙임
```

## 어떤 게 "중요한" 소식인가

| 소스 | 기준 (기본값) | 표시 |
|---|---|---|
| GitHub Trending (일간) | 오늘 별 **+500** 이상이면서 AI 관련, 또는 주제 무관 **+2,000** 이상 | `★ +3,854 today · 37,063 total · Python` |
| GitHub 신규 저장소 | 만든 지 **14일** 이내에 별 **500** 이상 (검색어: llm/agent/ai/gpt/claude) | `🆕 2,664 stars in 9d · Python` |
| Reddit | OAuth 사용 시 서브레딧별 추천수 기준 (`newsbot/sources.py`). 미사용 시 통합 피드의 오늘 상위 5개 | `▲ 812 · r/LocalLLaMA · 💬 140` |
| Hacker News | 36시간 내 **100점** 이상이면서 AI 키워드 포함 | `🟠 HN 1,138 pts · 💬 441 · 토론` |
| 공식 블로그 | 48시간 내 새 글 전부 (OpenAI, Anthropic, DeepMind, Google AI, Hugging Face, Qwen, Mistral) | `📰 OpenAI` |
| 연구소 블로그 | Google Research(AI만), Microsoft Research(AI만), Apple ML Research | `🔬 Apple ML Research` |
| 뉴스레터·블로그·영상 | TLDR AI(일간), Interconnects, Ahead of AI, Lil'Log, Simon Willison, GeekNews(AI 관련만), AI Explained(YouTube) | `🗞 TLDR AI` |
| Hugging Face 논문 | Daily Papers 중 추천 **15** 이상 | `📄 논문 ▲ 42 · 저자` |
| Hugging Face 모델 | 트렌딩 상위 **5** | `🤗 트렌딩 #1 · ❤ 1,047 · ⬇ 6` |
| X | HN·Reddit에서 화제가 된 x.com 게시물의 본문·작성자·좋아요 | `𝕏 @OpenAI · ❤ 12,000` |

같은 링크가 여러 곳에서 잡히면 하나로 합치고 토론 링크를 붙입니다. GitHub 저장소는 한 번 보낸 뒤 별이 **3배** 이상 늘면 한 번 더 알립니다. 한국시간 **00~08시**에는 보내지 않고 모아 뒀다가 아침에 보냅니다.

## 설치 (10분)

### 1. 저장소 올리기

```bash
cd AINewsBot
git init && git add -A && git commit -m "init"
gh repo create ainewsbot --private --source . --push
```

공개 저장소로 하면 Actions 실행 시간이 무제한입니다. 비공개는 월 2,000분이 무료인데, 15분 간격이면 한 달에 약 2,900분이 필요하므로 공개 저장소로 두세요.

### 2. 시크릿 등록

```bash
gh secret set TELEGRAM_BOT_TOKEN   # @BotFather 에서 받은 토큰
gh secret set TELEGRAM_CHAT_ID     # 받을 채팅의 ID
```

`GH_TOKEN`은 Actions가 자동으로 넣어 주므로 따로 등록하지 않습니다.

### 3. 한 번 실행해서 확인

GitHub 저장소 → **Actions** → "AI news to Telegram" → **Run workflow**. `dry_run`을 켜면 보내지 않고 결과만 Summary에 보여 줍니다. 이후에는 15분마다 자동으로 돕니다.

첫 실행은 지금 화제인 것들 중 상위 **5건**만 보내고 나머지는 "본 것"으로 기록합니다. 그 다음부터는 새로 기준을 넘은 것만 옵니다.

## Reddit 공식 API 연결 (선택, 승인 필요)

로그인 없는 Reddit 접근은 클라우드 IP에서 가끔 차단됩니다. 기본 설정은 서브레딧 6개를 하나로 묶은 RSS 피드를 한 번만 요청해서 오늘의 상위 5개를 가져오며, GitHub Actions 서버에서 정상 동작을 확인했습니다. 추천수 기준으로 정밀하게 거르려면 공식 API가 필요한데, 2026년 기준 Reddit은 앱 생성 전에 **Data Access Request 티켓을 제출하고 수동 승인**을 받도록 바뀌었습니다.

1. https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164 에서 Data Access Request 제출 (개인·비상업 용도)
2. 승인 메일을 받으면 https://www.reddit.com/prefs/apps 에서 **script** 앱 생성 (redirect uri는 `http://localhost:8080`)
3. client id(앱 이름 아래 짧은 문자열)와 secret을 등록:

```bash
gh secret set REDDIT_CLIENT_ID
gh secret set REDDIT_CLIENT_SECRET
gh variable set REDDIT_USER_AGENT --body "github-actions:ainewsbot:1.0 (by /u/내레딧아이디)"
```

승인이 없어도 봇은 RSS 경로로 계속 돕니다.

## 선택: Claude가 항목마다 한 줄 설명 달기

```bash
gh secret set ANTHROPIC_API_KEY
gh variable set BRIEFING_PROVIDER --body claude
```

기본 모델은 `claude-opus-5`이고 `CLAUDE_MODEL` 변수로 바꿀 수 있습니다. 실패하면 자동으로 기본 서식으로 보냅니다.

## 선택: X 계정 타임라인 직접 수집

X는 무료 읽기 API가 없고 공개 Nitter 미러도 사실상 모두 막혀서 기본으로는 HN·Reddit 경유 방식만 씁니다. Nitter 호환 인스턴스를 직접 운영한다면:

```bash
gh variable set X_RSS_BASE --body https://내-인스턴스
gh variable set X_ACCOUNTS --body "OpenAI,AnthropicAI,GoogleDeepMind"
```

## 조정하기

- **소스·키워드**: `newsbot/sources.py` (서브레딧과 추천수 기준, RSS 목록과 `ai_only`/`limit`, AI 키워드(영어·한국어), GitHub 검색어). 소스를 추가한 뒤에는 `python -m newsbot --absorb`를 한 번 돌리고 state를 커밋하면 밀린 옛 글이 한꺼번에 오지 않습니다.
- **기준값**: 저장소 **Variables**로 덮어쓰기. 예) `gh variable set MAX_ITEMS_PER_RUN --body 5`, `gh variable set QUIET_HOURS_KST --body 23-7`
  전체 목록은 `.env.example` 참고.
- **주기**: `.github/workflows/newsbot.yml`의 `cron` (기본 15분). GitHub는 예약 실행을 몇 분씩 늦출 수 있습니다.

## 로컬에서 돌려 보기

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env    # 토큰 채우기
.venv/bin/python -m newsbot --dry-run --ignore-quiet-hours --state /tmp/nb.json   # 보내지 않음
.venv/bin/python -m newsbot                                                        # 실제 전송 + state 기록
.venv/bin/python -m newsbot --absorb                                               # 소스를 새로 추가한 뒤: 지금 것들은 보낸 셈 치고 기록만
.venv/bin/python -m pytest -q
```

## 상태 파일

`state/state.json`에 본 항목·보낸 시각·대기열이 있습니다. Actions가 매 실행 후 이 파일만 커밋합니다(`[skip ci]`). 로컬에서 작업한 뒤 push 하기 전에는 `git pull --rebase`를 먼저 하세요. 파일을 지우면 다음 실행이 "첫 실행"으로 취급되어 상위 5건만 다시 보냅니다.

## 예약 실행이 안 돌 때: Google Apps Script로 대신 깨우기

GitHub의 cron 예약은 새로 만든 워크플로를 며칠씩 등록하지 않는 장애가 종종 있습니다(GitHub 커뮤니티에 반복 보고됨). 그럴 때는 Google Apps Script가 15분마다 GitHub에 "실행해" 신호를 보내게 하면 됩니다. 새 계정이 필요 없고 무료입니다. 코드는 `trigger/apps_script.gs`.

1. **GitHub 토큰 만들기**: GitHub → 우측 상단 프로필 → Settings → 맨 아래 Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token.
   Repository access: *Only select repositories* → `ainewsbot`. Permissions → Repository permissions → **Actions: Read and write**. Expiration은 1년. 생성된 토큰(`github_pat_...`)을 복사합니다. 이 화면을 벗어나면 다시 볼 수 없습니다.
2. **Apps Script 프로젝트**: https://script.google.com → 새 프로젝트 → 편집기의 내용을 지우고 `trigger/apps_script.gs` 내용을 붙여 넣기 → 저장.
3. **토큰 저장**: 왼쪽 톱니바퀴(프로젝트 설정) → 스크립트 속성 → 속성 추가: 이름 `GH_PAT`, 값은 1번 토큰 → 저장.
4. **트리거 설치**: 편집기 상단 함수 선택에서 `installTrigger` 선택 → 실행. 처음 한 번 권한 허용 창이 뜹니다(외부 서비스 연결 허용). 실행 로그에 "trigger installed"가 보이면 끝.
5. **확인**: 15분 안에 GitHub 저장소 → Actions 탭에 `workflow_dispatch` 실행이 생깁니다.

GitHub 예약이 나중에 정상화되면 둘 다 돌지만, `concurrency` 설정 때문에 겹치지 않고 두 번째 실행은 새 소식이 없어 조용히 끝납니다. 하나만 남기고 싶으면 Apps Script에서 `removeTrigger`를 실행하거나, 워크플로의 `schedule` 항목을 지우면 됩니다.

## 노트북에서 대신 깨우기 (임시책)

Apps Script를 설정하기 전까지 쓰는 임시책입니다. Mac이 켜져 있을 때만 15분마다 GitHub에 실행 신호를 보냅니다. 스크립트는 `trigger/mac_dispatch.sh`의 복사본 `~/.local/bin/ainewsbot-dispatch.sh`(Desktop 폴더는 백그라운드 프로세스가 읽지 못해 밖에 둠), 등록 파일은 `~/Library/LaunchAgents/com.baebyeongchan.ainewsbot-dispatch.plist`, 로그는 `~/Library/Logs/ainewsbot-dispatch.log`.

```bash
# 끄기 (Apps Script 설정 후)
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.baebyeongchan.ainewsbot-dispatch.plist
rm ~/Library/LaunchAgents/com.baebyeongchan.ainewsbot-dispatch.plist
# 다시 켜기
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.baebyeongchan.ainewsbot-dispatch.plist
```

## 문제가 생기면

- **아무것도 안 옴**: Actions 로그의 JSON 요약을 보세요. `sources`에 소스별 건수와 오류가 있습니다. 조용한 시간대(`quiet_hours: true`)면 정상입니다.
- **Reddit 오류만 남**: 위의 OAuth 연결을 하세요.
- **GitHub 트렌딩 0건 오류**: github.com/trending 페이지 구조가 바뀐 것입니다. `newsbot/fetchers/github.py`의 `parse_trending_html`을 손보면 됩니다.
- **예약 실행이 한 번도 안 돎** (Actions 탭에 `schedule` 실행이 없음): 위의 Apps Script 예비 트리거를 쓰세요. 워크플로 파일을 조금 고쳐서 push하거나 Actions 탭에서 워크플로를 Disable → Enable 하면 풀리기도 합니다.
- **60일 동안 저장소에 push가 없으면** GitHub가 예약 실행을 끕니다. 상태 파일 커밋이 push로 잡히므로 봇이 살아 있는 한 문제없습니다.
