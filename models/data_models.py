from dataclasses import dataclass, field
from enum import Enum
from typing import List


class LeaseType(Enum):
    JEONSE = "전세"
    MONTHLY = "월세"


class RiskGrade(Enum):
    """위험 등급 (서열: SAFE > CAUTION > DANGER > VERY_DANGEROUS)"""
    SAFE = "안전"
    CAUTION = "주의"
    DANGER = "위험"
    VERY_DANGEROUS = "매우 위험"


# 등급 서열 (숫자가 클수록 위험)
GRADE_ORDER = {
    RiskGrade.SAFE: 0,
    RiskGrade.CAUTION: 1,
    RiskGrade.DANGER: 2,
    RiskGrade.VERY_DANGEROUS: 3,
}


def worse_grade(a: RiskGrade, b: RiskGrade) -> RiskGrade:
    """두 등급 중 더 나쁜 등급 반환"""
    return a if GRADE_ORDER[a] >= GRADE_ORDER[b] else b


@dataclass
class RegistryData:
    """등기부등본 추출 데이터"""
    priority_mortgage_total: float = 0.0       # 선순위 근저당 설정액 합계 (원)
    priority_lease_deposit_total: float = 0.0  # 선순위 임차보증금 합계 (원)
    has_seizure: bool = False                   # 압류·가압류·가처분·경매개시 여부
    has_trust: bool = False                     # 신탁등기 여부
    has_recent_ownership_transfer: bool = False # 최근 2년 내 소유권 이전 여부
    raw_text: str = ""
    parse_notes: List[str] = field(default_factory=list)

    @property
    def priority_debt_total(self) -> float:
        """선순위 채권 합계 (근저당 + 임차보증금)"""
        return self.priority_mortgage_total + self.priority_lease_deposit_total


@dataclass
class BuildingData:
    """건축물대장 추출 데이터"""
    published_price: float = 0.0        # 공시가격 / 시가표준액 (원)
    is_illegal_building: bool = False   # 위반건축물 여부
    is_residential: bool = True         # 대장상 주거용 여부
    is_non_residential: bool = False    # 근린생활시설 등 비주거 여부
    main_use: str = ""                  # 주용도 원문
    building_type: str = ""             # 건물 유형 (단독·다가구 / 공동주택 등)
    raw_text: str = ""
    parse_notes: List[str] = field(default_factory=list)


@dataclass
class ContractInput:
    """소득·계약 입력 데이터"""
    annual_income: float = 0.0                   # 본인 연소득 (원)
    lease_type: LeaseType = LeaseType.JEONSE     # 임차유형
    deposit: float = 0.0                         # 보증금 (원)
    monthly_rent: float = 0.0                    # 월세액 (원, 전세는 0)
    contract_months: int = 24                    # 계약기간 (개월)
    elapsed_ratio: float = 0.0                   # 신청시점 경과비율 (0.0 ~ 1.0)
    is_metropolitan: bool = True                 # 수도권 여부


@dataclass
class RiskFactor:
    """위험 요인 단건"""
    name: str                    # 요인명
    value: str                   # 측정값 (표시용 문자열)
    deduction: float             # 감점 (양수 = 감점)
    description: str             # 상세 설명
    is_fatal: bool = False       # 치명적 요소 여부 (등급 상한 강제)
    grade_ceiling: RiskGrade = None  # 치명 요소의 등급 상한


@dataclass
class ScoreResult:
    """위험도 점수 결과"""
    base_score: float = 100.0
    final_score: float = 100.0
    grade: RiskGrade = RiskGrade.SAFE
    risk_factors: List[RiskFactor] = field(default_factory=list)

    # 계산 중간값
    jeonse_rate: float = 0.0        # 전세가율 (소수)
    priority_ratio: float = 0.0     # 선순위 비중 (소수)
    rir: float = 0.0                # RIR (소수)

    grade_ceiling_applied: bool = False
    grade_ceiling_reason: str = ""


@dataclass
class InsuranceJudgment:
    """보증보험 단일 상품 판정"""
    product_name: str            # 상품명
    eligible: bool               # 가입 가능 여부
    reasons: List[str] = field(default_factory=list)      # 가입 불가 사유 목록
    conditions: List[str] = field(default_factory=list)   # 가입 가능 조건/안내


@dataclass
class InsuranceResult:
    """보증보험 추천 전체 결과"""
    hug: InsuranceJudgment = None   # HUG 전세보증금반환보증
    hf: InsuranceJudgment = None    # HF 일반전세지킴보증
    sgi: InsuranceJudgment = None   # SGI 전세금보장신용보험
    summary: str = ""               # 종합 안내 메시지
