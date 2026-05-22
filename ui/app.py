"""메인 윈도우 — QMainWindow + QTabWidget"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QStatusBar,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from models.data_models import RegistryData, BuildingData
from core.scorer import calculate_score
from core.insurance import recommend_insurance
from ui.state import AppState
from ui.styles import APP_STYLE, BG_DEEP, BG_CARD, BORDER, TEXT_PRI, TEXT_SEC, ACCENT
from ui.tab_registry import TabRegistry
from ui.tab_building import TabBuilding
from ui.tab_contract import TabContract
from ui.tab_result import TabResult


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        self._setup_window()
        self._setup_ui()
        self._connect_signals()

    def _setup_window(self):
        self.setWindowTitle("전세/월세 사기 방지 도우미")
        self.setMinimumSize(960, 680)
        self.resize(1100, 760)
        self.setStyleSheet(APP_STYLE)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 헤더 ──
        header = self._build_header()
        root.addWidget(header)

        # ── 탭 위젯 ──
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(False)
        root.addWidget(self._tabs, 1)

        self._tab_registry = TabRegistry(self.state)
        self._tab_building = TabBuilding(self.state)
        self._tab_contract = TabContract(self.state)
        self._tab_result = TabResult(self.state)

        self._tabs.addTab(self._tab_registry, "  📋  등기부등본  ")
        self._tabs.addTab(self._tab_building, "  🏠  건축물대장  ")
        self._tabs.addTab(self._tab_contract, "  📝  소득·계약  ")
        self._tabs.addTab(self._tab_result,   "  📊  분석 결과  ")

        # ── 상태바 ──
        self._statusbar = QStatusBar()
        self._statusbar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {BG_CARD};
                color: {TEXT_SEC};
                border-top: 1px solid {BORDER};
                font-size: 12px;
                padding: 4px 16px;
            }}
        """)
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("PDF를 업로드하거나 탭3에서 직접 정보를 입력하세요.")

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_CARD};
                border-bottom: 1px solid {BORDER};
            }}
        """)
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 0, 20, 0)

        title = QLabel("🏡  전세·월세 사기 방지 도우미")
        title.setStyleSheet(f"""
            QLabel {{
                color: {TEXT_PRI};
                font-size: 16px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
        """)
        h.addWidget(title)
        h.addStretch()

        subtitle = QLabel("등기부등본·건축물대장 기반 위험도 분석")
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: {TEXT_SEC};
                font-size: 12px;
                background: transparent;
                border: none;
            }}
        """)
        h.addWidget(subtitle)
        return header

    def _connect_signals(self):
        # PDF 완료 → 탭3 배너 업데이트
        self._tab_registry.data_ready.connect(self._on_registry_ready)
        self._tab_building.data_ready.connect(self._on_building_ready)

        # 분석 시작
        self._tab_contract.analysis_requested.connect(self._run_analysis)

    def _on_registry_ready(self, data):
        self._statusbar.showMessage("등기부등본 추출 완료 — 건축물대장을 업로드하거나 탭3으로 이동하세요.")
        self._tab_contract.update_pdf_status()

    def _on_building_ready(self, data):
        self._statusbar.showMessage("건축물대장 추출 완료 — 탭3에서 계약 정보를 입력하세요.")
        self._tab_contract.update_pdf_status()

    def _run_analysis(self):
        """calculate_score + recommend_insurance 실행 후 탭4로 이동"""
        registry = self.state.registry_data or RegistryData()
        building = self.state.building_data or BuildingData()
        contract = self.state.contract_input

        if contract is None:
            return

        self._statusbar.showMessage("분석 중...")
        try:
            self.state.score_result = calculate_score(registry, building, contract)
            self.state.insurance_result = recommend_insurance(registry, building, contract)
            self._tab_result.refresh()
            self._tabs.setCurrentWidget(self._tab_result)
            self._statusbar.showMessage(
                f"분석 완료 — 등급: {self.state.score_result.grade.value}  "
                f"({self.state.score_result.final_score:.0f}점)"
            )
        except Exception as e:
            self._statusbar.showMessage(f"분석 오류: {e}")
