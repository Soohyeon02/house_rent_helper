"""탭4 — 위험도 결과 및 보증보험 추천"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt

from models.data_models import ScoreResult, InsuranceResult, RiskGrade
from ui.styles import (
    TEXT_PRI, TEXT_SEC, TEXT_DIM, ACCENT,
    BG_CARD, BG_INPUT, BORDER, BORDER_LT,
    COLOR_SAFE, COLOR_CAUTION, COLOR_DANGER, COLOR_FATAL,
    GRADE_COLORS,
)
from ui.widgets import ScoreGauge, MetricCard, CardFrame


class TabResult(QWidget):
    """탭4: 점수 게이지 + 위험요인 + 보증보험 추천"""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(0, 0, 8, 20)
        self._main_layout.setSpacing(16)
        scroll.setWidget(container)
        root.addWidget(scroll)

        self._show_placeholder()

    def _show_placeholder(self):
        self._clear_layout()
        placeholder = QLabel("탭3에서 정보를 입력하고 '분석 시작'을 클릭하면\n결과가 여기에 표시됩니다.")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px;")
        self._main_layout.addStretch()
        self._main_layout.addWidget(placeholder)
        self._main_layout.addStretch()

    def refresh(self):
        """state에서 결과를 읽어 화면 전체 갱신"""
        if not self.state.result_ready:
            self._show_placeholder()
            return

        self._clear_layout()
        score = self.state.score_result
        insurance = self.state.insurance_result

        self._build_score_section(score)
        self._build_metrics_section(score)
        self._build_factors_section(score)
        if insurance:
            self._build_insurance_section(insurance)

    # ── 점수 섹션 ────────────────────────────────────────────────────

    def _build_score_section(self, score: ScoreResult):
        card = CardFrame()
        inner = QHBoxLayout()
        inner.setSpacing(24)

        # 왼쪽: 게이지
        self._gauge = ScoreGauge()
        self._gauge.setFixedWidth(320)
        inner.addWidget(self._gauge)

        # 오른쪽: 등급 배지 + 설명
        right = QVBoxLayout()
        right.setSpacing(10)
        right.addStretch()

        grade_val = score.grade.value
        fg, bg = GRADE_COLORS.get(grade_val, (ACCENT, BG_INPUT))

        grade_badge = QLabel(f"  {grade_val}  ")
        grade_badge.setAlignment(Qt.AlignCenter)
        grade_badge.setFixedHeight(40)
        grade_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 2px solid {fg};
                border-radius: 20px;
                font-size: 18px;
                font-weight: 700;
                padding: 0 20px;
            }}
        """)
        right.addWidget(grade_badge)

        if score.grade_ceiling_applied:
            ceiling_lbl = QLabel(f"⚠  등급 상한 적용\n{score.grade_ceiling_reason}")
            ceiling_lbl.setStyleSheet(f"color: {COLOR_FATAL}; font-size: 12px;")
            ceiling_lbl.setWordWrap(True)
            right.addWidget(ceiling_lbl)

        score_detail = QLabel(
            f"기본 점수: {score.base_score:.0f}점\n"
            f"감점 합계: -{score.base_score - score.final_score:.0f}점\n"
            f"최종 점수: {score.final_score:.0f}점"
        )
        score_detail.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; line-height: 1.6;")
        right.addWidget(score_detail)
        right.addStretch()

        inner.addLayout(right, 1)
        card.add_layout(inner)
        self._main_layout.addWidget(card)

        # 게이지 애니메이션 실행
        self._gauge.set_score(score.final_score, grade_val)

    # ── 지표 섹션 ────────────────────────────────────────────────────

    def _build_metrics_section(self, score: ScoreResult):
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)

        jeonse_card = MetricCard(
            "전세가율",
            [(0.70, COLOR_CAUTION), (0.80, COLOR_DANGER), (1.00, COLOR_FATAL)],
        )
        priority_card = MetricCard(
            "선순위 비중",
            [(0.30, COLOR_CAUTION), (0.50, COLOR_DANGER)],
        )
        rir_card = MetricCard(
            "RIR (임대료 소득 비율)",
            [(0.25, COLOR_CAUTION), (0.40, COLOR_DANGER)],
        )

        if score.jeonse_rate > 0:
            jeonse_card.set_value(score.jeonse_rate)
        else:
            jeonse_card.set_empty()

        if score.priority_ratio > 0:
            priority_card.set_value(score.priority_ratio)
        else:
            priority_card.set_empty()

        if score.rir > 0:
            rir_card.set_value(score.rir)
        else:
            rir_card.set_empty()

        for mc in [jeonse_card, priority_card, rir_card]:
            mc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            metrics_row.addWidget(mc)

        wrapper = QWidget()
        wrapper.setAttribute(Qt.WA_TranslucentBackground)
        wrapper.setLayout(metrics_row)
        self._main_layout.addWidget(wrapper)

    # ── 위험요인 섹션 ────────────────────────────────────────────────

    def _build_factors_section(self, score: ScoreResult):
        card = CardFrame("위험 요인 상세")
        self._main_layout.addWidget(card)

        if not score.risk_factors:
            lbl = QLabel("특이 위험 요인 없음")
            lbl.setStyleSheet(f"color: {COLOR_SAFE};")
            card.add_widget(lbl)
            return

        for factor in score.risk_factors:
            row = _FactorRow(factor)
            card.add_widget(row)

    # ── 보증보험 섹션 ────────────────────────────────────────────────

    def _build_insurance_section(self, insurance: InsuranceResult):
        header = QLabel("보증보험 추천")
        header.setStyleSheet(f"color: {TEXT_PRI}; font-size: 14px; font-weight: 700; margin-top: 4px;")
        self._main_layout.addWidget(header)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        for judgment in [insurance.hug, insurance.hf, insurance.sgi]:
            ic = _InsuranceCard(judgment)
            ic.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            cards_row.addWidget(ic)

        wrapper = QWidget()
        wrapper.setAttribute(Qt.WA_TranslucentBackground)
        wrapper.setLayout(cards_row)
        self._main_layout.addWidget(wrapper)

        # 종합 안내
        if insurance.summary:
            summary_card = CardFrame()
            summary_lbl = QLabel(f"💡  {insurance.summary}")
            summary_lbl.setWordWrap(True)
            summary_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 13px;")
            summary_card.add_widget(summary_lbl)
            self._main_layout.addWidget(summary_card)

    def _clear_layout(self):
        while self._main_layout.count():
            item = self._main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# ── 위험요인 행 위젯 ─────────────────────────────────────────────────

class _FactorRow(QWidget):
    def __init__(self, factor, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 4)
        v.setSpacing(4)

        # 헤더 행
        h = QHBoxLayout()
        h.setSpacing(8)

        if factor.is_fatal:
            icon = "⚠"
            color = COLOR_FATAL
        elif factor.deduction >= 20:
            icon = "✗"
            color = COLOR_DANGER
        elif factor.deduction >= 10:
            icon = "!"
            color = COLOR_CAUTION
        else:
            icon = "·"
            color = TEXT_SEC

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 700;")
        icon_lbl.setFixedWidth(16)
        h.addWidget(icon_lbl)

        name_lbl = QLabel(factor.name)
        name_lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 600;")
        h.addWidget(name_lbl)

        if factor.is_fatal:
            badge = QLabel("  치명  ")
            badge.setStyleSheet(f"""
                QLabel {{
                    background-color: #1e0a3c;
                    color: {COLOR_FATAL};
                    border: 1px solid {COLOR_FATAL}50;
                    border-radius: 4px;
                    padding: 1px 6px;
                    font-size: 11px;
                }}
            """)
            h.addWidget(badge)
        elif factor.deduction > 0:
            deduct_lbl = QLabel(f"  -{factor.deduction:.0f}점  ")
            deduct_lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: #2d0f0e;
                    color: {COLOR_DANGER};
                    border: 1px solid {COLOR_DANGER}40;
                    border-radius: 4px;
                    padding: 1px 6px;
                    font-size: 11px;
                }}
            """)
            h.addWidget(deduct_lbl)

        value_lbl = QLabel(f"({factor.value})")
        value_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        h.addWidget(value_lbl)
        h.addStretch()
        v.addLayout(h)

        # 설명
        desc = QLabel(factor.description)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; margin-left: 24px;")
        v.addWidget(desc)

        # 구분선
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        v.addWidget(sep)


# ── 보증보험 카드 ─────────────────────────────────────────────────────

class _InsuranceCard(QWidget):
    def __init__(self, judgment, parent=None):
        super().__init__(parent)

        # 상태 결정
        if judgment.eligible:
            status_text = "가입 가능"
            status_color = COLOR_SAFE
            card_border = COLOR_SAFE
            card_bg = "#0a1f14"
        elif judgment.reasons:
            status_text = "가입 어려움"
            status_color = COLOR_DANGER
            card_border = COLOR_DANGER
            card_bg = "#1f0a0a"
        else:
            status_text = "검토 권유"
            status_color = COLOR_CAUTION
            card_border = COLOR_CAUTION
            card_bg = "#1f1500"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {card_bg};
                border: 1px solid {card_border}60;
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # 상품명
        name_lbl = QLabel(judgment.product_name)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 12px; font-weight: 700;")
        layout.addWidget(name_lbl)

        # 상태 배지
        status_badge = QLabel(f"  {status_text}  ")
        status_badge.setAlignment(Qt.AlignCenter)
        status_badge.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                color: {status_color};
                border: 1px solid {status_color};
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: 700;
            }}
        """)
        layout.addWidget(status_badge)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {card_border}40;")
        layout.addWidget(sep)

        # 사유/조건 목록
        for reason in judgment.reasons:
            row = QLabel(f"✗  {reason}")
            row.setWordWrap(True)
            row.setStyleSheet(f"color: {COLOR_DANGER}; font-size: 11px;")
            layout.addWidget(row)

        for cond in judgment.conditions:
            row = QLabel(f"ℹ  {cond}")
            row.setWordWrap(True)
            row.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px;")
            layout.addWidget(row)

        layout.addStretch()
