"""
visualizer.py - 감성 분석 결과 시각화 대시보드
"""

import os
import warnings
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from collections import Counter

warnings.filterwarnings("ignore")

def _set_korean_font():
    font_candidates = [
        "Malgun Gothic", "AppleGothic", "NanumGothic", "Arial"
    ]
    for font in font_candidates:
        try:
            fm.fontManager.addfont(None) # Refresh
            plt.rc("font", family=font)
            break
        except:
            continue

_set_korean_font()

COLORS = {
    "긍정": "#2ECC71",
    "중립": "#95A5A6",
    "부정": "#E74C3C",
    "bg":   "#1A1A2E",
    "card": "#16213E",
    "text": "#EAEAEA",
}

class DashboardVisualizer:
    def __init__(self, keyword: str, output_dir: str = "output"):
        self.keyword = keyword
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def create_dashboard(self, df: pd.DataFrame) -> str:
        if df.empty: return ""
        
        fig = plt.figure(figsize=(16, 10), facecolor=COLORS["bg"])
        fig.suptitle(f"[{self.keyword}] 뉴스 감성 분석 대시보드", color=COLORS["text"], fontsize=20, y=0.95)

        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.2)
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 0])
        ax4 = fig.add_subplot(gs[1, 1])

        # 1. 감성 비율 (Pie)
        counts = df["sentiment"].value_counts()
        ax1.pie(counts, labels=counts.index, autopct='%1.1f%%', colors=[COLORS.get(x, COLORS["중립"]) for x in counts.index], textprops={'color':"w"})
        ax1.set_title("전체 감성 분포", color=COLORS["text"])

        # 2. 사이트별 감성 (Bar)
        site_sentiment = df.groupby(['source', 'sentiment']).size().unstack(fill_value=0)
        site_sentiment.plot(kind='bar', stacked=True, ax=ax2, color=[COLORS.get(x, COLORS["중립"]) for x in site_sentiment.columns])
        ax2.set_title("출처별 감성 비교", color=COLORS["text"])
        ax2.tick_params(axis='x', colors=COLORS["text"], rotation=0)

        # 3. 감성 점수 히스토그램
        sns.histplot(df["score"], bins=15, ax=ax3, kde=True, color="#3498DB")
        ax3.set_title("감성 점수 분포", color=COLORS["text"])

        # 4. 주요 키워드
        words = []
        for ws in df["matched_pos"].tolist() + df["matched_neg"].tolist():
            if ws: words.extend(ws.split(", "))
        
        if words:
            top_words = Counter(words).most_common(10)
            word_df = pd.DataFrame(top_words, columns=['Word', 'Count'])
            sns.barplot(x='Count', y='Word', data=word_df, ax=ax4, palette="viridis")
            ax4.set_title("주요 감성 키워드 TOP 10", color=COLORS["text"])

        output_path = os.path.join(self.output_dir, "dashboard.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
        plt.close()
        return output_path
