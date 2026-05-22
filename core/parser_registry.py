"""등기부등본 텍스트 파싱 모듈.

추출된 텍스트에서 정규식으로 필요한 항목을 파싱한다.
실제 등기부등본 PDF 포맷이 다양하므로, 여러 패턴을 시도해 최선값을 반환한다.
"""

import re
from datetime import datetime
from typing import List, Tuple

from models.data_models import RegistryData


# 현재 연도 기준 최근 이전 판단 기준 (2년)
_RECENT_YEARS = 2


def parse_registry(text: str) -> RegistryData:
    """등기부등본 텍스트를 파싱하여 RegistryData를 반환한다."""
    data = RegistryData(raw_text=text)

    data.priority_mortgage_total = _parse_mortgage_total(text, data.parse_notes)
    data.priority_lease_deposit_total = _parse_lease_deposit_total(text, data.parse_notes)
    data.has_seizure = _detect_seizure(text, data.parse_notes)
    data.has_trust = _detect_trust(text, data.parse_notes)
    data.has_recent_ownership_transfer = _detect_recent_transfer(text, data.parse_notes)

    return data


def _parse_amount(raw: str) -> float:
    """쉼표 포함 금액 문자열을 float으로 변환"""
    return float(raw.replace(",", "").replace(" ", ""))


def _parse_mortgage_total(text: str, notes: List[str]) -> float:
    """선순위 근저당 설정액(채권최고액) 합산.

    등기부등본 을구에 기재된 채권최고액을 모두 합산한다.
    말소된 근저당은 '말소' 키워드로 필터링한다.
    """
    # 채권최고액 패턴: "채권최고액 금 XXX,XXX,XXX원" 또는 "채권최고액 XXX,XXX,XXX원"
    patterns = [
        r'채권최고액\s*금\s*([\d,]+)\s*원',
        r'채권최고액\s*:\s*금?\s*([\d,]+)\s*원',
        r'채권최고액\s*([\d,]+)\s*원',
    ]

    amounts = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            start = match.start()
            # 해당 줄 앞뒤 100자 컨텍스트에서 말소 여부 확인
            context_start = max(0, start - 200)
            context_end = min(len(text), match.end() + 200)
            context = text[context_start:context_end]

            if _is_cancelled(context, match.group(0)):
                notes.append(f"말소된 근저당 제외: {match.group(1)}원")
                continue

            try:
                amount = _parse_amount(match.group(1))
                amounts.append(amount)
            except ValueError:
                pass

    total = sum(amounts)
    if amounts:
        notes.append(f"근저당 {len(amounts)}건 합계: {total:,.0f}원")
    else:
        notes.append("근저당 항목 미감지")

    return total


def _parse_lease_deposit_total(text: str, notes: List[str]) -> float:
    """선순위 임차보증금 합산.

    전세권 또는 임차권 등기의 보증금을 합산한다.
    """
    patterns = [
        r'임차보증금\s*금\s*([\d,]+)\s*원',
        r'임차보증금\s*:\s*금?\s*([\d,]+)\s*원',
        r'임차보증금\s*([\d,]+)\s*원',
        r'전세금\s*금\s*([\d,]+)\s*원',
        r'전세금\s*([\d,]+)\s*원',
        # 전세권 설정 금액
        r'전세권설정\s*금\s*([\d,]+)\s*원',
        r'전세권설정액\s*금?\s*([\d,]+)\s*원',
    ]

    amounts = []
    seen_positions = set()

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            pos = match.start()
            if pos in seen_positions:
                continue

            context_start = max(0, pos - 200)
            context_end = min(len(text), match.end() + 200)
            context = text[context_start:context_end]

            if _is_cancelled(context, match.group(0)):
                notes.append(f"말소된 임차보증금 제외: {match.group(1)}원")
                continue

            try:
                amount = _parse_amount(match.group(1))
                amounts.append(amount)
                seen_positions.add(pos)
            except ValueError:
                pass

    total = sum(amounts)
    if amounts:
        notes.append(f"임차보증금 {len(amounts)}건 합계: {total:,.0f}원")
    else:
        notes.append("임차보증금 항목 미감지")

    return total


def _is_cancelled(context: str, anchor: str) -> bool:
    """해당 권리가 말소되었는지 판단.

    말소, 해지, 취소, 등기말소 등 키워드가 근처에 있으면 말소로 판단.
    """
    cancel_keywords = ["말소", "해지", "취소", "등기말소", "변경등기 말소"]
    for kw in cancel_keywords:
        if kw in context:
            return True
    return False


def _detect_seizure(text: str, notes: List[str]) -> bool:
    """압류·가압류·가처분·경매개시 여부 탐지"""
    patterns = [
        (r'압류', "압류"),
        (r'가압류', "가압류"),
        (r'가처분', "가처분"),
        (r'경매개시결정', "경매개시결정"),
        (r'임의경매', "임의경매"),
        (r'강제경매', "강제경매"),
    ]

    found = []
    for pattern, label in patterns:
        if re.search(pattern, text):
            # 말소된 항목인지 확인 (간이 체크)
            matches = list(re.finditer(pattern, text))
            active = False
            for m in matches:
                ctx_start = max(0, m.start() - 300)
                ctx_end = min(len(text), m.end() + 100)
                ctx = text[ctx_start:ctx_end]
                if not _is_cancelled(ctx, m.group(0)):
                    active = True
                    break
            if active:
                found.append(label)

    if found:
        notes.append(f"권리침해 감지: {', '.join(found)}")
        return True

    notes.append("압류·경매 항목 없음")
    return False


def _detect_trust(text: str, notes: List[str]) -> bool:
    """신탁등기 여부 탐지.

    단순 '신탁' 키워드가 아니라 신탁등기 관련 맥락에서만 탐지.
    금융기관명(신탁은행, 자산신탁 등)은 등기 원인이 될 수 있으므로
    '신탁등기', '신탁원부', '위탁자' 등 등기 원인 패턴으로 판별.

    말소 처리:
    신탁 말소 기록("신탁등기말소", "N번 신탁등기말소")은 원본 신탁등기 항목보다
    이후 항목에 기재되므로, 컨텍스트를 매치 위치부터 문서 끝까지 확장해 검사한다.
    """
    trust_patterns = [
        r'신탁등기',
        r'신탁원부',
        r'위탁자\s',
        r'수탁자\s',
        r'신탁\s*재산',
        r'부동산\s*신탁',
        r'담보신탁',
        r'관리신탁',
        r'처분신탁',
    ]

    for pattern in trust_patterns:
        matches = list(re.finditer(pattern, text))
        if not matches:
            continue

        for m in matches:
            # 신탁 말소는 원본 등기 이후 항목에 기재되므로
            # 컨텍스트를 "매치 위치 ~ 문서 끝"까지 확장해 후방 말소 기록을 탐지한다.
            context = text[max(0, m.start() - 50):]
            if not _is_cancelled_trust(context):
                notes.append(f"신탁등기 감지 (유효): 패턴 '{pattern}'")
                return True
            else:
                notes.append(f"신탁등기 말소 확인 — 유효 아님: 패턴 '{pattern}'")

    notes.append("신탁등기 없음")
    return False


def _is_cancelled_trust(context: str) -> bool:
    """신탁등기 전용 말소 판별.

    컨텍스트(매치 위치 이후 전체)에서 신탁 말소 키워드를 탐색한다.
    "신탁등기말소", "N번 신탁등기말소" 등의 패턴도 포함한다.
    """
    # 직접 말소 키워드
    cancel_keywords = [
        "신탁등기말소",
        "신탁말소",
        "신탁 말소",
        "신탁원부말소",
    ]
    for kw in cancel_keywords:
        if kw in context:
            return True

    # "[숫자]번 ... 말소" 패턴 (갑구 항목 번호 참조 말소)
    if re.search(r'\d+\s*번\s*[^。\n]*말소', context):
        return True

    return False


def _detect_recent_transfer(text: str, notes: List[str]) -> bool:
    """최근 2년 이내 소유권 이전 여부 탐지"""
    current_year = datetime.now().year
    threshold_year = current_year - _RECENT_YEARS

    # 소유권이전 등기 날짜 패턴
    transfer_patterns = [
        r'소유권이전.*?(\d{4})\s*년',
        r'(\d{4})\s*년.*?소유권이전',
        r'이전\s*(\d{4})[.\-년]',
    ]

    for pattern in transfer_patterns:
        for match in re.finditer(pattern, text, re.DOTALL):
            try:
                year = int(match.group(1))
                if year >= threshold_year:
                    notes.append(f"최근 소유권 이전 감지: {year}년")
                    return True
            except (ValueError, IndexError):
                pass

    # 연도 없이 '소유권이전'만 있는 경우 주의 표시
    if re.search(r'소유권이전', text):
        notes.append("소유권이전 기록 있음 (연도 미확인)")

    return False
