"""
sentiment.py - 뉴스 감성 분석 엔진
사전 기반(Lexicon-based) 감성 분석 및 부정어 처리
"""

import re
import pandas as pd
from dataclasses import dataclass, field


# -- 감성 사전 데이터 ---------------------------------------------------------------------
# 긍정 사전: { "단어": 점수 }  (긍정=양수, 부정=음수)
# 점수 가중치: +1(일반) ~ +3(강력)

POSITIVE_DICT: dict[str, float] = {
    # 경제/증권 긍정 키워드
    "급등":       3.0,
    "상한가":     3.0,
    "최고가":     2.5,
    "호재":       2.0,
    "매수":       1.5,
    "반등":       1.5,
    "흑자":       2.0,
    "성장":       2.0,
    "수주":       2.0,
    "돌파":       1.5,
    "강세":       2.0,
    "기대":       1.5,
    "최대":       1.5,
    "혁신":       2.0,
    "상승":       1.0,
    "배당":       2.0,
    "배당확대":   2.5,
    "주주환원":   2.5,
    # 일반 긍정
    "우수":       2.0,
    "좋은":       1.5,
    "1위":        2.0,
    "최초":       2.0,
    "성공":       1.5,
    "인기":       2.0,
    "협력":       1.0,
    "활발":       1.5,
    "주목":       1.5,
    "유망":       1.5,
    "신제품":     1.5,
    "신기술":     2.5,
    "공급":       1.5,
    "체결":       1.5,
    "출시":       0.5,
    "박차":       1.0,
    "목표":       1.5,
    "전망":       1.5,
    "확대":       1.0,
    "낙관":       2.0,
    "최적":       1.0,
}

NEGATIVE_DICT: dict[str, float] = {
    # 경제/증권 부정 키워드
    "급락":       -3.0,
    "하한가":     -3.0,
    "폭락":       -3.0,
    "악재":       -2.0,
    "매도":       -1.5,
    "하락":       -1.5,
    "적자":       -2.0,
    "손실":       -3.0,
    "우려":       -2.5,
    "불확실":     -2.0,
    "횡령":       -3.0,
    "쇼크":       -2.5,
    "부도":       -3.0,
    "파산":       -3.0,
    "조사":       -1.5,
    "과징금":     -2.0,
    "침체":       -2.0,
    "위기":       -2.0,
    # 기타 부정 키워드
    "결함":       -2.5,
    "리콜":       -2.0,
    "논란":       -2.0,
    "부진":       -2.0,
    "제한":       -1.5,
    "중단":       -1.5,
    "폐쇄":       -2.0,
    "실망":       -1.5,
    "압수수색":   -2.5,
    "취소":       -1.5,
    "거부":       -2.0,
    "경고":       -2.0,
    "부작용":     -2.0,
    "갈등":       -1.5,
    "분쟁":       -1.5,
    "소송":       -1.5,
    "리스크":     -1.5,
    "직격탄":     -2.0,
    "부담":       -1.0,
    "악화":       -2.0,
    "차단":       -1.5,
    "부인":       -1.5,
    "혐의":       -2.0,
    "의혹":       -1.5,
    "구속":       -2.5,
    "압수":       -1.5,
    "비판":       -1.5,
    "공백":       -2.0,
    "사퇴":       -2.0,
}

# 부정/반전어 - 감성 점수의 극성을 반전시킴
NEGATION_WORDS = ["않다", "없다", "못해", "모르다", "아냐", "아니", "말다", "어렵다"]


@dataclass
class SentimentResult:
    score: float
    sentiment: str          # '긍정' / '부정' / '중립'
    matched_pos: list[str] = field(default_factory=list)
    matched_neg: list[str] = field(default_factory=list)


class SentimentAnalyzer:
    """
    뉴스 제목을 바탕으로 감성 분석 수행
    알고리즘:
      1. 제목에 포함된 감성 키워드 점수 합산
      2. 부정어(않다, 없다 등) 수식 시 감성 극성 반전
      3. 최종 점수에 따라 긍정/부정/중립 분류
    """

    POS_THRESHOLD = 0.5
    NEG_THRESHOLD = -0.5

    def __init__(
        self,
        pos_dict: dict = None,
        neg_dict: dict = None,
    ):
        self.pos_dict = pos_dict or POSITIVE_DICT
        self.neg_dict = neg_dict or NEGATIVE_DICT
        self.all_dict = {**self.pos_dict, **self.neg_dict}

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrame의 'title' 컬럼을 분석하여 감성 결과 추가
        """
        results = df["title"].apply(self._score_title)

        df = df.copy()
        df["score"]       = results.apply(lambda r: r.score)
        df["sentiment"]   = results.apply(lambda r: r.sentiment)
        df["matched_pos"] = results.apply(lambda r: ", ".join(r.matched_pos))
        df["matched_neg"] = results.apply(lambda r: ", ".join(r.matched_neg))
        return df

    def _score_title(self, title: str) -> SentimentResult:
        if not isinstance(title, str) or not title.strip():
            return SentimentResult(score=0.0, sentiment="중립")

        total_score = 0.0
        matched_pos = []
        matched_neg = []

        # 긴 단어부터 매칭되도록 정렬 (중복 방지 기초)
        sorted_keys = sorted(self.all_dict.keys(), key=len, reverse=True)

        for word in sorted_keys:
            if word not in title:
                continue

            base_score = self.all_dict[word]
            
            # 부정어(반전어) 체크 (단어 뒤 7자 내외 확인)
            idx = title.find(word)
            context_after = title[idx + len(word): idx + len(word) + 7]
            has_negation = any(neg in context_after for neg in NEGATION_WORDS)

            actual_score = -base_score if has_negation else base_score

            if actual_score > 0:
                matched_pos.append(word)
            elif actual_score < 0:
                matched_neg.append(word)

            total_score += actual_score

        # 감성 라벨링
        if total_score > self.POS_THRESHOLD:
            sentiment = "긍정"
        elif total_score < self.NEG_THRESHOLD:
            sentiment = "부정"
        else:
            sentiment = "중립"

        return SentimentResult(
            score=round(total_score, 2),
            sentiment=sentiment,
            matched_pos=matched_pos,
            matched_neg=matched_neg,
        )

    def get_statistics(self, df: pd.DataFrame) -> dict:
        counts = df["sentiment"].value_counts()
        total = len(df)
        if total == 0:
            return {"total": 0, "positive": 0, "negative": 0, "neutral": 0, 
                    "pos_ratio": 0, "neg_ratio": 0, "avg_score": 0}
                    
        return {
            "total":       total,
            "positive":    counts.get("긍정", 0),
            "negative":    counts.get("부정", 0),
            "neutral":     counts.get("중립", 0),
            "pos_ratio":   round(counts.get("긍정", 0) / total * 100, 1),
            "neg_ratio":   round(counts.get("부정", 0) / total * 100, 1),
            "avg_score":   round(df["score"].mean(), 3),
        }
