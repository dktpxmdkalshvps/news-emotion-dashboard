"""
logger.py - 중앙 집중식 로깅 시스템
구조화된 로깅을 제공하여 디버깅, 모니터링, 감시를 용이하게 합니다.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """컬러 기반 콘솔 포매터"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[92m',      # Green
        'WARNING': '\033[93m',   # Yellow
        'ERROR': '\033[91m',     # Red
        'CRITICAL': '\033[95m',  # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logger(name: str, log_level: int = logging.INFO, 
                 log_file: str = None) -> logging.Logger:
    """
    중앙 로거 설정
    
    Args:
        name: 로거 이름
        log_level: 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (선택사항)
    
    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = ColoredFormatter(
        '[%(levelname)s] %(name)s - %(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (옵션)
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    logger.propagate = False
    return logger


# 기본 앱 로거
app_logger = setup_logger(
    'news_sentiment',
    log_level=logging.INFO,
    log_file='logs/app.log'
)


def get_logger(name: str) -> logging.Logger:
    """서브 로거 획득"""
    return logging.getLogger(f'news_sentiment.{name}')
