"""전세/월세 사기 방지 도우미 — CLI 테스트 진입점.

사용 예시:
  # PDF 없이 수동 값으로 테스트
  python main.py --income 50000000 --lease-type 전세 --deposit 300000000 --metro

  # PDF 파일 포함
  python main.py --registry 등기부등본.pdf --building 건축물대장.pdf \\
                 --income 50000000 --lease-type 전세 --deposit 300000000 --metro

  # 월세 예시
  python main.py --income 40000000 --lease-type 월세 --deposit 50000000 \\
                 --monthly-rent 800000 --contract-months 24 --metro
"""

import argparse
import sys

from models.data_models import ContractInput, LeaseType, RegistryData, BuildingData
from core.extractor import extract_text_from_pdf
from core.parser_registry import parse_registry
from core.parser_building import parse_building
from core.scorer import calculate_score
from core.insurance import recommend_insurance


_GRADE_COLOR = {
    "안전": "\033[92m",       # 초록
    "주의": "\033[93m",       # 노랑
    "위험": "\033[91m",       # 빨강
    "매우 위험": "\033[95m",  # 자주
}
_RESET = "\033[0m"


def main():
    args = _parse_args()

    print("\n" + "=" * 60)
    print("  전세/월세 사기 방지 분석 도우미")
    print("=" * 60)

    # ── PDF 파싱 ──────────────────────────────────────────────────
    registry = _load_registry(args.registry)
    building = _load_building(args.building)

    # ── 계약 입력 ─────────────────────────────────────────────────
    lease_type = LeaseType.JEONSE if args.lease_type == "전세" else LeaseType.MONTHLY
    contract = ContractInput(
        annual_income=args.income,
        lease_type=lease_type,
        deposit=args.deposit,
        monthly_rent=args.monthly_rent,
        contract_months=args.contract_months,
        elapsed_ratio=args.elapsed_ratio,
        is_metropolitan=args.metro,
    )

    # ── 점수 계산 ─────────────────────────────────────────────────
    score_result = calculate_score(registry, building, contract)

    # ── 보증보험 추천 ─────────────────────────────────────────────
    insurance_result = recommend_insurance(registry, building, contract, score_result)

    # ── 결과 출력 ─────────────────────────────────────────────────
    _print_registry_summary(registry)
    _print_building_summary(building)
    _print_score_result(score_result)
    _print_insurance_result(insurance_result)

    print("\n" + "=" * 60 + "\n")


# ── 파싱 헬퍼 ────────────────────────────────────────────────────────

def _load_registry(path: str) -> RegistryData:
    if not path:
        print("[등기부등본] PDF 미입력 — 기본값(0)으로 계산합니다.")
        return RegistryData()
    print(f"[등기부등본] 추출 중: {path}")
    try:
        text = extract_text_from_pdf(path)
        data = parse_registry(text)
        print(f"  → 근저당 합계: {data.priority_mortgage_total:,.0f}원")
        print(f"  → 임차보증금 합계: {data.priority_lease_deposit_total:,.0f}원")
        print(f"  → 압류·경매: {'있음' if data.has_seizure else '없음'}")
        print(f"  → 신탁등기: {'있음' if data.has_trust else '없음'}")
        print(f"  → 최근 소유권 이전: {'있음' if data.has_recent_ownership_transfer else '없음/미확인'}")
        return data
    except FileNotFoundError as e:
        print(f"  [오류] {e}")
        return RegistryData()


def _load_building(path: str) -> BuildingData:
    if not path:
        print("[건축물대장] PDF 미입력 — 기본값(0)으로 계산합니다.")
        return BuildingData()
    print(f"[건축물대장] 추출 중: {path}")
    try:
        text = extract_text_from_pdf(path)
        data = parse_building(text)
        print(f"  → 공시가격: {data.published_price:,.0f}원")
        print(f"  → 위반건축물: {'있음' if data.is_illegal_building else '없음'}")
        print(f"  → 주용도: {data.main_use or '미확인'}")
        print(f"  → 주거용: {'예' if data.is_residential else '아니오'}")
        return data
    except FileNotFoundError as e:
        print(f"  [오류] {e}")
        return BuildingData()


# ── 출력 함수들 ──────────────────────────────────────────────────────

def _print_registry_summary(registry: RegistryData):
    pass  # 이미 _load_registry에서 출력


def _print_building_summary(building: BuildingData):
    pass  # 이미 _load_building에서 출력


def _print_score_result(result):
    grade_str = result.grade.value
    color = _GRADE_COLOR.get(grade_str, "")

    print("\n" + "─" * 60)
    print("  위험도 분석 결과")
    print("─" * 60)
    print(f"  최종 점수: {result.final_score:.1f}점 / 100점")
    print(f"  위험 등급: {color}{grade_str}{_RESET}")

    if result.grade_ceiling_applied:
        print(f"  * 등급 상한 적용: {result.grade_ceiling_reason}")

    print(f"\n  [주요 지표]")
    if result.jeonse_rate > 0:
        print(f"  - 전세가율    : {result.jeonse_rate * 100:.1f}%")
    if result.priority_ratio > 0:
        print(f"  - 선순위 비중 : {result.priority_ratio * 100:.1f}%")
    if result.rir > 0:
        print(f"  - RIR         : {result.rir * 100:.1f}%")

    print(f"\n  [위험 요인 상세]")
    if not result.risk_factors:
        print("  위험 요인 없음")
    for i, factor in enumerate(result.risk_factors, 1):
        fatal_mark = " [치명]" if factor.is_fatal else ""
        deduction_str = f"(-{factor.deduction:.0f}점)" if factor.deduction > 0 else ""
        print(f"  {i}. {factor.name}{fatal_mark} {deduction_str}")
        print(f"     {factor.description}")


def _print_insurance_result(result):
    print("\n" + "─" * 60)
    print("  보증보험 추천 결과")
    print("─" * 60)

    for judgment in [result.hug, result.hf, result.sgi]:
        status = "가입 가능" if judgment.eligible else ("검토 권유" if not judgment.reasons else "가입 어려움")
        print(f"\n  [{judgment.product_name}] → {status}")
        for reason in judgment.reasons:
            print(f"    ✗ {reason}")
        for cond in judgment.conditions:
            print(f"    ℹ {cond}")

    print(f"\n  [종합 안내]")
    print(f"  {result.summary}")


# ── CLI 인자 파싱 ────────────────────────────────────────────────────

def _parse_args():
    parser = argparse.ArgumentParser(
        description="전세/월세 사기 방지 위험도 분석 도구"
    )
    parser.add_argument("--registry", type=str, default="", help="등기부등본 PDF 경로")
    parser.add_argument("--building", type=str, default="", help="건축물대장 PDF 경로")
    parser.add_argument("--income", type=float, required=True, help="연소득 (원)")
    parser.add_argument("--lease-type", choices=["전세", "월세"], required=True, help="임차 유형")
    parser.add_argument("--deposit", type=float, required=True, help="보증금 (원)")
    parser.add_argument("--monthly-rent", type=float, default=0.0, help="월세액 (원, 월세인 경우)")
    parser.add_argument("--contract-months", type=int, default=24, help="계약기간 (개월, 기본 24)")
    parser.add_argument("--elapsed-ratio", type=float, default=0.0, help="경과비율 0.0~1.0 (기본 0.0)")
    parser.add_argument("--metro", action="store_true", help="수도권 여부 (플래그)")

    # 수동 오버라이드 (PDF 없을 때 직접 값 입력)
    parser.add_argument("--mortgage", type=float, default=0.0, help="선순위 근저당 합계 (원, PDF 없을 때)")
    parser.add_argument("--lease-deposit", type=float, default=0.0, help="선순위 임차보증금 합계 (원)")
    parser.add_argument("--house-price", type=float, default=0.0, help="공시가격 (원, PDF 없을 때)")
    parser.add_argument("--seizure", action="store_true", help="압류·경매 있음 (플래그)")
    parser.add_argument("--trust", action="store_true", help="신탁등기 있음 (플래그)")
    parser.add_argument("--illegal-building", action="store_true", help="위반건축물 (플래그)")

    args = parser.parse_args()

    # 수동 오버라이드 적용 여부는 main()에서 처리
    return args


if __name__ == "__main__":
    # 수동 오버라이드 처리를 위해 재파싱
    args = _parse_args()

    # 수동 값이 있으면 PDF 파싱 결과에 덮어씀
    def _load_registry_with_override(path, args):
        data = _load_registry(path)
        if args.mortgage:
            data.priority_mortgage_total = args.mortgage
            print(f"  [오버라이드] 근저당: {args.mortgage:,.0f}원")
        if args.lease_deposit:
            data.priority_lease_deposit_total = args.lease_deposit
            print(f"  [오버라이드] 임차보증금: {args.lease_deposit:,.0f}원")
        if args.seizure:
            data.has_seizure = True
        if args.trust:
            data.has_trust = True
        return data

    def _load_building_with_override(path, args):
        data = _load_building(path)
        if args.house_price:
            data.published_price = args.house_price
            print(f"  [오버라이드] 공시가격: {args.house_price:,.0f}원")
        if args.illegal_building:
            data.is_illegal_building = True
        return data

    print("\n" + "=" * 60)
    print("  전세/월세 사기 방지 분석 도우미")
    print("=" * 60)

    registry = _load_registry_with_override(args.registry, args)
    building = _load_building_with_override(args.building, args)

    lease_type = LeaseType.JEONSE if args.lease_type == "전세" else LeaseType.MONTHLY
    contract = ContractInput(
        annual_income=args.income,
        lease_type=lease_type,
        deposit=args.deposit,
        monthly_rent=args.monthly_rent,
        contract_months=args.contract_months,
        elapsed_ratio=args.elapsed_ratio,
        is_metropolitan=args.metro,
    )

    score_result = calculate_score(registry, building, contract)
    insurance_result = recommend_insurance(registry, building, contract, score_result)

    _print_score_result(score_result)
    _print_insurance_result(insurance_result)

    print("\n" + "=" * 60 + "\n")
