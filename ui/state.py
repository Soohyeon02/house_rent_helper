"""탭 간 공유 애플리케이션 상태"""

from models.data_models import (
    RegistryData, BuildingData, ContractInput, ScoreResult, InsuranceResult,
)


class AppState:
    """모든 탭이 공유하는 단일 상태 객체.
    app.py에서 생성 후 각 탭에 참조 전달.
    """

    def __init__(self):
        self.registry_data: RegistryData = None
        self.building_data: BuildingData = None
        self.contract_input: ContractInput = None
        self.score_result: ScoreResult = None
        self.insurance_result: InsuranceResult = None

    @property
    def registry_ready(self) -> bool:
        return self.registry_data is not None

    @property
    def building_ready(self) -> bool:
        return self.building_data is not None

    @property
    def result_ready(self) -> bool:
        return self.score_result is not None

    def reset_results(self):
        """입력이 변경되면 결과 초기화"""
        self.score_result = None
        self.insurance_result = None
