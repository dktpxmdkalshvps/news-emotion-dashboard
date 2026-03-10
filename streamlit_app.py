"""
streamlit_app.py - 뉴스 감성 분석 웹 대시보드 v3.0
실행: streamlit run streamlit_app.py
"""

import sys
import os
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from collections import Counter

import streamlit as st

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="뉴스 감성 분석 대시보드",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 다크 테마 CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp { background-color: #0F0F1A; color: #E8E8F0; }
    .main  { background-color: #0F0F1A; }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background-color: #1A1A2E;
        border-right: 1px solid #2D2D4E;
    }
    [data-testid="stSidebar"] * { color: #E8E8F0 !important; }

    /* 메트릭 카드 */
    [data-testid="stMetric"] {
        background-color: #1A1A2E;
        border: 1px solid #2D2D4E;
        border-radius: 8px;
        padding: 12px;
    }
    [data-testid="stMetricLabel"]  { color: #9999BB !important; font-size: 0.82rem; }
    [data-testid="stMetricValue"]  { color: #E8E8F0 !important; font-size: 1.6rem; }

    /* 타이틀 */
    h1, h2, h3 { color: #E8E8F0 !important; }

    /* 데이터프레임 */
    .dataframe-container { border-radius: 8px; overflow: hidden; }

    /* 버튼 */
    .stButton button {
        background-color: #6C63FF;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: bold;
    }
    .stButton button:hover { background-color: #5a52cc; }

    /* 탭 */
    .stTabs [data-baseweb="tab"] { color: #9999BB; }
    .stTabs [aria-selected="true"] { color: #6C63FF !important; }

    /* 구분선 */
    hr { border-color: #2D2D4E; }

    /* 배지 */
    .badge-pos { background:#1a4a2e; color:#2ECC71; padding:3px 10px; border-radius:12px; font-size:0.82rem; font-weight:bold; }
    .badge-neg { background:#4a1a1a; color:#E74C3C; padding:3px 10px; border-radius:12px; font-size:0.82rem; font-weight:bold; }
    .badge-neu { background:#2a2a1a; color:#F39C12; padding:3px 10px; border-radius:12px; font-size:0.82rem; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

# ── 색상 상수 ─────────────────────────────────────────────────────────────────
C = {
    "긍정": "#2ECC71", "중립": "#F39C12", "부정": "#E74C3C",
    "bg": "#0F0F1A", "card": "#1A1A2E", "border": "#2D2D4E",
    "text": "#E8E8F0", "text2": "#9999BB", "accent": "#6C63FF",
    "naver": "#03C75A", "daum": "#FF5722", "hankyung": "#1565C0",
}
SITE_KR = {"naver": "네이버", "daum": "다음", "hankyung": "한국경제"}

PLOTLY_LAYOUT = dict(
    paper_bgcolor=C["card"], plot_bgcolor=C["card"],
    font=dict(color=C["text"], family="Apple SD Gothic Neo, Malgun Gothic, sans-serif"),
    margin=dict(l=10, r=10, t=40, b=10),
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  세션 상태 초기화
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
if "last_keyword" not in st.session_state:
    st.session_state.last_keyword = ""
if "history" not in st.session_state:
    st.session_state.history = []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  사이드바
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.sidebar:
    st.markdown("## ⚙️ 분석 설정")
    st.markdown("---")

    # 키워드 입력
    keyword = st.text_input(
        "🔍 검색 키워드",
        placeholder="예: 삼성전자, 현대차, 카카오",
        value=st.session_state.last_keyword,
    )

    # 사이트 선택
    st.markdown("**📡 수집 사이트**")
    col1, col2, col3 = st.columns(3)
    use_naver    = col1.checkbox("네이버",    value=True)
    use_daum     = col2.checkbox("다음",      value=True)
    use_hankyung = col3.checkbox("한국경제",  value=True)

    # 페이지 수
    pages = st.slider("📄 사이트당 수집 페이지", 1, 10, 2)

    # 감성 분석 모드
    st.markdown("**🧠 감성 분석 모드**")
    analysis_mode = st.selectbox(
        "모드 선택",
        options=["lexicon", "hybrid", "ml"],
        format_func=lambda x: {
            "lexicon": "📚 사전 기반 (빠름)",
            "ml":      "🤖 KoBERT ML (정확)",
            "hybrid":  "⚡ 하이브리드 (균형)",
        }[x],
    )

    if analysis_mode in ("ml", "hybrid"):
        ml_model = st.text_input(
            "HuggingFace 모델 ID",
            value="snunlp/KR-FinBert-SC",
            help="pip install transformers torch 후 사용 가능"
        )
    else:
        ml_model = "snunlp/KR-FinBert-SC"

    # 고급 옵션
    with st.expander("🔧 고급 옵션"):
        timeout    = st.number_input("타임아웃 (초)", 10, 60, 20)
        max_retry  = st.number_input("최대 재시도 횟수", 1, 5, 3)
        headless   = st.checkbox("헤드리스 모드", value=True)
        show_wc    = st.checkbox("WordCloud 표시", value=True)

    st.markdown("---")
    run_btn = st.button("🚀 분석 시작", use_container_width=True)

    # 데모 모드
    st.markdown("---")
    demo_btn = st.button("🧪 데모 모드 (샘플 데이터)", use_container_width=True)

    # 분석 이력
    if st.session_state.history:
        st.markdown("---")
        st.markdown("**📋 최근 분석 이력**")
        for h in st.session_state.history[-5:][::-1]:
            st.markdown(f"• `{h['keyword']}` ({h['count']}건, {h['time']})")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  메인 헤더
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<h1 style='text-align:center; font-size:2rem; margin-bottom:0;'>
  📰 뉴스 감성 분석 대시보드
</h1>
<p style='text-align:center; color:#9999BB; font-size:0.95rem; margin-top:4px;'>
  네이버 · 다음 · 한국경제 통합 분석 | Lexicon + KoBERT 하이브리드
</p>
""", unsafe_allow_html=True)
st.markdown("---")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  분석 실행 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_data(ttl=600, show_spinner=False)
def run_crawl(keyword, sites, pages, timeout, max_retry, headless):
    """크롤링 (10분 캐시)"""
    from crawler import MultiSiteCrawler
    crawler = MultiSiteCrawler(
        sites=sites, headless=headless,
        max_retries=max_retry, timeout_sec=timeout,
    )
    return crawler.crawl_to_df(keyword=keyword, pages_per_site=pages)


def run_analysis(df, mode, ml_model):
    """감성 분석"""
    from sentiment import SentimentAnalyzer
    analyzer = SentimentAnalyzer(mode=mode, ml_model=ml_model)
    return analyzer.analyze(df), analyzer.get_statistics(analyzer.analyze(df))


def load_demo_data(keyword):
    """데모용 샘플 데이터 생성"""
    import random
    from datetime import timedelta

    random.seed(42)
    titles = [
        f"{keyword}, 2분기 영업이익 급등…반도체 흑자 전환 성공",
        "코스피 2600 돌파…외국인 매수세 강세 지속",
        f"{keyword} 글로벌 1위 달성…성장세 가속",
        f"{keyword} AI 신사업 수주 잇달아…주가 상한가",
        "LG에너지솔루션 신고가 경신…수주 잔고 급증",
        f"{keyword} 수출 30% 증가…무역수지 개선",
        "SK하이닉스, HBM 독점 공급 계약 타결",
        f"{keyword} 주가 급락…미중 갈등 여파 충격",
        "코스피 3% 하락…글로벌 긴축 공포 재부각",
        "부동산 PF 위기…건설사 파산 우려 현실화",
        "원달러 환율 폭등…외환시장 불안 심화",
        f"{keyword} 실적 쇼크…3분기 영업이익 대폭 감소",
        "IT 기업 대규모 구조조정…고용 불안 확대",
        "반도체 수요 부진 지속…업황 악화 우려 증가",
        "한국은행, 기준금리 동결 결정",
        "금융위, 내년 금융정책 방향 발표",
        f"{keyword}, 3분기 실적 발표 예정",
        "현대차, 신모델 출시 계획 공개",
        "LG전자 신사업 전략 설명회 개최",
        f"{keyword} 혁신 기술 특허 취득 성공",
        f"{keyword} 적자 전환…손실 3000억 기록",
        "글로벌 침체 우려…수출 비상",
        f"{keyword} 파트너십 계약 체결…협력 확대",
        "반도체 호황 재개…급등 신호",
        f"{keyword} 논란 지속…소송 리스크 증가",
    ]
    sources = ["naver", "daum", "hankyung"]
    press_map = {
        "naver":    ["조선일보","중앙일보","동아일보","MBC","KBS"],
        "daum":     ["이데일리","머니투데이","헤럴드경제","뉴시스"],
        "hankyung": ["한국경제","한경닷컴"],
    }
    base = datetime.now()
    rows = []
    for src in sources:
        for i, title in enumerate(random.sample(titles, min(10, len(titles)))):
            rows.append({
                "title":      title,
                "press":      random.choice(press_map[src]),
                "pub_time":   (base - timedelta(hours=random.randint(1, 48))).strftime("%Y.%m.%d %H:%M"),
                "url":        f"https://{src}.example.com/article/{i+1000}",
                "source":     src,
                "crawled_at": base.strftime("%Y-%m-%d %H:%M:%S"),
            })
    return pd.DataFrame(rows)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  실행 트리거
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if demo_btn:
    kw = keyword.strip() or "삼성전자"
    with st.spinner(f"🧪 [{kw}] 샘플 데이터 생성 중…"):
        raw_df = load_demo_data(kw)
    with st.spinner("🧠 감성 분석 중…"):
        from sentiment import SentimentAnalyzer
        analyzer = SentimentAnalyzer(mode="lexicon")
        df       = analyzer.analyze(raw_df)
        stats    = analyzer.get_statistics(df)
    st.session_state.df           = df
    st.session_state.last_keyword = kw
    st.session_state.history.append({
        "keyword": kw, "count": len(df),
        "time": datetime.now().strftime("%H:%M"),
    })
    st.success(f"✅ 데모 완료: {len(df)}건")

elif run_btn:
    if not keyword.strip():
        st.warning("⚠️ 검색 키워드를 입력하세요.")
        st.stop()

    sites = []
    if use_naver:    sites.append("naver")
    if use_daum:     sites.append("daum")
    if use_hankyung: sites.append("hankyung")
    if not sites:
        st.warning("⚠️ 최소 1개 이상의 사이트를 선택하세요.")
        st.stop()

    progress_bar = st.progress(0, "🔍 크롤링 시작…")
    status_text  = st.empty()

    try:
        status_text.info(f"🌐 {' / '.join(SITE_KR.get(s, s) for s in sites)} 크롤링 중…")
        raw_df = run_crawl(keyword.strip(), sites, pages, timeout, max_retry, headless)
        progress_bar.progress(60, "🧠 감성 분석 중…")

        if raw_df.empty:
            st.error("❌ 수집된 데이터가 없습니다. 키워드를 변경하거나 잠시 후 다시 시도하세요.")
            st.stop()

        status_text.info(f"🧠 {len(raw_df)}건 감성 분석 중…")
        from sentiment import SentimentAnalyzer
        analyzer = SentimentAnalyzer(mode=analysis_mode, ml_model=ml_model)
        df       = analyzer.analyze(raw_df)
        stats    = analyzer.get_statistics(df)
        progress_bar.progress(100, "✅ 완료!")
        status_text.empty()

        st.session_state.df           = df
        st.session_state.last_keyword = keyword.strip()
        st.session_state.history.append({
            "keyword": keyword.strip(), "count": len(df),
            "time": datetime.now().strftime("%H:%M"),
        })
        st.success(f"✅ 분석 완료: {len(df)}건")

    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ 오류 발생: {e}")
        st.stop()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  결과 표시
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
df = st.session_state.df
if df.empty:
    st.markdown("""
    <div style='text-align:center; padding:60px; color:#9999BB;'>
      <div style='font-size:3rem;'>📰</div>
      <div style='font-size:1.1rem; margin-top:12px;'>
        사이드바에서 키워드를 입력하고 <b>분석 시작</b>을 클릭하세요
      </div>
      <div style='font-size:0.9rem; margin-top:8px;'>
        또는 <b>데모 모드</b>로 샘플 데이터를 확인해보세요
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# 감성 통계 계산
counts = df["sentiment"].value_counts()
total  = len(df)
pos_n  = int(counts.get("긍정", 0))
neg_n  = int(counts.get("부정", 0))
neu_n  = int(counts.get("중립", 0))
avg_s  = df["score"].mean()
avg_c  = df.get("confidence", pd.Series([0])).mean()
kw     = st.session_state.last_keyword

# ── 헤더 + KPI 카드 ──────────────────────────────────────────────────────────
st.markdown(f"## 📊 [{kw}] 분석 결과")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("📰 총 기사", f"{total}건")
c2.metric("🟢 긍정",   f"{pos_n}건",  f"{pos_n/total*100:.1f}%")
c3.metric("🔴 부정",   f"{neg_n}건",  f"{neg_n/total*100:.1f}%")
c4.metric("🟡 중립",   f"{neu_n}건",  f"{neu_n/total*100:.1f}%")
c5.metric("📈 평균 점수", f"{avg_s:+.2f}")
c6.metric("🎯 평균 신뢰도", f"{avg_c:.2f}")
st.markdown("---")

# ── 탭 레이아웃 ──────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 차트 대시보드", "📰 기사 목록", "🏢 사이트별 분석", "⬇️ 데이터 내보내기"]
)

# ════════════════════════════════════════════════════════
#  Tab 1: 차트 대시보드
# ════════════════════════════════════════════════════════
with tab1:
    row1_l, row1_r = st.columns([1, 2])

    # 도넛 차트
    with row1_l:
        fig_pie = go.Figure(go.Pie(
            labels=["긍정", "중립", "부정"],
            values=[pos_n, neu_n, neg_n],
            hole=0.55,
            marker_colors=[C["긍정"], C["중립"], C["부정"]],
            textinfo="label+percent",
            textfont_size=12,
        ))
        fig_pie.update_layout(
            title="감성 비율",
            showlegend=False,
            **PLOTLY_LAYOUT
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # 감성 점수 분포
    with row1_r:
        fig_hist = go.Figure()
        for sent, color in [("긍정", C["긍정"]), ("중립", C["중립"]), ("부정", C["부정"])]:
            sub = df[df["sentiment"] == sent]["score"]
            if not sub.empty:
                fig_hist.add_trace(go.Histogram(
                    x=sub, name=sent, nbinsx=15,
                    marker_color=color, opacity=0.75,
                    marker_line=dict(width=0.5, color=C["bg"]),
                ))
        fig_hist.add_vline(x=avg_s, line_dash="dash",
                           line_color=C["accent"], line_width=1.5,
                           annotation_text=f"평균 {avg_s:+.2f}",
                           annotation_font_color=C["accent"])
        fig_hist.update_layout(
            title="감성 점수 분포",
            barmode="overlay",
            xaxis_title="점수",
            yaxis_title="빈도",
            **PLOTLY_LAYOUT
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    row2_l, row2_r = st.columns(2)

    # 키워드 빈도 (양방향 막대)
    with row2_l:
        pos_words, neg_words = [], []
        for _, row in df.iterrows():
            if isinstance(row.get("matched_pos"), str) and row["matched_pos"]:
                pos_words.extend(w.strip() for w in row["matched_pos"].split(",") if w.strip())
            if isinstance(row.get("matched_neg"), str) and row["matched_neg"]:
                neg_words.extend(w.strip() for w in row["matched_neg"].split(",") if w.strip())

        top_pos = Counter(pos_words).most_common(7)
        top_neg = Counter(neg_words).most_common(7)
        words   = [w for w, _ in top_neg[::-1]] + [w for w, _ in top_pos]
        vals    = [-c for _, c in top_neg[::-1]] + [c for _, c in top_pos]
        colors_ = [C["부정"]]*len(top_neg) + [C["긍정"]]*len(top_pos)

        if words:
            fig_kw = go.Figure(go.Bar(
                x=vals, y=words, orientation="h",
                marker_color=colors_,
                marker_line=dict(width=0),
            ))
            fig_kw.add_vline(x=0, line_color=C["border"], line_width=1)
            fig_kw.update_layout(
                title="감성 키워드 빈도 (←부정 │ 긍정→)",
                xaxis_title="빈도",
                **PLOTLY_LAYOUT
            )
            st.plotly_chart(fig_kw, use_container_width=True)

    # 신뢰도 vs 점수 산점도
    with row2_r:
        if "confidence" in df.columns:
            fig_sc = px.scatter(
                df, x="score", y="confidence",
                color="sentiment",
                color_discrete_map={"긍정": C["긍정"], "중립": C["중립"], "부정": C["부정"]},
                hover_data=["title", "press"],
                opacity=0.75,
                title="신뢰도 vs 감성 점수",
                labels={"score": "점수", "confidence": "신뢰도", "sentiment": "감성"},
            )
            fig_sc.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig_sc, use_container_width=True)


# ════════════════════════════════════════════════════════
#  Tab 2: 기사 목록
# ════════════════════════════════════════════════════════
with tab2:
    # 필터
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    sent_filter = fc1.multiselect(
        "감성 필터", ["긍정", "중립", "부정"],
        default=["긍정", "중립", "부정"]
    )
    site_filter = fc2.multiselect(
        "사이트 필터",
        options=list(df["source"].unique()),
        format_func=lambda x: SITE_KR.get(x, x),
        default=list(df["source"].unique()),
    )
    min_score = fc3.number_input("최소 점수", value=float(df["score"].min()), step=0.5)

    filtered = df[
        df["sentiment"].isin(sent_filter) &
        df["source"].isin(site_filter) &
        (df["score"] >= min_score)
    ].sort_values("score", ascending=False)

    st.markdown(f"**{len(filtered)}건** 표시 중")

    # 기사 카드 렌더링
    for _, row in filtered.head(50).iterrows():
        sent  = row["sentiment"]
        badge = (f'<span class="badge-pos">긍정 {row["score"]:+.1f}</span>' if sent == "긍정"
                 else f'<span class="badge-neg">부정 {row["score"]:+.1f}</span>' if sent == "부정"
                 else f'<span class="badge-neu">중립 {row["score"]:+.1f}</span>')
        site_label = SITE_KR.get(row.get("source",""), "")
        url = row.get("url", "#")

        st.markdown(f"""
        <div style='background:{C["card"]}; border:1px solid {C["border"]};
                    border-left:3px solid {C.get(sent, C["accent"])};
                    border-radius:8px; padding:12px 16px; margin-bottom:8px;'>
          <div style='display:flex; justify-content:space-between; align-items:center;'>
            <span style='color:{C["text2"]}; font-size:0.8rem;'>
              {site_label} · {row.get("press","")} · {row.get("pub_time","")}
            </span>
            {badge}
          </div>
          <div style='margin-top:6px; font-size:0.97rem; color:{C["text"]};'>
            <a href='{url}' target='_blank'
               style='color:{C["text"]}; text-decoration:none;'>
              {row["title"]}
            </a>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  Tab 3: 사이트별 분석
# ════════════════════════════════════════════════════════
with tab3:
    if "source" not in df.columns:
        st.info("출처 데이터가 없습니다.")
    else:
        # 사이트별 KPI
        for site in df["source"].unique():
            sub = df[df["source"] == site]
            scounts = sub["sentiment"].value_counts()
            site_name = SITE_KR.get(site, site)
            site_color = C.get(site, C["accent"])

            st.markdown(f"""
            <div style='border-left:3px solid {site_color}; padding-left:12px; margin:16px 0 8px;'>
              <span style='font-size:1.1rem; font-weight:bold; color:{site_color};'>{site_name}</span>
              <span style='color:{C["text2"]}; margin-left:8px; font-size:0.9rem;'>{len(sub)}건 수집</span>
            </div>
            """, unsafe_allow_html=True)

            kc1, kc2, kc3, kc4 = st.columns(4)
            kc1.metric("긍정", f"{scounts.get('긍정', 0)}건")
            kc2.metric("부정", f"{scounts.get('부정', 0)}건")
            kc3.metric("중립", f"{scounts.get('중립', 0)}건")
            kc4.metric("평균 점수", f"{sub['score'].mean():+.2f}")

        st.markdown("---")

        # 사이트 비교 그룹 막대 차트
        pivot = (df.groupby(["source", "sentiment"])
                   .size().reset_index(name="count"))
        pivot["site_kr"] = pivot["source"].map(SITE_KR)

        fig_cmp = px.bar(
            pivot, x="site_kr", y="count", color="sentiment",
            color_discrete_map={"긍정": C["긍정"], "중립": C["중립"], "부정": C["부정"]},
            barmode="group",
            title="사이트별 감성 비교",
            labels={"site_kr": "사이트", "count": "건수", "sentiment": "감성"},
        )
        fig_cmp.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_cmp, use_container_width=True)

        # 사이트별 평균 점수
        site_avg = df.groupby("source")["score"].mean().reset_index()
        site_avg["site_kr"] = site_avg["source"].map(SITE_KR)
        site_avg["color"]   = site_avg["score"].apply(
            lambda s: C["긍정"] if s > 0.5 else C["부정"] if s < -0.5 else C["중립"]
        )
        fig_avg = go.Figure(go.Bar(
            x=site_avg["site_kr"], y=site_avg["score"],
            marker_color=site_avg["color"].tolist(),
            text=[f"{v:+.2f}" for v in site_avg["score"]],
            textposition="outside",
        ))
        fig_avg.add_hline(y=0, line_color=C["border"])
        fig_avg.update_layout(
            title="사이트별 평균 감성 점수",
            yaxis_title="평균 점수",
            **PLOTLY_LAYOUT
        )
        st.plotly_chart(fig_avg, use_container_width=True)


# ════════════════════════════════════════════════════════
#  Tab 4: 내보내기
# ════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 📥 분석 결과 내보내기")
    ec1, ec2 = st.columns(2)

    # CSV 다운로드
    with ec1:
        st.markdown("**📄 CSV 파일**")
        csv_data = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ CSV 다운로드",
            data=csv_data.encode("utf-8-sig"),
            file_name=f"{kw}_감성분석_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Excel 다운로드
    with ec2:
        st.markdown("**📊 Excel 파일**")
        if st.button("⬇️ Excel 다운로드", use_container_width=True):
            try:
                from exporter import DataExporter
                exp  = DataExporter(keyword=kw)
                path = exp.export(df)
                with open(path, "rb") as f:
                    st.download_button(
                        "📥 저장된 Excel 열기",
                        data=f,
                        file_name=os.path.basename(path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                st.success(f"✅ 저장됨: {path}")
            except Exception as e:
                st.error(f"Excel 저장 실패: {e}")

    st.markdown("---")
    st.markdown("**🔍 전체 데이터 미리보기**")
    cols_show = ["source", "title", "press", "pub_time", "score", "sentiment", "confidence"]
    cols_show = [c for c in cols_show if c in df.columns]
    st.dataframe(
        df[cols_show].rename(columns={
            "source": "출처", "title": "제목", "press": "언론사",
            "pub_time": "게시시각", "score": "점수",
            "sentiment": "감성", "confidence": "신뢰도",
        }),
        use_container_width=True,
        height=450,
    )

# ── 푸터 ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#9999BB; font-size:0.8rem;'>"
    "News Sentiment Insight Dashboard v3.0 · "
    "네이버 · 다음 · 한국경제 | Lexicon + KoBERT</div>",
    unsafe_allow_html=True
)