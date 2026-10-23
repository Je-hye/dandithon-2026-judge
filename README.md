# 단디톤 2026 심사 에이전트

단디톤 2026 참가팀 발표자료를 AI 심사위원이 자동 평가하는 Streamlit 앱.

## 배포 주소

| 버전 | URL |
|------|-----|
| v1 (GitHub URL 입력) | https://dandithon-2026-judge-3fwwxj5oftqkfotmlrwqe7.streamlit.app/ |
| v2 (PPT 파일 업로드) | https://dandithon-2026-judge-meq8frvdxnfh2fuggitaz5.streamlit.app/ |

## 버전 차이

- **v1** (`judge.py`): GitHub 레포 URL을 입력하면 README·파일 구조를 분석, 4인 심사위원 병렬 평가
- **v2** (`judge_v2.py`): `.pptx` 파일을 직접 업로드, 5인 심사위원 병렬 평가

## 심사 기준 (총 100점)

| 항목 | 배점 |
|------|------|
| 기획 | 50점 |
| 개발 | 30점 |
| 디자인 | 10점 |
| 발표 | 10점 |

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run judge_v2.py   # v2
streamlit run judge.py      # v1
```

`ANTHROPIC_API_KEY` 환경변수 필요.
