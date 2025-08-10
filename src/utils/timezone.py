"""타임존 관련 유틸리티 함수들"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union

# 한국 타임존 설정 (UTC+9)
KST = timezone(timedelta(hours=9))
UTC = timezone.utc


def get_kst_now() -> datetime:
    """현재 한국 시간을 반환
    
    Returns:
        datetime: 한국 표준시(KST) 기준 현재 시간
    """
    return datetime.now(KST)


def utc_to_kst(utc_time: Union[datetime, str]) -> datetime:
    """UTC 시간을 한국 시간으로 변환
    
    Args:
        utc_time: UTC 시간 (datetime 객체 또는 ISO 형식 문자열)
        
    Returns:
        datetime: 한국 표준시로 변환된 시간
    """
    if isinstance(utc_time, str):
        # ISO 형식 문자열인 경우 파싱
        utc_time = datetime.fromisoformat(utc_time.replace('Z', '+00:00'))
    
    # timezone이 없는 경우 UTC로 설정
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=UTC)
    
    # KST로 변환
    return utc_time.astimezone(KST)


def kst_to_utc(kst_time: Union[datetime, str]) -> datetime:
    """한국 시간을 UTC로 변환
    
    Args:
        kst_time: 한국 시간 (datetime 객체 또는 ISO 형식 문자열)
        
    Returns:
        datetime: UTC로 변환된 시간
    """
    if isinstance(kst_time, str):
        # ISO 형식 문자열인 경우 파싱
        kst_time = datetime.fromisoformat(kst_time)
    
    # timezone이 없는 경우 KST로 설정
    if kst_time.tzinfo is None:
        kst_time = kst_time.replace(tzinfo=KST)
    
    # UTC로 변환
    return kst_time.astimezone(UTC)


def format_kst_time(dt: Optional[datetime] = None, 
                    format_str: str = "%Y-%m-%d %H:%M:%S KST") -> str:
    """한국 시간을 포맷팅된 문자열로 반환
    
    Args:
        dt: 변환할 datetime 객체 (None이면 현재 시간)
        format_str: 출력 형식 문자열
        
    Returns:
        str: 포맷팅된 한국 시간 문자열
    """
    if dt is None:
        dt = get_kst_now()
    elif dt.tzinfo is None:
        # timezone이 없으면 UTC로 가정하고 KST로 변환
        dt = utc_to_kst(dt)
    elif dt.tzinfo != KST:
        # 다른 timezone이면 KST로 변환
        dt = dt.astimezone(KST)
    
    return dt.strftime(format_str)


def get_timestamp_kst() -> str:
    """한국 시간 기준 ISO 형식 타임스탬프 반환
    
    Returns:
        str: ISO 형식의 한국 시간 타임스탬프
    """
    return get_kst_now().isoformat()