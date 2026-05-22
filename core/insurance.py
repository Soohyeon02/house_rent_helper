"""보증보험 추천 판정 모듈.

HUG·HF는 가부 판정, SGI는 단정하지 않고 대안 검토만 안내.

판정 흐름:
  HUG·HF: 한도식 + 결격 모두 검사 → 가입가능/어려움 + 사유 목록
  SGI: 권리침해 있으면 어려움 / HUG·HF 모두 결격 → 검토 권유 / 그 외 HUG·HF 우선 안내
"""

from models.data_models import (
    BuildingData, ContractInput, InsuranceJudgment, InsuranceResult,
    LeaseType, RegistryData,
)

# 한도 (원)
_HUG_LIMIT_METRO = 700_000_000     # HUG 수도권 7억
_HUG_LIMIT_OTHER = 500_000_000     # HUG 그 외 5억
_HF_LIMIT_METRO = 700_000_000      # HF 수도권 7억
_HF_LIMIT_OTHER = 500_000_000      # HF 지방 5억


def recommend_insurance(
    registry: RegistryData,
    building: BuildingData,
    contract: ContractInput,
    score_result=None,  # ScoreResult (선택적, 현재 미사용)
) -> InsuranceResult:
    """보증보험 3종에 대한 추천 판정을 수행한다."""
    house_price = building.published_price
    priority_debt = registry.priority_debt_total
    deposit = contract.deposit

    hug = _judge_hug(registry, building, contract, house_price, priority_debt, deposit)
    hf = _judge_hf(registry, building, contract, house_price, priority_debt, deposit)
    sgi = _judge_sgi(registry, hug, hf)

    summary = _build_summary(hug, hf, sgi)

    return InsuranceResult(hug=hug, hf=hf, sgi=sgi, summary=summary)


# ── HUG 판정 ────────────────────────────────────────────────────────

def _judge_hug(
    registry: RegistryData,
    building: BuildingData,
    contract: ContractInput,
    house_price: float,
    priority_debt: float,
    deposit: float,
) -> InsuranceJudgment:
    """HUG 전세보증금반환보증 판정"""
    reasons = []
    conditions = []

    # 결격 사유 체크
    if registry.has_seizure:
        reasons.append("압류·가압류·가처분·경매개시 등 권리침해 등기 존재")

    if not building.is_residential:
        reasons.append("건축물대장상 주거용 건물이 아님 (오피스텔은 주거용 표기 필수)")

    if contract.elapsed_ratio >= 0.5:
        pct = contract.elapsed_ratio * 100
        reasons.append(f"계약기간 1/2 이상 경과 ({pct:.0f}% 경과) — 신청 기한 초과")

    # 한도 체크
    limit = _HUG_LIMIT_METRO if contract.is_metropolitan else _HUG_LIMIT_OTHER
    limit_label = "수도권 7억" if contract.is_metropolitan else "비수도권 5억"

    if deposit > limit:
        over = deposit - limit
        reasons.append(f"보증금({_fmt_eok(deposit)})이 한도({limit_label})보다 {_fmt_eok(over)} 초과")

    # 한도식 체크: 보증금 ≤ 주택가격 × 90% − 선순위채권
    if house_price > 0:
        max_deposit = house_price * 0.9 - priority_debt
        if deposit > max_deposit:
            over = deposit - max_deposit
            reasons.append(
                f"한도식 초과: 보증금({_fmt_eok(deposit)}) > 주택가격×90%-선순위채권({_fmt_eok(max_deposit)}) — {_fmt_eok(over)} 초과"
            )
    else:
        conditions.append("공시가격 미확인 — 한도식 검토 불가 (공시가격 확인 필요)")

    eligible = len(reasons) == 0
    if eligible:
        conditions.append("신규 전세계약 일반 임차인 대상 1순위 추천 상품")
        conditions.append(f"한도: {limit_label}")

    return InsuranceJudgment(
        product_name="HUG 전세보증금반환보증",
        eligible=eligible,
        reasons=reasons,
        conditions=conditions,
    )


# ── HF 판정 ─────────────────────────────────────────────────────────

def _judge_hf(
    registry: RegistryData,
    building: BuildingData,
    contract: ContractInput,
    house_price: float,
    priority_debt: float,
    deposit: float,
) -> InsuranceJudgment:
    """HF 일반전세지킴보증 판정"""
    reasons = []
    conditions = []

    # 결격 사유 체크
    if registry.has_seizure or registry.has_trust:
        detail = []
        if registry.has_seizure:
            detail.append("압류·경매 등")
        if registry.has_trust:
            detail.append("신탁등기")
        reasons.append(f"권리침해 등기 존재: {', '.join(detail)}")

    if contract.contract_months < 12:
        reasons.append(f"계약기간 {contract.contract_months}개월 — 1년 미만 단기 계약 불가")

    # 한도 체크
    limit = _HF_LIMIT_METRO if contract.is_metropolitan else _HF_LIMIT_OTHER
    limit_label = "수도권 7억" if contract.is_metropolitan else "지방 5억"

    if deposit > limit:
        over = deposit - limit
        reasons.append(f"보증금({_fmt_eok(deposit)})이 한도({limit_label})보다 {_fmt_eok(over)} 초과")

    # 한도식 체크
    if house_price > 0:
        max_deposit = house_price * 0.9 - priority_debt
        if deposit > max_deposit:
            over = deposit - max_deposit
            reasons.append(
                f"한도식 초과: 보증금({_fmt_eok(deposit)}) > 주택가격×90%-선순위채권({_fmt_eok(max_deposit)}) — {_fmt_eok(over)} 초과"
            )

        # 선순위 비율 제한
        is_single = building.building_type == "단독·다가구"
        _check_hf_priority_ratio(
            reasons, house_price, priority_debt,
            registry.priority_mortgage_total, is_single,
        )
    else:
        conditions.append("공시가격 미확인 — 한도식 및 선순위 비율 검토 불가")

    eligible = len(reasons) == 0
    if eligible:
        conditions.append("전세자금대출 연계자 대상 추천 상품")
        conditions.append(f"한도: {limit_label}")

    return InsuranceJudgment(
        product_name="HF 일반전세지킴보증",
        eligible=eligible,
        reasons=reasons,
        conditions=conditions,
    )


def _check_hf_priority_ratio(
    reasons, house_price, priority_debt_total, priority_mortgage, is_single_house
):
    """HF 선순위 비율 제한 검사"""
    if house_price <= 0:
        return

    total_ratio = priority_debt_total / house_price
    mortgage_ratio = priority_mortgage / house_price

    if is_single_house:
        # 단독·다가구: 총액 80%, 근저당 60%
        if total_ratio > 0.80:
            reasons.append(
                f"단독·다가구 선순위 총액 비율 {total_ratio*100:.1f}% — 80% 초과 (HF 제한)"
            )
        if mortgage_ratio > 0.60:
            reasons.append(
                f"단독·다가구 근저당 비율 {mortgage_ratio*100:.1f}% — 60% 초과 (HF 제한)"
            )
    else:
        # 그 외: 총액 60%
        if total_ratio > 0.60:
            reasons.append(
                f"선순위 총액 비율 {total_ratio*100:.1f}% — 60% 초과 (HF 제한)"
            )


# ── SGI 판정 ─────────────────────────────────────────────────────────

def _judge_sgi(
    registry: RegistryData,
    hug: InsuranceJudgment,
    hf: InsuranceJudgment,
) -> InsuranceJudgment:
    """SGI 전세금보장신용보험 판정 (민간 보험 — 가부 단정 불가)"""
    reasons = []
    conditions = []

    has_rights_violation = registry.has_seizure or registry.has_trust

    if has_rights_violation:
        detail = []
        if registry.has_seizure:
            detail.append("압류·경매")
        if registry.has_trust:
            detail.append("신탁등기")
        reasons.append(f"권리침해 등기 존재({', '.join(detail)}) — 민간 보험도 가입 어려움")
        eligible = False
        conditions.append("심사 기준 비공개이므로 직접 문의 권장")
    elif not hug.eligible and not hf.eligible:
        eligible = False  # '어려움'은 아니지만 '검토 권유'
        conditions.append("HUG·HF 모두 가입 어려움 — SGI 전세금보장신용보험 검토 권유")
        conditions.append("아파트: 보증금 전액 / 그 외: 최대 10억 (상품별 상이)")
        conditions.append("심사 기준 비공개 — 가입 가능 여부는 직접 문의 필요")
        eligible = False  # eligible=False이지만 reasons가 없어서 '검토 권유' 표시
    else:
        eligible = False
        conditions.append("HUG·HF 우선 가입 검토 후 한도 초과 시 SGI 추가 검토")
        conditions.append("아파트: 보증금 전액 / 그 외: 최대 10억 (상품별 상이)")
        conditions.append("민간 보험으로 심사 기준 비공개 — 가부 단정 불가")

    return InsuranceJudgment(
        product_name="SGI 전세금보장신용보험",
        eligible=eligible,
        reasons=reasons,
        conditions=conditions,
    )


# ── 종합 요약 ─────────────────────────────────────────────────────────

def _build_summary(hug: InsuranceJudgment, hf: InsuranceJudgment, sgi: InsuranceJudgment) -> str:
    lines = []
    if hug.eligible:
        lines.append("HUG 전세보증금반환보증 가입 가능 → 우선 신청 권장")
    if hf.eligible:
        lines.append("HF 일반전세지킴보증 가입 가능 → 전세자금대출과 연계 시 유리")
    if not hug.eligible and not hf.eligible:
        lines.append("HUG·HF 모두 가입 어려움 → SGI 전세금보장신용보험 검토 필요")
    elif not hug.eligible:
        lines.append("HUG 가입 불가 → HF 또는 SGI 검토")
    elif not hf.eligible:
        lines.append("HF 가입 불가 → HUG 우선 이용")

    return " / ".join(lines) if lines else "보증보험 가입 여부를 개별 확인하세요."


# ── 금액 포맷 헬퍼 ───────────────────────────────────────────────────

def _fmt_eok(amount: float) -> str:
    """원 → 억/만 단위 표시"""
    if amount >= 1_0000_0000:
        eok = amount / 1_0000_0000
        return f"{eok:.1f}억원"
    elif amount >= 1_0000:
        man = amount / 1_0000
        return f"{man:.0f}만원"
    else:
        return f"{amount:,.0f}원"
