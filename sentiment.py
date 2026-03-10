"""
sentiment.py - 감성 분석 엔진 v3.0
사전 기반(Lexicon) 분석 + KoBERT ML 분석 하이브리드 지원
KoBERT 미설치 시 자동으로 사전 기반으로 폴백
"""

import re
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
from logger import get_logger

logger = get_logger('sentiment')

# ── KoBERT / HuggingFace 로드 시도 ───────────────────────────────────────────
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
    logger.info("transformers 로드 성공 - ML 감성 분석 활성화")
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.info("transformers 없음 - 사전 기반 감성 분석 사용")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  감성 사전 (경제/금융 특화, 160+ 단어)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSITIVE_DICT: dict[str, float] = {
    # 주가/실적 강세
    "급등": 3.0, "상한가": 3.0, "신고가": 2.5, "최고가": 2.5,
    "강세": 2.0, "상승세": 2.0, "반등": 2.0, "돌파": 2.0,
    "상승": 1.5, "올랐": 1.5, "올라": 1.5,
    # 실적/재무
    "흑자": 2.5, "최대실적": 3.0, "어닝서프라이즈": 2.5,
    "역대최대": 2.5, "성장": 2.0, "증가": 1.5, "확대": 1.5,
    "수익": 1.5, "개선": 1.5, "초과달성": 2.5,
    # 사업/계약
    "수주": 2.0, "계약": 1.5, "타결": 1.5, "공급": 1.5,
    "협력": 1.0, "투자": 1.5, "혁신": 2.0, "성공": 2.0,
    # 긍정 평가
    "호재": 2.5, "유망": 1.5, "기대": 1.5, "낙관": 1.5,
    "선두": 1.5, "1위": 2.0, "수혜": 1.5, "배당": 2.0,
    "주주환원": 2.5, "자사주": 1.5, "흥행": 2.0,
    "호평": 2.0, "인기": 1.5, "신제품": 1.5, "신기술": 2.0,
    "회복": 1.5, "정상화": 1.5, "안정": 1.0, "승인": 1.5,
    # 강도어와 결합 패턴
    "강한상승": 2.5, "가파른상승": 2.5, "급격상승": 2.5,
}

NEGATIVE_DICT: dict[str, float] = {
    # 주가/실적 약세
    "급락": -3.0, "하한가": -3.0, "신저가": -2.5, "최저가": -2.5,
    "약세": -2.0, "하락세": -2.0, "추락": -2.5, "폭락": -3.0,
    "하락": -1.5, "내렸": -1.5, "내려": -1.5,
    # 실적/재무 부진
    "적자": -2.5, "손실": -2.5, "쇼크": -2.5, "감소": -1.5,
    "축소": -1.5, "부진": -2.0, "악화": -2.0, "후퇴": -1.5,
    # 법적/규제 리스크
    "파산": -3.0, "부도": -3.0, "횡령": -3.0, "구속": -2.5,
    "기소": -2.5, "압수수색": -2.5, "과징금": -2.0, "제재": -2.0,
    "소송": -1.5, "혐의": -2.0, "의혹": -1.5, "고발": -2.0,
    # 시장/경기 불안
    "위기": -2.5, "침체": -2.5, "불황": -2.5, "공포": -2.0,
    "불안": -1.5, "우려": -2.0, "리스크": -2.0, "경고": -1.5,
    "충격": -2.0, "붕괴": -3.0, "폭탄": -2.5,
    # 사업 차질
    "취소": -1.5, "중단": -1.5, "철수": -2.0, "폐쇄": -2.0,
    "결함": -2.5, "리콜": -2.0, "논란": -1.5, "갈등": -1.5,
    "분쟁": -1.5, "비판": -1.5, "규제": -1.5, "제한": -1.5,
}

# 복합어 (사전 키워드보다 우선 적용)
COMPOUND_DICT: dict[str, float] = {
    "급등락": 0.0,    # 중립화
    "상승세": 2.0,
    "하락세": -2.0,
    "최대실적": 3.0,
    "역대최대": 2.5,
    "어닝서프라이즈": 2.5,
    "어닝쇼크": -2.5,
}

# 강도 수정어
INTENSIFIERS  = {"매우": 1.3, "극히": 1.3, "상당히": 1.2, "더": 1.1, "정말": 1.2}
DIMINISHERS   = {"약간": 0.8, "조금": 0.8, "다소": 0.8, "다만": 0.7}
NEGATION_WORDS = ["아니", "않", "못", "없", "말", "부", "미", "불", "거부", "부정", "아냐"]


@dataclass
class SentimentResult:
    score:       float
    sentiment:   str         # '긍정' / '부정' / '중립'
    confidence:  float       # 0.0 ~ 1.0
    method:      str         # 'lexicon' / 'ml' / 'hybrid'
    matched_pos: list = field(default_factory=list)
    matched_neg: list = field(default_factory=list)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  사전 기반 분석기 (Lexicon)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LexiconAnalyzer:
    POS_THRESHOLD = 0.5
    NEG_THRESHOLD = -0.5

    def __init__(self, negation_window: int = 15):
        self.all_dict     = {**POSITIVE_DICT, **NEGATIVE_DICT}
        self.neg_window   = negation_window

    def score(self, title: str) -> SentimentResult:
        if not isinstance(title, str) or not title.strip():
            return SentimentResult(0.0, "중립", 0.0, "lexicon")

        total, n_match = 0.0, 0
        matched_pos, matched_neg = [], []

        # Step 1: 복합어 우선 매칭
        for expr, base in sorted(COMPOUND_DICT.items(), key=lambda x: -len(x[0])):
            if expr in title:
                total += base
                n_match += 1
                if base > 0: matched_pos.append(expr)
                elif base < 0: matched_neg.append(expr)

        # Step 2: 단일 키워드 (길이 내림차순으로 중복 방지)
        for word in sorted(self.all_dict, key=len, reverse=True):
            if word not in title:
                continue
            # 이미 복합어에서 처리된 경우 스킵
            if any(word in expr for expr in COMPOUND_DICT if expr in title):
                continue

            base = self.all_dict[word]
            idx  = title.find(word)

            # Step 3: 강도어 수정
            ctx_before = title[max(0, idx-15): idx]
            for w, m in INTENSIFIERS.items():
                if w in ctx_before: base *= m; break
            for w, m in DIMINISHERS.items():
                if w in ctx_before: base *= m; break

            # Step 4: 부정어 체크 (뒤쪽 15자)
            ctx_after = title[idx + len(word): idx + len(word) + self.neg_window]
            if any(neg in ctx_after for neg in NEGATION_WORDS):
                base = -base

            total += base
            n_match += 1
            if base > 0: matched_pos.append(word)
            elif base < 0: matched_neg.append(word)

        # 분류
        sentiment = ("긍정" if total > self.POS_THRESHOLD
                     else "부정" if total < self.NEG_THRESHOLD
                     else "중립")
        confidence = min(1.0, n_match * 0.25 + abs(total) * 0.08)

        return SentimentResult(
            score=round(total, 2),
            sentiment=sentiment,
            confidence=round(confidence, 3),
            method="lexicon",
            matched_pos=matched_pos,
            matched_neg=matched_neg,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  KoBERT ML 분석기
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class KoBERTAnalyzer:
    """
    HuggingFace 기반 한국어 금융 뉴스 감성 분석기

    권장 모델 (자동 다운로드):
      snunlp/KR-FinBert-SC   ← 금융 뉴스 특화 (추천)
      hun3359/klue-bert-base-sentiment
      monologg/koelectra-base-finetuned-sentiment

    설치:
      pip install transformers torch

    사용:
      analyzer = KoBERTAnalyzer()          # 기본 모델
      analyzer = KoBERTAnalyzer("snunlp/KR-FinBert-SC")
    """

    # 모델별 레이블 매핑 (모델에 따라 다름)
    _LABEL_MAP = {
        # KR-FinBert-SC
        "positive": "긍정", "negative": "부정", "neutral": "중립",
        # klue-bert
        "LABEL_0": "부정", "LABEL_1": "중립", "LABEL_2": "긍정",
        # koelectra
        "0": "부정", "1": "긍정",
    }

    def __init__(self, model_name: str = "snunlp/KR-FinBert-SC",
                 device: int = -1, batch_size: int = 16):
        """
        Args:
            model_name:  HuggingFace 모델 경로 또는 Hub 모델 ID
            device:      -1=CPU, 0=GPU
            batch_size:  배치 처리 크기
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers 라이브러리를 설치하세요:\n"
                              "  pip install transformers torch")

        self.model_name = model_name
        self.batch_size = batch_size
        self._pipe = None

        logger.info(f"KoBERT 모델 로드 중: {model_name}")
        try:
            self._pipe = pipeline(
                "text-classification",
                model=model_name,
                tokenizer=model_name,
                device=device,
                truncation=True,
                max_length=128,
            )
            logger.info(f"KoBERT 로드 완료: {model_name}")
        except Exception as e:
            logger.error(f"KoBERT 로드 실패: {e}")
            raise

    def score(self, title: str) -> SentimentResult:
        """단일 제목 분석"""
        if not isinstance(title, str) or not title.strip():
            return SentimentResult(0.0, "중립", 0.0, "ml")
        try:
            result = self._pipe(title[:512])[0]
            label  = self._map_label(result["label"])
            conf   = round(float(result["score"]), 3)
            # ML 점수를 -3~+3 스케일로 변환
            score = self._conf_to_score(label, conf)
            return SentimentResult(score, label, conf, "ml")
        except Exception as e:
            logger.warning(f"KoBERT 추론 오류: {e}")
            return SentimentResult(0.0, "중립", 0.0, "ml")

    def score_batch(self, titles: list[str]) -> list[SentimentResult]:
        """배치 추론 (대량 처리 시 효율적)"""
        results = []
        for i in range(0, len(titles), self.batch_size):
            batch = titles[i: i + self.batch_size]
            batch_clean = [t[:512] if isinstance(t, str) else "" for t in batch]
            try:
                preds = self._pipe(batch_clean)
                for pred in preds:
                    label = self._map_label(pred["label"])
                    conf  = round(float(pred["score"]), 3)
                    results.append(SentimentResult(
                        self._conf_to_score(label, conf),
                        label, conf, "ml"
                    ))
            except Exception as e:
                logger.warning(f"KoBERT 배치 오류: {e}")
                results.extend([
                    SentimentResult(0.0, "중립", 0.0, "ml")
                    for _ in batch
                ])
        return results

    def _map_label(self, raw: str) -> str:
        return self._LABEL_MAP.get(raw.lower(), self._LABEL_MAP.get(raw, "중립"))

    @staticmethod
    def _conf_to_score(sentiment: str, confidence: float) -> float:
        """신뢰도를 -3~+3 점수로 변환"""
        base = confidence * 3.0
        if sentiment == "긍정":   return round(base, 2)
        elif sentiment == "부정": return round(-base, 2)
        return 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  통합 감성 분석기 (퍼사드)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class SentimentAnalyzer:
    """
    Lexicon + KoBERT 하이브리드 감성 분석기

    mode 옵션:
      'lexicon'  - 사전 기반만 사용 (빠름, 기본값)
      'ml'       - KoBERT만 사용 (정확, transformers 필요)
      'hybrid'   - 두 방법 앙상블 (가장 정확)

    사용 예:
        # 사전 기반 (항상 사용 가능)
        analyzer = SentimentAnalyzer(mode='lexicon')

        # KoBERT (transformers 설치 후)
        analyzer = SentimentAnalyzer(mode='ml',
                                     ml_model='snunlp/KR-FinBert-SC')

        # 하이브리드
        analyzer = SentimentAnalyzer(mode='hybrid')

        df = analyzer.analyze(df)
    """

    def __init__(
        self,
        mode: str = "lexicon",
        ml_model: str = "snunlp/KR-FinBert-SC",
        hybrid_ml_weight: float = 0.6,
        enable_compound: bool = True,
        enable_intensifiers: bool = True,
        negation_context_window: int = 15,
    ):
        """
        Args:
            mode:             'lexicon' | 'ml' | 'hybrid'
            ml_model:         HuggingFace 모델 ID
            hybrid_ml_weight: 하이브리드 시 ML 점수 비중 (0~1)
        """
        self.mode             = mode
        self.ml_weight        = hybrid_ml_weight
        self._lexicon         = LexiconAnalyzer(negation_context_window)
        self._ml: Optional[KoBERTAnalyzer] = None

        # ML 초기화
        if mode in ("ml", "hybrid"):
            if not TRANSFORMERS_AVAILABLE:
                logger.warning(
                    "transformers 미설치 → 사전 기반으로 자동 폴백\n"
                    "  설치: pip install transformers torch"
                )
                self.mode = "lexicon"
            else:
                try:
                    self._ml = KoBERTAnalyzer(ml_model)
                except Exception as e:
                    logger.warning(f"KoBERT 초기화 실패 → 사전 기반으로 폴백: {e}")
                    self.mode = "lexicon"

        logger.info(f"감성 분석기 초기화: mode={self.mode}")

    # ── 공개 API ─────────────────────────────────────────────────────
    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrame의 'title' 컬럼을 분석하여 감성 컬럼을 추가합니다.
        추가 컬럼: score, sentiment, confidence, method, matched_pos, matched_neg
        """
        titles  = df["title"].tolist()
        results = self._analyze_batch(titles)

        df = df.copy()
        df["score"]       = [r.score       for r in results]
        df["sentiment"]   = [r.sentiment   for r in results]
        df["confidence"]  = [r.confidence  for r in results]
        df["method"]      = [r.method      for r in results]
        df["matched_pos"] = [", ".join(r.matched_pos) for r in results]
        df["matched_neg"] = [", ".join(r.matched_neg) for r in results]
        return df

    def analyze_single(self, title: str) -> SentimentResult:
        """단일 제목 분석"""
        return self._score(title)

    def get_statistics(self, df: pd.DataFrame) -> dict:
        counts = df["sentiment"].value_counts()
        total  = len(df)
        if total == 0:
            return {k: 0 for k in ["total","positive","negative","neutral",
                                   "pos_ratio","neg_ratio","neutral_ratio",
                                   "avg_score","avg_confidence"]}
        return {
            "total":          total,
            "positive":       int(counts.get("긍정", 0)),
            "negative":       int(counts.get("부정", 0)),
            "neutral":        int(counts.get("중립", 0)),
            "pos_ratio":      round(counts.get("긍정", 0) / total * 100, 1),
            "neg_ratio":      round(counts.get("부정", 0) / total * 100, 1),
            "neutral_ratio":  round(counts.get("중립", 0) / total * 100, 1),
            "avg_score":      round(df["score"].mean(), 3),
            "avg_confidence": round(df.get("confidence", pd.Series([0])).mean(), 3),
            "max_score":      round(df["score"].max(), 2),
            "min_score":      round(df["score"].min(), 2),
            "mode":           df.get("method", pd.Series(["lexicon"])).iloc[0],
        }

    # ── 내부 로직 ─────────────────────────────────────────────────────
    def _analyze_batch(self, titles: list[str]) -> list[SentimentResult]:
        if self.mode == "ml" and self._ml:
            return self._ml.score_batch(titles)
        elif self.mode == "hybrid" and self._ml:
            lex_res = [self._lexicon.score(t) for t in titles]
            ml_res  = self._ml.score_batch(titles)
            return [self._ensemble(l, m) for l, m in zip(lex_res, ml_res)]
        else:
            return [self._lexicon.score(t) for t in titles]

    def _score(self, title: str) -> SentimentResult:
        if self.mode == "ml" and self._ml:
            return self._ml.score(title)
        elif self.mode == "hybrid" and self._ml:
            return self._ensemble(self._lexicon.score(title), self._ml.score(title))
        return self._lexicon.score(title)

    def _ensemble(self, lex: SentimentResult, ml: SentimentResult) -> SentimentResult:
        """Lexicon + ML 앙상블"""
        w_ml  = self.ml_weight
        w_lex = 1.0 - w_ml
        combined = round(lex.score * w_lex + ml.score * w_ml, 2)
        conf     = round(lex.confidence * w_lex + ml.confidence * w_ml, 3)
        if combined > 0.5:
            sentiment = "긍정"
        elif combined < -0.5:
            sentiment = "부정"
        else:
            sentiment = "중립"
        return SentimentResult(
            score=combined, sentiment=sentiment,
            confidence=conf, method="hybrid",
            matched_pos=lex.matched_pos,
            matched_neg=lex.matched_neg,
        )