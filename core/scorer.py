"""위험도 점수 계산 모듈.

처리 흐름:
  1. 100점 시작
  2. 감점형 지표(전세가율·선순위비중·RIR·보조요소) 순서대로 감점
  3. 점수 기반 기본 등급 산정
  4. 치명적 요소로 등급 상한 강제 적용 (등급 희석 방지)
  5. 위험 사유 목록 반환
"""

from models.data_models import (
    BuildingData, ContractInput, LeaseType, RegistryData,
    RiskFactor, RiskGrade, ScoreResult, GRADE_ORDER, worse_grade,
)

# 전월세전환율 (법정 상한: 연 5%)
JEONSE_CONVERSION_RATE = 0.05


def calculate_score(
    registry: RegistryData,
    building: BuildingData,
    contract: ContractInput,
) -> ScoreResult:
    """위험도 점수를 계산한다.

    Args:
        registry: 등기부등본 파싱 결과
        building: 건축물대장 파싱 결과
        contract: 소득·계약 입력값

    Returns:
        ScoreResult — 점수, 등급, 위험요인 목록 포함
    """
    result = ScoreResult()
    house_price = building.published_price
    priority_debt = registry.priority_debt_total
    deposit = contract.deposit

    # ── 1. 감점형 지표 ──────────────────────────────────────────────
    _score_jeonse_rate(result, deposit, priority_debt, house_price)
    _score_priority_ratio(result, priority_debt, house_price)
    _score_rir(result, contract)
    _score_auxiliary(result, registry, building)

    # ── 2. 점수 → 기본 등급 ─────────────────────────────────────────
    result.final_score = max(0.0, result.base_score - sum(f.deduction for f in result.risk_factors))
    result.grade = _score_to_grade(result.final_score)

    # ── 3. 치명적 요소 등급 상한 강제 ──────────────────────────────
    _apply_fatal_ceiling(result, registry, building)

    return result


# ── 감점 계산 함수들 ────────────────────────────────────────────────

def _score_jeonse_rate(
    result: ScoreResult,
    deposit: float,
    priority_debt: float,
    house_price: float,
) -> None:
    """전세가율 감점: (보증금 + 선순위채권) / 주택가격"""
    if house_price <= 0:
        result.risk_factors.append(RiskFactor(
            name="전세가율",
            value="계산불가 (공시가격 미입력)",
            deduction=0,
            description="공시가격을 입력해야 전세가율을 계산할 수 있습니다.",
        ))
        return

    rate = (deposit + priority_debt) / house_price
    result.jeonse_rate = rate
    rate_pct = rate * 100

    if rate < 0.70:
        deduction = 0
        desc = f"전세가율 {rate_pct:.1f}% — 안전 범위 (70% 미만)"
    elif rate < 0.80:
        deduction = 10
        desc = f"전세가율 {rate_pct:.1f}% — 주의 (70~80%): 시세 하락 시 보증금 회수 위험"
    elif rate < 1.00:
        deduction = 20
        desc = f"전세가율 {rate_pct:.1f}% — 위험 (80~100%): 경매 시 보증금 손실 가능성 높음"
    else:
        deduction = 30
        desc = f"전세가율 {rate_pct:.1f}% — 깡통전세 (100% 이상): 보증금 전액 손실 위험"

    result.risk_factors.append(RiskFactor(
        name="전세가율",
        value=f"{rate_pct:.1f}%",
        deduction=deduction,
        description=desc,
    ))


def _score_priority_ratio(
    result: ScoreResult,
    priority_debt: float,
    house_price: float,
) -> None:
    """선순위 비중 감점: 선순위채권 / 주택가격"""
    if house_price <= 0:
        return

    ratio = priority_debt / house_price
    result.priority_ratio = ratio
    ratio_pct = ratio * 100

    if ratio < 0.30:
        deduction = 0
        desc = f"선순위 비중 {ratio_pct:.1f}% — 안전 범위 (30% 미만)"
    elif ratio < 0.50:
        deduction = 10
        desc = f"선순위 비중 {ratio_pct:.1f}% — 주의 (30~50%): 경매 낙찰 후 배당 부족 가능"
    else:
        deduction = 20
        desc = f"선순위 비중 {ratio_pct:.1f}% — 위험 (50% 이상): 선순위 채권자에게 배당 대부분 소진"

    result.risk_factors.append(RiskFactor(
        name="선순위 비중",
        value=f"{ratio_pct:.1f}%",
        deduction=deduction,
        description=desc,
    ))


def _score_rir(result: ScoreResult, contract: ContractInput) -> None:
    """RIR(임대료 소득 대비 비율) 감점

    전세: 연임대료 = 보증금 × 전월세전환율
    월세: 연임대료 = 월세 × 12
    """
    if contract.annual_income <= 0:
        result.risk_factors.append(RiskFactor(
            name="RIR",
            value="계산불가 (연소득 미입력)",
            deduction=0,
            description="연소득을 입력해야 RIR을 계산할 수 있습니다.",
        ))
        return

    if contract.lease_type == LeaseType.JEONSE:
        annual_rent = contract.deposit * JEONSE_CONVERSION_RATE
        rent_label = f"전세 환산 연임대료 ({JEONSE_CONVERSION_RATE*100:.0f}% 적용)"
    else:
        annual_rent = contract.monthly_rent * 12
        rent_label = "연임대료 (월세×12)"

    rir = annual_rent / contract.annual_income
    result.rir = rir
    rir_pct = rir * 100

    if rir < 0.25:
        deduction = 0
        desc = f"RIR {rir_pct:.1f}% — 부담 낮음 (25% 미만) / {rent_label}: {annual_rent:,.0f}원"
    elif rir < 0.40:
        deduction = 10
        desc = f"RIR {rir_pct:.1f}% — 주의 (25~40%): 임대료 부담이 소득의 상당 비중 / {rent_label}: {annual_rent:,.0f}원"
    else:
        deduction = 20
        desc = f"RIR {rir_pct:.1f}% — 위험 (40% 이상): 임대료 부담 과중, 생계비 압박 우려 / {rent_label}: {annual_rent:,.0f}원"

    result.risk_factors.append(RiskFactor(
        name="RIR (임대료 소득 비율)",
        value=f"{rir_pct:.1f}%",
        deduction=deduction,
        description=desc,
    ))


def _score_auxiliary(
    result: ScoreResult,
    registry: RegistryData,
    building: BuildingData,
) -> None:
    """보조 감점 항목"""
    if registry.has_recent_ownership_transfer:
        result.risk_factors.append(RiskFactor(
            name="최근 소유권 이전",
            value="있음",
            deduction=5,
            description="최근 2년 이내 소유권 이전 이력이 있습니다. 갭투자 의심 또는 권리관계 변동 가능성이 있습니다.",
        ))

    if building.is_non_residential and not building.is_residential:
        result.risk_factors.append(RiskFactor(
            name="비주거용 건물",
            value=f"{building.main_use or '비주거'}",
            deduction=5,
            description="건축물대장상 비주거 용도입니다. 보증보험 가입이 제한될 수 있습니다.",
        ))


# ── 등급 산정 ───────────────────────────────────────────────────────

def _score_to_grade(score: float) -> RiskGrade:
    if score >= 80:
        return RiskGrade.SAFE
    elif score >= 60:
        return RiskGrade.CAUTION
    elif score >= 40:
        return RiskGrade.DANGER
    else:
        return RiskGrade.VERY_DANGEROUS


# ── 치명적 요소 등급 상한 ────────────────────────────────────────────

def _apply_fatal_ceiling(result: ScoreResult, registry: RegistryData, building: BuildingData) -> None:
    """치명적 요소가 있으면 등급 상한을 강제 적용한다.

    단순 감점이 아닌 등급 천장 방식을 사용하여
    다른 조건이 좋아도 치명 요소가 희석되지 않도록 한다.
    """
    ceiling = None
    ceiling_reasons = []

    if registry.has_seizure:
        result.risk_factors.append(RiskFactor(
            name="압류·경매개시",
            value="있음",
            deduction=0,
            description="압류·가압류·가처분·경매개시 등이 등기되어 있습니다. 다른 조건이 양호해도 거래를 피해야 합니다.",
            is_fatal=True,
            grade_ceiling=RiskGrade.VERY_DANGEROUS,
        ))
        ceiling = _harder_ceiling(ceiling, RiskGrade.VERY_DANGEROUS)
        ceiling_reasons.append("압류·경매개시 — 등급 상한: 매우 위험")

    if registry.has_trust:
        result.risk_factors.append(RiskFactor(
            name="신탁등기",
            value="있음",
            deduction=0,
            description="신탁등기가 설정되어 있습니다. 소유자가 임대 권한을 가지지 않을 수 있어 계약 자체가 무효가 될 위험이 있습니다.",
            is_fatal=True,
            grade_ceiling=RiskGrade.DANGER,
        ))
        ceiling = _harder_ceiling(ceiling, RiskGrade.DANGER)
        ceiling_reasons.append("신탁등기 — 등급 상한: 위험")

    if building.is_illegal_building:
        result.risk_factors.append(RiskFactor(
            name="위반건축물",
            value="있음",
            deduction=0,
            description="위반건축물로 등재되어 있습니다. 보증보험 가입이 거절될 가능성이 있습니다.",
            is_fatal=True,
            grade_ceiling=RiskGrade.DANGER,
        ))
        ceiling = _harder_ceiling(ceiling, RiskGrade.DANGER)
        ceiling_reasons.append("위반건축물 — 등급 상한: 위험")

    if ceiling is not None:
        # 현재 등급이 상한보다 '좋으면' 상한으로 강등
        if GRADE_ORDER[result.grade] < GRADE_ORDER[ceiling]:
            result.grade = ceiling
            result.grade_ceiling_applied = True
            result.grade_ceiling_reason = " / ".join(ceiling_reasons)


def _harder_ceiling(current, new_ceiling: RiskGrade):
    """더 나쁜(강한) 상한을 반환"""
    if current is None:
        return new_ceiling
    return new_ceiling if GRADE_ORDER[new_ceiling] > GRADE_ORDER[current] else current
