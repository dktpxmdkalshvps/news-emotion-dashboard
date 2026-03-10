"""
font_utils.py - 한글 폰트 전역 설정 유틸리티
모든 모듈에서 import하여 사용 → 한글 깨짐 완전 해결
"""
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

# ── 한글 지원 폰트 후보 경로 (우선순위 순) ─────────────────────────────────
_FONT_CANDIDATES = [
    # Linux (Noto CJK – 한국어 완전 지원)
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    # macOS
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Library/Fonts/AppleGothic.ttf",
    # Windows
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/gulim.ttc",
]

_KR_FONT_PROP: fm.FontProperties | None = None
_KR_FONT_NAME: str = "sans-serif"


def get_kr_font(size: int = 12) -> fm.FontProperties:
    """
    한글을 지원하는 FontProperties 객체를 반환합니다.
    크기별로 새 객체를 생성하므로 size 인자로 제어합니다.
    """
    global _KR_FONT_PROP, _KR_FONT_NAME

    if _KR_FONT_PROP is None:
        for path in _FONT_CANDIDATES:
            if Path(path).exists():
                _KR_FONT_PROP = fm.FontProperties(fname=path)
                _KR_FONT_NAME = _KR_FONT_PROP.get_name()
                break

        # 폴백: matplotlib 등록 폰트에서 탐색
        if _KR_FONT_PROP is None:
            for f in fm.fontManager.ttflist:
                if any(k in f.name for k in ["CJK", "Gothic", "Nanum", "Malgun"]):
                    _KR_FONT_PROP = fm.FontProperties(fname=f.fname)
                    _KR_FONT_NAME = f.name
                    break

    if _KR_FONT_PROP is not None:
        prop = fm.FontProperties(fname=_KR_FONT_PROP.get_file())
        prop.set_size(size)
        return prop

    # 최종 폴백
    return fm.FontProperties(size=size)


def apply_kr_font_globally():
    """
    matplotlib 전역 폰트를 한글 지원 폰트로 설정합니다.
    모듈 임포트 시 한 번만 호출합니다.
    """
    prop = get_kr_font()
    if _KR_FONT_NAME != "sans-serif":
        matplotlib.rc("font", family=_KR_FONT_NAME)
    matplotlib.rcParams["axes.unicode_minus"] = False

    # 폰트 캐시 갱신
    try:
        fm._load_fontmanager(try_read_cache=False)
    except Exception:
        pass


# ── 모듈 로드 시 자동 적용 ───────────────────────────────────────────────────
apply_kr_font_globally()