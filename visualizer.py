"""
visualizer.py - 감성 분석 결과 시각화 대시보드 v3.0
한글 완전 지원 + 6패널 대시보드 + 사이트별 비교 + WordCloud
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import seaborn as sns
from collections import Counter
from pathlib import Path

import font_utils  # 한글 폰트 전역 적용
from font_utils import get_kr_font
from logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger('visualizer')

try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False

# ── 디자인 토큰 ──────────────────────────────────────────────────────────────
BG      = "#0F0F1A"
CARD    = "#1A1A2E"
CARD2   = "#16213E"
BORDER  = "#2D2D4E"
TEXT    = "#E8E8F0"
TEXT2   = "#9999BB"
ACCENT  = "#6C63FF"

SENTIMENT_COLORS = {
    "긍정": "#2ECC71",
    "중립": "#F39C12",
    "부정": "#E74C3C",
}
SITE_COLORS = {
    "naver":    "#03C75A",
    "daum":     "#FF5722",
    "hankyung": "#1565C0",
}

FONT_PATH = None
for _p in [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgun.ttf",
]:
    if Path(_p).exists():
        FONT_PATH = _p
        break


def _fp(size=11, bold=False):
    """FontProperties 헬퍼"""
    if FONT_PATH:
        p = fm.FontProperties(fname=FONT_PATH, size=size)
        if bold:
            p.set_weight("bold")
        return p
    return fm.FontProperties(size=size)


def _ax_style(ax, title="", xlabel="", ylabel=""):
    """Axes 공통 다크 스타일 적용"""
    ax.set_facecolor(CARD)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
        spine.set_linewidth(0.8)
    ax.tick_params(colors=TEXT2, labelsize=9)
    ax.xaxis.label.set_color(TEXT2)
    ax.yaxis.label.set_color(TEXT2)
    if title:
        ax.set_title(title, fontproperties=_fp(12, bold=True), color=TEXT, pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, fontproperties=_fp(9))
    if ylabel:
        ax.set_ylabel(ylabel, fontproperties=_fp(9))
    ax.grid(axis="y", color=BORDER, linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)


class DashboardVisualizer:
    """
    6패널 감성 대시보드 생성기

    패널 구성:
      Row 1: [파이 차트] [감성 점수 분포] [신뢰도 분포]
      Row 2: [사이트별 감성 비교] [키워드 빈도] [WordCloud / 요약통계]
    """

    def __init__(self, keyword: str, output_dir: str = "output",
                 enable_wordcloud: bool = True, wordcloud_max_words: int = 80):
        self.keyword = keyword
        self.output_dir = output_dir
        self.enable_wordcloud = enable_wordcloud and WORDCLOUD_AVAILABLE
        self.wordcloud_max_words = wordcloud_max_words
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"대시보드 초기화: {keyword}")

    # ── 공개 API ─────────────────────────────────────────────────────────────
    def create_dashboard(self, df: pd.DataFrame) -> str:
        if df.empty:
            logger.warning("빈 DataFrame - 대시보드 생성 불가")
            return ""
        path = self._build_dashboard(df)
        logger.info(f"대시보드 저장: {path}")
        return path

    # ── 메인 레이아웃 ─────────────────────────────────────────────────────────
    def _build_dashboard(self, df: pd.DataFrame) -> str:
        fig = plt.figure(figsize=(20, 13), facecolor=BG)

        # 2행 3열 그리드 (행 높이 비율 다름)
        gs = fig.add_gridspec(
            2, 3,
            height_ratios=[1, 1.1],
            hspace=0.48, wspace=0.38,
            left=0.05, right=0.97,
            top=0.88, bottom=0.07,
        )

        ax_pie   = fig.add_subplot(gs[0, 0])
        ax_hist  = fig.add_subplot(gs[0, 1])
        ax_conf  = fig.add_subplot(gs[0, 2])
        ax_site  = fig.add_subplot(gs[1, 0])
        ax_kw    = fig.add_subplot(gs[1, 1])
        ax_wc    = fig.add_subplot(gs[1, 2])

        self._plot_pie(ax_pie, df)
        self._plot_score_dist(ax_hist, df)
        self._plot_confidence(ax_conf, df)
        self._plot_site_comparison(ax_site, df)
        self._plot_keywords(ax_kw, df)

        if self.enable_wordcloud:
            self._plot_wordcloud(ax_wc, df)
        else:
            self._plot_summary_text(ax_wc, df)

        # 제목 + 서브타이틀
        fp_title = _fp(22, bold=True)
        fp_sub   = _fp(11)
        fig.text(0.5, 0.94, f"[{self.keyword}] 뉴스 감성 분석 대시보드",
                 ha="center", va="center",
                 fontproperties=fp_title, color=TEXT)

        total = len(df)
        counts = df["sentiment"].value_counts()
        pos_r  = counts.get("긍정", 0) / total * 100
        avg_s  = df["score"].mean()
        avg_c  = df.get("confidence", pd.Series([0])).mean()
        sub = (f"총 {total}건 분석  │  긍정 {pos_r:.1f}%  │  "
               f"평균 감성 점수 {avg_s:+.2f}  │  평균 신뢰도 {avg_c:.2f}")
        fig.text(0.5, 0.905, sub, ha="center", va="center",
                 fontproperties=fp_sub, color=TEXT2)

        # 하단 출처 범례
        handles = [
            mpatches.Patch(color=SITE_COLORS.get(k, "#888"),
                           label={"naver":"네이버","daum":"다음","hankyung":"한국경제"}.get(k, k))
            for k in df["source"].unique() if k in SITE_COLORS
        ]
        if handles:
            fig.legend(handles=handles, loc="lower center",
                       ncol=len(handles), frameon=False,
                       prop=_fp(10), labelcolor=TEXT2,
                       bbox_to_anchor=(0.5, 0.01))

        fname = f"{self.keyword}_dashboard.png"
        path  = os.path.join(self.output_dir, fname)
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
        plt.close()
        return path

    # ── 패널 1: 도넛 파이 차트 ───────────────────────────────────────────────
    def _plot_pie(self, ax, df: pd.DataFrame):
        counts = df["sentiment"].value_counts()
        order  = [s for s in ["긍정", "중립", "부정"] if s in counts.index]
        sizes  = [counts[s] for s in order]
        colors = [SENTIMENT_COLORS[s] for s in order]
        total  = sum(sizes)

        wedges, _, autotexts = ax.pie(
            sizes, colors=colors, autopct="%1.1f%%",
            startangle=90, pctdistance=0.72,
            wedgeprops=dict(width=0.55, edgecolor=BG, linewidth=2),
        )
        for at in autotexts:
            at.set_fontproperties(_fp(9, bold=True))
            at.set_color("white")

        # 중앙 텍스트
        ax.text(0, 0.08, str(total), ha="center", va="center",
                fontproperties=_fp(20, bold=True), color=TEXT)
        ax.text(0, -0.22, "총 기사 수", ha="center", va="center",
                fontproperties=_fp(9), color=TEXT2)

        # 범례
        legend_handles = [
            mpatches.Patch(color=SENTIMENT_COLORS[s],
                           label=f"{s}  {counts[s]}건")
            for s in order
        ]
        ax.legend(handles=legend_handles, loc="lower center",
                  bbox_to_anchor=(0.5, -0.18), ncol=3,
                  frameon=False, prop=_fp(9), labelcolor=TEXT)

        ax.set_facecolor(CARD)
        ax.set_title("감성 비율", fontproperties=_fp(12, bold=True),
                     color=TEXT, pad=10)

    # ── 패널 2: 감성 점수 분포 히스토그램 ────────────────────────────────────
    def _plot_score_dist(self, ax, df: pd.DataFrame):
        if "score" not in df.columns:
            return

        for sentiment in ["긍정", "중립", "부정"]:
            subset = df[df["sentiment"] == sentiment]["score"]
            if subset.empty:
                continue
            ax.hist(subset, bins=12, color=SENTIMENT_COLORS[sentiment],
                    alpha=0.75, edgecolor=BG, linewidth=0.6,
                    label=sentiment)

        mean = df["score"].mean()
        ax.axvline(mean, color=ACCENT, linestyle="--",
                   linewidth=1.5, label=f"평균 {mean:+.2f}")

        ax.set_xticks(ax.get_xticks())
        ax.set_xticklabels(
            [f"{v:.0f}" for v in ax.get_xticks()],
            fontproperties=_fp(8)
        )
        ax.set_yticks(ax.get_yticks())
        ax.set_yticklabels(
            [str(int(v)) for v in ax.get_yticks()],
            fontproperties=_fp(8)
        )

        leg = ax.legend(frameon=False, prop=_fp(9), labelcolor=TEXT)
        _ax_style(ax, title="감성 점수 분포",
                  xlabel="점수", ylabel="빈도")

    # ── 패널 3: 신뢰도 분포 ──────────────────────────────────────────────────
    def _plot_confidence(self, ax, df: pd.DataFrame):
        col = "confidence" if "confidence" in df.columns else None
        if col is None:
            ax.axis("off")
            ax.text(0.5, 0.5, "신뢰도 데이터 없음",
                    ha="center", va="center",
                    fontproperties=_fp(11), color=TEXT2,
                    transform=ax.transAxes)
            ax.set_facecolor(CARD)
            return

        # 감성별 신뢰도 바이올린/박스
        data_by_sent = [
            df[df["sentiment"] == s][col].values
            for s in ["긍정", "중립", "부정"]
            if not df[df["sentiment"] == s].empty
        ]
        labels_used = [
            s for s in ["긍정", "중립", "부정"]
            if not df[df["sentiment"] == s].empty
        ]
        colors_used = [SENTIMENT_COLORS[s] for s in labels_used]

        bp = ax.boxplot(data_by_sent, patch_artist=True, widths=0.5,
                        medianprops=dict(color="white", linewidth=2),
                        whiskerprops=dict(color=TEXT2),
                        capprops=dict(color=TEXT2),
                        flierprops=dict(markerfacecolor=TEXT2, markersize=4))
        for patch, color in zip(bp["boxes"], colors_used):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)
            patch.set_edgecolor(BG)

        ax.set_xticks(range(1, len(labels_used) + 1))
        ax.set_xticklabels(labels_used,
                           fontproperties=_fp(10))
        ax.set_yticks(ax.get_yticks())
        ax.set_yticklabels(
            [f"{v:.1f}" for v in ax.get_yticks()],
            fontproperties=_fp(8)
        )
        _ax_style(ax, title="감성별 신뢰도", ylabel="신뢰도")

    # ── 패널 4: 사이트별 감성 비교 ───────────────────────────────────────────
    def _plot_site_comparison(self, ax, df: pd.DataFrame):
        if "source" not in df.columns or df["source"].nunique() < 1:
            ax.axis("off")
            ax.set_facecolor(CARD)
            return

        site_label = {"naver":"네이버","daum":"다음","hankyung":"한국경제"}
        order = [s for s in ["naver","daum","hankyung"]
                 if s in df["source"].unique()]

        pivot = (df.groupby(["source","sentiment"])
                   .size()
                   .unstack(fill_value=0)
                   .reindex(order))

        x   = np.arange(len(order))
        w   = 0.22
        for i, sent in enumerate(["긍정","중립","부정"]):
            if sent not in pivot.columns:
                continue
            ax.bar(x + i*w, pivot[sent].values,
                   width=w, color=SENTIMENT_COLORS[sent],
                   edgecolor=BG, linewidth=0.6,
                   label=sent, alpha=0.9)

        ax.set_xticks(x + w)
        ax.set_xticklabels(
            [site_label.get(s, s) for s in order],
            fontproperties=_fp(10)
        )
        ax.set_yticks(ax.get_yticks())
        ax.set_yticklabels(
            [str(int(v)) for v in ax.get_yticks()],
            fontproperties=_fp(8)
        )

        legend_h = [
            mpatches.Patch(color=SENTIMENT_COLORS[s], label=s)
            for s in ["긍정","중립","부정"]
        ]
        ax.legend(handles=legend_h, frameon=False,
                  prop=_fp(9), labelcolor=TEXT,
                  loc="upper right")
        _ax_style(ax, title="사이트별 감성 비교", ylabel="건수")

    # ── 패널 5: 키워드 빈도 수평 막대 ────────────────────────────────────────
    def _plot_keywords(self, ax, df: pd.DataFrame):
        pos_words, neg_words = [], []
        for _, row in df.iterrows():
            if isinstance(row.get("matched_pos"), str) and row["matched_pos"]:
                pos_words.extend(w.strip() for w in row["matched_pos"].split(",") if w.strip())
            if isinstance(row.get("matched_neg"), str) and row["matched_neg"]:
                neg_words.extend(w.strip() for w in row["matched_neg"].split(",") if w.strip())

        top_pos = Counter(pos_words).most_common(7)
        top_neg = Counter(neg_words).most_common(7)

        if not top_pos and not top_neg:
            ax.text(0.5, 0.5, "키워드 없음", ha="center", va="center",
                    fontproperties=_fp(11), color=TEXT2,
                    transform=ax.transAxes)
            ax.set_facecolor(CARD)
            ax.set_title("감성 키워드", fontproperties=_fp(12, bold=True),
                         color=TEXT, pad=10)
            return

        # 부정을 왼쪽, 긍정을 오른쪽에 배치
        words  = [w for w, _ in top_neg[::-1]] + [w for w, _ in top_pos]
        scores = [-c for _, c in top_neg[::-1]] + [c for _, c in top_pos]
        colors = [SENTIMENT_COLORS["부정"]]*len(top_neg) + \
                 [SENTIMENT_COLORS["긍정"]]*len(top_pos)

        y = range(len(words))
        ax.barh(list(y), scores, color=colors, edgecolor=BG,
                linewidth=0.6, height=0.65, alpha=0.88)

        for yi, (w, s) in zip(y, zip(words, scores)):
            ax.text(
                s + (0.1 if s >= 0 else -0.1),
                yi,
                str(abs(int(s))),
                va="center", ha=("left" if s >= 0 else "right"),
                fontproperties=_fp(8), color=TEXT
            )

        ax.set_yticks(list(y))
        ax.set_yticklabels(words, fontproperties=_fp(9))
        ax.axvline(0, color=BORDER, linewidth=1)
        ax.set_title("감성 키워드 빈도 (←부정 │ 긍정→)",
                     fontproperties=_fp(12, bold=True), color=TEXT, pad=10)
        ax.set_facecolor(CARD)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        ax.tick_params(colors=TEXT2)
        ax.grid(axis="x", color=BORDER, linewidth=0.5, alpha=0.5)
        ax.set_axisbelow(True)

    # ── 패널 6: WordCloud ─────────────────────────────────────────────────────
    def _plot_wordcloud(self, ax, df: pd.DataFrame):
        text = " ".join(df["title"].astype(str).tolist())
        if not text.strip():
            ax.axis("off"); ax.set_facecolor(CARD); return

        try:
            wc_kwargs = dict(
                width=700, height=350,
                background_color=BG,
                colormap="RdYlGn",
                max_words=self.wordcloud_max_words,
                relative_scaling=0.4,
                min_font_size=10,
                collocations=False,
            )
            if FONT_PATH:
                wc_kwargs["font_path"] = FONT_PATH

            wc = WordCloud(**wc_kwargs).generate(text)
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            ax.set_title("핵심 단어 클라우드",
                         fontproperties=_fp(12, bold=True), color=TEXT, pad=10)
            ax.set_facecolor(CARD)
        except Exception as e:
            logger.warning(f"WordCloud 생성 실패: {e}")
            self._plot_summary_text(ax, df)

    # ── 패널 6 폴백: 요약 통계 텍스트 ───────────────────────────────────────
    def _plot_summary_text(self, ax, df: pd.DataFrame):
        ax.axis("off")
        ax.set_facecolor(CARD)
        ax.set_title("분석 요약", fontproperties=_fp(12, bold=True),
                     color=TEXT, pad=10)

        total  = len(df)
        counts = df["sentiment"].value_counts()
        avg_s  = df["score"].mean() if "score" in df.columns else 0
        avg_c  = df["confidence"].mean() if "confidence" in df.columns else 0

        lines = [
            ("총 기사",      f"{total}건"),
            ("긍정",         f"{counts.get('긍정',0)}건  ({counts.get('긍정',0)/total*100:.1f}%)"),
            ("부정",         f"{counts.get('부정',0)}건  ({counts.get('부정',0)/total*100:.1f}%)"),
            ("중립",         f"{counts.get('중립',0)}건  ({counts.get('중립',0)/total*100:.1f}%)"),
            ("평균 점수",    f"{avg_s:+.3f}"),
            ("평균 신뢰도",  f"{avg_c:.3f}"),
        ]
        y = 0.82
        for label, val in lines:
            ax.text(0.12, y, label, fontproperties=_fp(11),
                    color=TEXT2, transform=ax.transAxes)
            ax.text(0.55, y, val, fontproperties=_fp(11, bold=True),
                    color=TEXT,  transform=ax.transAxes)
            y -= 0.13