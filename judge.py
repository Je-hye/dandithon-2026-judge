"""단디톤 2026 심사 에이전트 — 4개 페르소나 병렬 평가"""

import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
import streamlit as st

client = anthropic.Anthropic()


def fetch_github_info(repo_url: str) -> str:
    """공개 GitHub 레포에서 README와 파일 구조를 가져옴"""
    match = re.search(r"github\.com/([^/]+)/([^/\s#?]+)", repo_url)
    if not match:
        return "레포 URL 파싱 실패"

    owner, repo = match.group(1), match.group(2).rstrip(".git")
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "dandithon-judge"}
    info = []

    # README
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/contents/README.md",
            headers={**headers, "Accept": "application/vnd.github.v3.raw"},
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            readme = r.read().decode("utf-8")[:2500]
            info.append(f"README.md:\n{readme}")
    except Exception:
        info.append("README 없음")

    # 파일 구조
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode("utf-8"))
            files = [i["path"] for i in data.get("tree", []) if i["type"] == "blob"][:60]
            info.append(f"파일 구조 ({len(files)}개):\n" + "\n".join(files))
    except Exception:
        pass

    return "\n\n".join(info) if info else "레포 정보를 가져올 수 없습니다"

JUDGES = [
    {
        "id": "planning",
        "name": "이재원",
        "role": "기획 심사위원",
        "emoji": "📋",
        "background": "지역학·서비스 기획 전공 교수",
        "max_score": 50,
        "criteria": """
- 지역 고유성 (8점): 대구·경북만의 고유한 강점과 가치를 발견했는가?
- 사용자 리서치 (4점): 실제 조사나 데이터로 니즈를 검증했는가?
- 주제 적합성 (8점): 감정적·경험적 가치를 서비스 핵심 가치로 연결했는가?
- 가치의 재해석 (8점): 새로운 관점으로 해석해 서비스에 반영했는가?
- 기술 활용 타당성 (4점): AI 등 기술이 가치 전달에 적절히 활용되었는가?
- 창의성 및 차별성 (8점): 기존 서비스와 다른 독창적인 접근인가?
- 비즈니스 및 지속 가능성 (5점): 수익 구조가 명확하고 현실적인가?
- 전국적 확장 가능성 (5점): 대구·경북 외 지역 사용자에게도 제공 가능한가?""",
        "personality": """당신은 이재원 교수(지역학·서비스 기획 전공)입니다.
WHY LOCAL에 가장 엄격합니다. '대구·경북이 없어도 작동하는 서비스는 지역 고유성 0점'이 철칙입니다.
학술적이고 꼼꼼하며, 주제 해석의 깊이를 중요하게 봅니다.
단순한 지역 홍보 서비스와 '경험의 원리를 추출한 서비스'를 날카롭게 구분합니다.
정중하지만 기준이 엄격한 말투를 씁니다.""",
    },
    {
        "id": "dev",
        "name": "박준혁",
        "role": "개발 심사위원",
        "emoji": "💻",
        "background": "스타트업 CTO 출신 개발자",
        "max_score": 30,
        "criteria": """
- 핵심 기능 동작 여부 (5점): 핵심 기능이 실제로 동작하는가?
- 완성도 및 안정성 (4점): 주요 사용 흐름에서 오류 없이 작동하는가?
- UI 연동 (3점): 프론트엔드와 백엔드가 유기적으로 연결되어 있는가?
- AI 기능 실제 동작 (4점): AI 기능이 단순 API 연동을 넘어 실제로 동작하는가?
- AI 적용 적절성 (3점): AI 모델·API의 선택과 활용 방식이 적합한가?
- 응답 품질 (3점): AI가 생성하는 결과물이 실질적인 가치를 제공하는가?
- 코드 가독성 (2점): 변수명, 함수 분리, 주석 등 코드가 읽기 쉬운가?
- 아키텍처 설계 (2점): 유지보수와 확장을 고려한 구조인가?
- README 및 문서화 (1점): 프로젝트 설명, 실행 방법, 기술 스택이 기록되어 있는가?
- 실배포 여부 (2점): 외부에서 접근 가능한 URL로 배포되어 있는가?
- 배포 안정성 (1점): 데모 시연 중 서비스가 안정적으로 작동하는가?""",
        "personality": """당신은 박준혁, 스타트업 CTO 출신의 냉정한 개발자 심사위원입니다.
'작동하냐 안 하냐'가 가장 중요합니다.
AI를 'ChatGPT API 그냥 붙인 것'과 '진짜 AI 활용'을 날카롭게 구분합니다.
Multi-agent 언급 시 '왜 multi-agent여야 하는지, 단순 API 호출과 뭐가 다른지' 반드시 질문합니다.
기술 과시에 회의적이며 실용적 구현을 선호합니다.
짧고 직설적인 말투를 씁니다.""",
    },
    {
        "id": "design",
        "name": "김나연",
        "role": "디자인 심사위원",
        "emoji": "🎨",
        "background": "UX/UI 디자이너, 감성 디자인 전문",
        "max_score": 10,
        "criteria": """
- 컨셉 및 일관성 (5점): 서비스의 목적을 직관적으로 전달하는 디자인 컨셉과 일관된 비주얼 아이덴티티를 갖추었는가?
- UX 설계 및 심미성 (5점): 사용자 경험 과정이 직관적이며, 시각적 완성도를 갖추었는가?""",
        "personality": """당신은 김나연, 감성 디자인 전문 UX/UI 디자이너 심사위원입니다.
사용자의 감정적 여정을 중요하게 봅니다.
기획의 감정적 가치가 실제 UI/UX에서 느껴지는지 평가합니다.
비주얼 완성도보다 '흐름의 자연스러움'을 더 중시합니다.
공감적이고 따뜻한 말투를 씁니다.""",
    },
    {
        "id": "presentation",
        "name": "최성민",
        "role": "발표 심사위원",
        "emoji": "🎤",
        "background": "스타트업 투자자, 피칭 심사 다수 경험",
        "max_score": 10,
        "criteria": """
- PPT 완성도 및 시각화 (5점): 기획 내용을 효과적으로 전달하기 위한 장표 구성과 시각 자료가 우수한가?
- 발표 태도 (5점): 발표자의 전달력이 좋고, 논리적인가?""",
        "personality": """당신은 최성민, 스타트업 투자자이자 피칭 심사 경험이 많은 심사위원입니다.
'이 팀이 믿음이 가냐'를 중요하게 봅니다.
논리의 일관성, 주장의 근거, 발표 태도를 봅니다.
허점과 모순을 날카롭게 잡아냅니다.
비즈니스 마인드, 스토리텔링, 간결함을 선호합니다.
발표 자료의 구성과 전달력을 시각 디자인보다 중요하게 봅니다.""",
    },
]


def _sanitize_json(text: str) -> str:
    """JSON string 값 내부의 제어 문자와 이스케이프되지 않은 따옴표를 처리"""
    result = []
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and in_string:
            result.append(c)
            i += 1
            if i < len(text):
                result.append(text[i])
            i += 1
            continue
        if c == '"':
            if not in_string:
                in_string = True
                result.append(c)
            else:
                # 전방 탐색: 다음 비공백 문자가 JSON 구조 문자면 문자열 종료
                j = i + 1
                while j < len(text) and text[j] in " \t\r\n":
                    j += 1
                if j >= len(text) or text[j] in ":,}]":
                    in_string = False
                    result.append(c)
                else:
                    # 문자열 내부 따옴표 → 이스케이프
                    result.append('\\"')
        elif in_string and c == "\n":
            result.append("\\n")
        elif in_string and c == "\r":
            result.append("\\r")
        elif in_string and c == "\t":
            result.append("\\t")
        else:
            result.append(c)
        i += 1
    return "".join(result)


def get_judge_response(judge: dict, project_info: str) -> dict:
    system_prompt = f"""당신은 {judge['name']}({judge['role']}, {judge['background']})입니다.

{judge['personality']}

담당 심사 기준과 배점:
{judge['criteria']}

총 {judge['max_score']}점을 담당합니다.

주의: 아이디어가 확정된 단계입니다. 제시된 기획 내용을 바탕으로 평가하며, 배포·코드 품질 등 아직 구현되지 않은 항목은 계획의 구체성과 실현 가능성으로 평가합니다.

응답은 반드시 아래 JSON 형식으로만 출력하세요. JSON 외 다른 텍스트 없이.
주의: comment, verdict, strongPoint, weakness, killerQuestion 등 텍스트 필드 내에서 큰따옴표(")를 절대 사용하지 마세요. 인용이 필요하면 「」 또는 ''를 사용하세요.
{{
  "totalScore": <숫자>,
  "maxScore": {judge['max_score']},
  "scores": [
    {{"item": "항목명", "score": <숫자>, "max": <배점>, "comment": "한 줄 코멘트"}}
  ],
  "verdict": "전체 총평 (2-3문장, 페르소나 특성 살려서)",
  "strongPoint": "가장 잘 된 점 (구체적으로)",
  "weakness": "가장 개선이 필요한 점 (구체적으로)",
  "killerQuestion": "발표장에서 내가 반드시 물어볼 질문 (날카롭게)"
}}"""

    # 기획(8항목)·개발(11항목)은 JSON이 길어서 넉넉하게 설정
    max_tokens = 8192 if judge["max_score"] >= 30 else 1500
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": f"다음 팀의 프로젝트를 심사해주세요:\n\n{project_info}"}],
    )

    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_sanitize_json(text))


def evaluate_all(project_info: str) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(get_judge_response, j, project_info): j for j in JUDGES}
        for future in as_completed(futures):
            judge = futures[future]
            try:
                results[judge["id"]] = {"judge": judge, "result": future.result()}
            except Exception as e:
                results[judge["id"]] = {"judge": judge, "error": str(e)}
    return results


# ── UI ────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="단디톤 2026 심사 에이전트", page_icon="🦁", layout="wide")

st.title("🦁 단디톤 2026 심사 에이전트")
st.caption("4명의 심사위원 페르소나가 당신의 아이디어를 평가합니다 — 기획 50 · 개발 30 · 디자인 10 · 발표 10")

if not os.getenv("ANTHROPIC_API_KEY"):
    st.error("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다. `export ANTHROPIC_API_KEY=sk-...` 후 재실행하세요.")
    st.stop()

with st.form("project_form"):
    st.subheader("프로젝트 정보")

    col1, col2 = st.columns(2)

    with col1:
        service_name = st.text_input("서비스 이름 *", placeholder="예: 레이어(Layer)")
        service_desc = st.text_area("서비스 설명 (1-2문장) *", placeholder="어떤 서비스인지 한눈에", height=80)
        why_local = st.text_area(
            "WHY LOCAL — 왜 대구·경북인가?",
            placeholder="대구·경북의 어떤 고유한 가치/경험에서 출발했는지",
            height=100,
        )
        why_people = st.text_area(
            "WHY PEOPLE — 어떤 감정/가치를 제공하는가?",
            placeholder="사람들에게 어떤 감정과 의미를 주는지",
            height=100,
        )

    with col2:
        why_service = st.text_area(
            "WHY SERVICE — 어떻게 서비스로 구현하는가?",
            placeholder="경험의 원리를 어떻게 재설계했는지, 핵심 기능",
            height=100,
        )
        tech_stack = st.text_area(
            "기술 스택 및 AI 활용",
            placeholder="사용 기술과 AI를 어떻게 활용하는지",
            height=100,
        )
        business_model = st.text_area(
            "비즈니스 모델 및 확장 계획",
            placeholder="수익 구조, 전국 확장 방법",
            height=80,
        )
        extra = st.text_area("추가 정보 (선택)", placeholder="팀 구성, 차별점 등", height=60)

    github_url = st.text_input(
        "GitHub 레포 URL (선택)",
        placeholder="https://github.com/username/repo",
        help="공개 레포만 가능. 입력하면 README·파일 구조를 개발 심사에 반영합니다.",
    )

    submitted = st.form_submit_button("🎯 심사받기", use_container_width=True, type="primary")

if submitted:
    if not service_name or not service_desc:
        st.error("서비스 이름과 설명은 필수입니다.")
        st.stop()

    project_info = f"""서비스명: {service_name}
서비스 설명: {service_desc}
WHY LOCAL: {why_local or '미기재'}
WHY PEOPLE: {why_people or '미기재'}
WHY SERVICE: {why_service or '미기재'}
기술 스택 및 AI 활용: {tech_stack or '미기재'}
비즈니스 모델 및 확장: {business_model or '미기재'}
추가 정보: {extra or '없음'}"""

    if github_url.strip():
        with st.spinner("GitHub 레포 불러오는 중..."):
            repo_info = fetch_github_info(github_url.strip())
        project_info += f"\n\n--- GitHub 레포 정보 ---\n레포 URL: {github_url}\n{repo_info}"
        st.caption(f"✅ GitHub 레포 연결됨: `{github_url}`")

    with st.spinner("4명의 심사위원이 평가 중입니다 (약 10-15초)..."):
        results = evaluate_all(project_info)

    # 총점
    total = sum(
        d["result"].get("totalScore", 0) for d in results.values() if "result" in d
    )
    st.divider()
    grade = "🟢" if total >= 75 else "🟡" if total >= 55 else "🔴"
    st.markdown(f"## {grade} 총점: **{total} / 100**")
    st.progress(total / 100)
    st.divider()

    # 심사위원 카드 (2열)
    judge_order = ["planning", "dev", "design", "presentation"]
    cols = st.columns(2)

    for idx, judge_id in enumerate(judge_order):
        data = results.get(judge_id, {})
        judge = data.get("judge", {})

        with cols[idx % 2]:
            if "error" in data:
                st.error(f"{judge.get('emoji','❌')} {judge.get('name','?')} 평가 오류: {data['error']}")
                continue

            result = data["result"]
            score = result.get("totalScore", 0)
            max_s = judge["max_score"]

            with st.container(border=True):
                st.markdown(f"### {judge['emoji']} {judge['name']} — {judge['role']}")
                st.caption(judge["background"])

                st.metric("점수", f"{score} / {max_s}", f"{round(score / max_s * 100)}%")
                st.progress(score / max_s)

                with st.expander("세부 점수"):
                    for item in result.get("scores", []):
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"**{item['item']}** — {item.get('comment', '')}")
                        c2.write(f"{item['score']}/{item['max']}")

                st.info(f"💬 {result.get('verdict', '')}")

                c1, c2 = st.columns(2)
                c1.success(f"✅ {result.get('strongPoint', '')}")
                c2.error(f"⚠️ {result.get('weakness', '')}")

                st.warning(f"❓ **킬러 질문:** {result.get('killerQuestion', '')}")
