"""
로깅 설정 유틸리티
"""
import logging


def setup_logging(level=logging.INFO, format_string='%(asctime)s - %(levelname)s - %(message)s'):
    """로깅 설정"""
    logging.basicConfig(level=level, format=format_string)
    return logging.getLogger(__name__)
