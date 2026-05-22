"""건축물대장 텍스트 파싱 모듈.

추출된 텍스트에서 공시가격, 위반건축물 여부, 주용도 등을 파싱한다.
"""

import re
from typing import List

from models.data_models import BuildingData


# 주거용 용도 키워드
_RESIDENTIAL_KEYWORDS = [
    "단독주택", "다가구주택", "다중주택", "공관",
    "아파트", "연립주택", "다세대주택", "기숙사",
    "공동주택", "오피스텔",
]

# 비주거 용도 키워드 (근린생활시설 등)
_NON_RESIDENTIAL_KEYWORDS = [
    "근린생활시설", "제1종근린생활시설", "제2종근린생활시설",
    "업무시설", "판매시설", "숙박시설", "위락시설",
    "공장", "창고", "운수시설",
]

# 단독·다가구 건물 유형 (HF 선순위 비율 제한 다름)
_SINGLE_HOUSE_KEYWORDS = ["단독주택", "다가구주택", "다중주택"]


def parse_building(text: str) -> BuildingData:
    """건축물대장 텍스트를 파싱하여 BuildingData를 반환한다."""
    data = BuildingData(raw_text=text)

    data.published_price = _parse_published_price(text, data.parse_notes)
    data.is_illegal_building = _detect_illegal_building(text, data.parse_notes)
    data.main_use, data.is_residential, data.is_non_residential = _parse_main_use(text, data.parse_notes)
    data.building_type = _classify_building_type(data.main_use)

    return data


def _parse_amount(raw: str) -> float:
    return float(raw.replace(",", "").replace(" ", ""))


def _parse_published_price(text: str, notes: List[str]) -> float:
    """공시가격 또는 시가표준액 파싱.

    우선순위:
    1. 공시가격 (개별주택/공동주택 공시가격)
    2. 시가표준액 (건축물대장 기재 기준가)
    3. 과세표준액
    """
    patterns = [
        (r'공시가격\s*[:：]?\s*금?\s*([\d,]+)\s*원?', "공시가격"),
        (r'주택공시가격\s*[:：]?\s*금?\s*([\d,]+)\s*원?', "주택공시가격"),
        (r'개별주택가격\s*[:：]?\s*금?\s*([\d,]+)\s*원?', "개별주택가격"),
        (r'공동주택가격\s*[:：]?\s*금?\s*([\d,]+)\s*원?', "공동주택가격"),
        (r'시가표준액\s*[:：]?\s*금?\s*([\d,]+)\s*원?', "시가표준액"),
        (r'과세표준액\s*[:：]?\s*금?\s*([\d,]+)\s*원?', "과세표준액"),
        # 숫자만 있는 테이블 형식 (예: 공시가격 줄 다음 줄에 숫자)
        (r'공시가격[^\n]*\n\s*([\d,]+)', "공시가격(테이블)"),
    ]

    for pattern, label in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                amount = _parse_amount(match.group(1))
                if amount > 0:
                    notes.append(f"{label} 감지: {amount:,.0f}원")
                    return amount
            except ValueError:
                pass

    notes.append("공시가격 미감지 — 수동 입력 필요")
    return 0.0


def _detect_illegal_building(text: str, notes: List[str]) -> bool:
    """위반건축물 여부 탐지"""
    if re.search(r'위반건축물', text):
        # "위반건축물 아님", "위반건축물 없음" 등 부정 표현 확인
        neg_patterns = [r'위반건축물\s*(아님|없음|해당없음|해당\s*없음|N)']
        for neg in neg_patterns:
            if re.search(neg, text):
                notes.append("위반건축물 아님 (부정 표현 감지)")
                return False
        notes.append("위반건축물 감지")
        return True

    notes.append("위반건축물 없음")
    return False


def _parse_main_use(text: str, notes: List[str]):
    """주용도 파싱 및 주거/비주거 판별.

    Returns:
        (main_use_str, is_residential, is_non_residential)
    """
    # 주용도 필드 직접 추출
    use_patterns = [
        r'주\s*용\s*도\s*[:：]?\s*([^\n\r]+)',
        r'용\s*도\s*[:：]?\s*([^\n\r]+)',
        r'건축물용도\s*[:：]?\s*([^\n\r]+)',
    ]

    main_use = ""
    for pattern in use_patterns:
        match = re.search(pattern, text)
        if match:
            main_use = match.group(1).strip()
            break

    if not main_use:
        notes.append("주용도 필드 미감지 — 전체 텍스트에서 키워드 탐색")

    # 전체 텍스트에서 용도 키워드 탐색
    combined = (main_use + " " + text).lower()

    is_residential = any(kw in combined for kw in _RESIDENTIAL_KEYWORDS)
    is_non_residential = any(kw in combined for kw in _NON_RESIDENTIAL_KEYWORDS)

    if is_residential:
        notes.append(f"주거용 건물 확인: {main_use or '키워드 감지'}")
    elif is_non_residential:
        notes.append(f"비주거 건물 감지: {main_use or '키워드 감지'}")
    else:
        notes.append(f"용도 불명확: '{main_use}'")
        # 용도 불명확 시 보수적으로 주거용으로 처리 (감점은 scorer에서 판단)

    return main_use, is_residential, is_non_residential


def _classify_building_type(main_use: str) -> str:
    """건물 유형 분류 (HF 선순위 비율 제한 적용 시 사용)"""
    for kw in _SINGLE_HOUSE_KEYWORDS:
        if kw in main_use:
            return "단독·다가구"
    return "공동주택 등"
