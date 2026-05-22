"""탭3 — 소득·계약 정보 입력"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QRadioButton, QCheckBox, QSlider, QSpinBox,
    QScrollArea, QButtonGroup, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal

from models.data_models import ContractInput, LeaseType
from ui.styles import (
    TEXT_PRI, TEXT_SEC, TEXT_DIM, ACCENT, BG_CARD, BORDER,
    COLOR_SAFE, COLOR_CAUTION,
)
from ui.widgets import CardFrame


class TabContract(QWidget):
    """탭3: 소득·계약 입력 폼"""

    analysis_requested = pyqtSignal()   # 분석 시작 버튼 클릭 시그널

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # 상단: PDF 준비 상태 배너
        self._status_banner = _StatusBanner()
        root.addWidget(self._status_banner)

        # 스크롤
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(16)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        # ── 임차 정보 카드 ──
        lease_card = CardFrame("임차 정보")
        layout.addWidget(lease_card)

        # 임차 유형 라디오
        type_row = QHBoxLayout()
        self._jeonse_radio = QRadioButton("전세")
        self._monthly_radio = QRadioButton("월세")
        self._jeonse_radio.setChecked(True)
        self._jeonse_radio.toggled.connect(self._on_lease_type_changed)
        type_row.addWidget(self._jeonse_radio)
        type_row.addWidget(self._monthly_radio)
        type_row.addStretch()
        lease_card.add_widget(self._make_row("임차 유형", type_row))

        # 보증금
        self._deposit_edit = self._make_money_edit()
        lease_card.add_widget(self._make_row("보증금", self._make_money_row(self._deposit_edit)))

        # 월세액 (월세 선택 시만)
        self._monthly_edit = self._make_money_edit()
        self._monthly_row_widget = self._make_row("월세액", self._make_money_row(self._monthly_edit))
        self._monthly_row_widget.setVisible(False)
        lease_card.add_widget(self._monthly_row_widget)

        # 수도권 토글
        self._metro_check = QCheckBox("수도권 (서울·경기·인천)")
        self._metro_check.setChecked(True)
        self._metro_check.setStyleSheet(f"color: {TEXT_PRI};")
        lease_card.add_widget(self._make_row("지역", self._metro_check))

        # ── 소득 및 계약 기간 카드 ──
        income_card = CardFrame("소득 및 계약 기간")
        layout.addWidget(income_card)

        # 연소득
        self._income_edit = self._make_money_edit()
        income_card.add_widget(self._make_row("연소득", self._make_money_row(self._income_edit)))

        # 계약기간 (슬라이더 + 스핀박스)
        income_card.add_widget(self._make_row("계약기간", self._make_duration_row()))

        # 경과비율 (슬라이더)
        income_card.add_widget(self._make_row("경과 비율", self._make_elapsed_row()))

        layout.addStretch()

        # ── 분석 시작 버튼 ──
        btn_container = QWidget()
        btn_container.setAttribute(Qt.WA_TranslucentBackground)
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 8, 0, 0)

        self._analyze_btn = QPushButton("  분석 시작  →")
        self._analyze_btn.setObjectName("primary")
        self._analyze_btn.setFixedHeight(48)
        self._analyze_btn.setMinimumWidth(200)
        self._analyze_btn.setCursor(Qt.PointingHandCursor)
        self._analyze_btn.clicked.connect(self._on_analyze)
        btn_layout.addStretch()
        btn_layout.addWidget(self._analyze_btn)
        root.addWidget(btn_container)

    # ── 위젯 팩토리 ──────────────────────────────────────────────────

    def _make_row(self, label: str, content) -> QWidget:
        w = QWidget()
        w.setAttribute(Qt.WA_TranslucentBackground)
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)
        lbl = QLabel(label)
        lbl.setFixedWidth(110)
        lbl.setStyleSheet(f"color: {TEXT_SEC};")
        h.addWidget(lbl)
        if isinstance(content, QWidget):
            h.addWidget(content, 1)
        elif isinstance(content, QHBoxLayout):
            h.addLayout(content, 1)
        return w

    def _make_money_edit(self) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText("0")
        edit.setAlignment(Qt.AlignRight)
        edit.setFixedHeight(36)
        return edit

    def _make_money_row(self, edit: QLineEdit) -> QWidget:
        w = QWidget()
        w.setAttribute(Qt.WA_TranslucentBackground)
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(edit, 1)
        unit = QLabel("원")
        unit.setStyleSheet(f"color: {TEXT_SEC};")
        h.addWidget(unit)
        return w

    def _make_duration_row(self) -> QWidget:
        w = QWidget()
        w.setAttribute(Qt.WA_TranslucentBackground)
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        self._duration_slider = QSlider(Qt.Horizontal)
        self._duration_slider.setRange(6, 60)
        self._duration_slider.setValue(24)
        self._duration_slider.setTickInterval(6)

        self._duration_spin = QSpinBox()
        self._duration_spin.setRange(6, 60)
        self._duration_spin.setValue(24)
        self._duration_spin.setFixedWidth(60)
        self._duration_spin.setFixedHeight(36)

        self._duration_slider.valueChanged.connect(self._duration_spin.setValue)
        self._duration_spin.valueChanged.connect(self._duration_slider.setValue)

        h.addWidget(self._duration_slider, 1)
        h.addWidget(self._duration_spin)
        unit = QLabel("개월")
        unit.setStyleSheet(f"color: {TEXT_SEC};")
        h.addWidget(unit)
        return w

    def _make_elapsed_row(self) -> QWidget:
        w = QWidget()
        w.setAttribute(Qt.WA_TranslucentBackground)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        h = QHBoxLayout()
        self._elapsed_slider = QSlider(Qt.Horizontal)
        self._elapsed_slider.setRange(0, 100)
        self._elapsed_slider.setValue(0)
        self._elapsed_slider.valueChanged.connect(self._on_elapsed_changed)
        h.addWidget(self._elapsed_slider, 1)

        self._elapsed_lbl = QLabel("0%")
        self._elapsed_lbl.setFixedWidth(40)
        self._elapsed_lbl.setAlignment(Qt.AlignRight)
        self._elapsed_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: 600;")
        h.addWidget(self._elapsed_lbl)
        v.addLayout(h)

        hint = QLabel("보증보험 신청 시점의 계약 경과 비율 (50% 이상이면 HUG 신청 불가)")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        hint.setWordWrap(True)
        v.addWidget(hint)
        return w

    def _on_elapsed_changed(self, val: int):
        self._elapsed_lbl.setText(f"{val}%")
        color = COLOR_CAUTION if val >= 50 else ACCENT
        self._elapsed_lbl.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _on_lease_type_changed(self, checked: bool):
        is_jeonse = self._jeonse_radio.isChecked()
        self._monthly_row_widget.setVisible(not is_jeonse)

    def update_pdf_status(self):
        """탭3 상단 배너 업데이트 (탭1/탭2 완료 상태 반영)"""
        self._status_banner.update_status(
            self.state.registry_ready,
            self.state.building_ready,
        )

    def _on_analyze(self):
        contract = self._build_contract()
        if contract is None:
            return
        self.state.contract_input = contract
        self.analysis_requested.emit()

    def _build_contract(self):
        try:
            deposit = float(self._deposit_edit.text().replace(",", "") or "0")
            income = float(self._income_edit.text().replace(",", "") or "0")
            monthly = float(self._monthly_edit.text().replace(",", "") or "0")
        except ValueError:
            self._show_error("금액은 숫자로 입력해주세요.")
            return None

        if deposit <= 0:
            self._show_error("보증금을 입력해주세요.")
            return None
        if income <= 0:
            self._show_error("연소득을 입력해주세요.")
            return None

        lease_type = LeaseType.JEONSE if self._jeonse_radio.isChecked() else LeaseType.MONTHLY

        return ContractInput(
            annual_income=income,
            lease_type=lease_type,
            deposit=deposit,
            monthly_rent=monthly,
            contract_months=self._duration_spin.value(),
            elapsed_ratio=self._elapsed_slider.value() / 100.0,
            is_metropolitan=self._metro_check.isChecked(),
        )

    def _show_error(self, msg: str):
        from PyQt5.QtWidgets import QMessageBox
        mb = QMessageBox(self)
        mb.setWindowTitle("입력 오류")
        mb.setText(msg)
        mb.setIcon(QMessageBox.Warning)
        mb.exec_()


class _StatusBanner(QWidget):
    """탭1/탭2 준비 상태 배너"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(16)

        self._registry_lbl = self._make_chip("등기부등본", False)
        self._building_lbl = self._make_chip("건축물대장", False)
        hint = QLabel("PDF 없이도 분석 가능합니다 (추출값 0으로 계산)")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")

        h.addWidget(self._registry_lbl)
        h.addWidget(self._building_lbl)
        h.addWidget(hint)
        h.addStretch()

    def _make_chip(self, label: str, ready: bool) -> QLabel:
        lbl = QLabel()
        self._apply_chip_style(lbl, label, ready)
        return lbl

    def _apply_chip_style(self, lbl: QLabel, label: str, ready: bool):
        if ready:
            lbl.setText(f"  ✓  {label}  ")
            lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: #0d2818;
                    color: {COLOR_SAFE};
                    border: 1px solid {COLOR_SAFE}40;
                    border-radius: 12px;
                    padding: 4px 8px;
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        else:
            lbl.setText(f"  ○  {label}  ")
            lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: {TEXT_DIM};
                    border: 1px solid {BORDER};
                    border-radius: 12px;
                    padding: 4px 8px;
                    font-size: 12px;
                }}
            """)

    def update_status(self, registry_ready: bool, building_ready: bool):
        self._apply_chip_style(self._registry_lbl, "등기부등본", registry_ready)
        self._apply_chip_style(self._building_lbl, "건축물대장", building_ready)
