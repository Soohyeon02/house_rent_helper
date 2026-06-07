"""재사용 가능한 커스텀 위젯 모음"""

import math
from PyQt5.QtWidgets import (
    QFrame, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSizePolicy,
)
from PyQt5.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPainterPath, QFontMetrics

from ui.styles import (
    BG_CARD, BG_INPUT, BORDER, BORDER_LT,
    TEXT_PRI, TEXT_SEC, TEXT_DIM, ACCENT,
    COLOR_SAFE, COLOR_CAUTION, COLOR_DANGER, COLOR_FATAL,
    GRADE_COLORS,
)


# ── CardFrame ────────────────────────────────────────────────────────

class CardFrame(QFrame):
    """둥근 테두리 카드 프레임. 타이틀 + 내용 레이아웃."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._setup_style()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(12)

        if title:
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 600;")
            outer.addWidget(title_lbl)

            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet(f"color: {BORDER};")
            outer.addWidget(sep)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        outer.addLayout(self.content_layout)

    def _setup_style(self):
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)


# ── StatusBadge ──────────────────────────────────────────────────────

class StatusBadge(QLabel):
    """pill 형태 상태 배지"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(24)
        self.setMinimumWidth(60)
        self.set_unknown()

    def set_status(self, is_ok: bool, ok_label: str = "없음", bad_label: str = "있음",
                   is_fatal: bool = False):
        if is_ok:
            color = COLOR_SAFE
            bg = "#0d2818"
            self.setText(f"  ✓  {ok_label}  ")
        elif is_fatal:
            color = COLOR_FATAL
            bg = "#1e0a3c"
            self.setText(f"  ⚠  {bad_label}  ")
        else:
            color = COLOR_DANGER
            bg = "#2d0f0e"
            self.setText(f"  ✗  {bad_label}  ")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {color};
                border: 1px solid {color}40;
                border-radius: 12px;
                padding: 2px 6px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)

    def set_warning(self, label: str = "주의"):
        self.setText(f"  !  {label}  ")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #2b1d00;
                color: {COLOR_CAUTION};
                border: 1px solid {COLOR_CAUTION}40;
                border-radius: 12px;
                padding: 2px 6px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)

    def set_unknown(self):
        self.setText("  —  미확인  ")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_INPUT};
                color: {TEXT_DIM};
                border: 1px solid {BORDER};
                border-radius: 12px;
                padding: 2px 6px;
                font-size: 12px;
            }}
        """)


# ── LabelRow ─────────────────────────────────────────────────────────

class LabelRow(QWidget):
    """라벨 + 값(위젯) 한 줄 레이아웃"""

    def __init__(self, label: str, value_widget: QWidget, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFixedWidth(160)
        lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px;")
        layout.addWidget(lbl)
        layout.addWidget(value_widget, 1)


# ── ScoreGauge ───────────────────────────────────────────────────────

class ScoreGauge(QWidget):
    """QPainter로 그린 반원 게이지. 점수 및 등급 표시."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._score = 0.0
        self._display_score = 0.0   # 애니메이션용
        self._grade = "—"
        self._color = COLOR_SAFE
        self.setMinimumSize(320, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 애니메이션
        self._anim = QPropertyAnimation(self, b"display_score")
        self._anim.setDuration(800)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    # pyqtProperty: 애니메이션 대상
    def _get_display_score(self):
        return self._display_score

    def _set_display_score(self, val):
        self._display_score = val
        self.update()

    display_score = pyqtProperty(float, _get_display_score, _set_display_score)

    def set_score(self, score: float, grade_value: str):
        self._score = score
        self._grade = grade_value
        colors = {
            "안전": COLOR_SAFE,
            "주의": COLOR_CAUTION,
            "위험": COLOR_DANGER,
            "매우 위험": COLOR_FATAL,
        }
        self._color = colors.get(grade_value, ACCENT)

        self._anim.stop()
        self._anim.setStartValue(self._display_score)
        self._anim.setEndValue(score)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 게이지 영역: 중앙 정렬 원
        radius = min(w // 2 - 20, h - 40)
        cx = w // 2
        cy = h - 50

        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        track_width = 16
        pen = QPen()
        pen.setWidth(track_width)
        pen.setCapStyle(Qt.RoundCap)

        # 배경 트랙 (반원: 180° ~ 0°, 즉 startAngle=0°, span=180°)
        pen.setColor(QColor(BORDER))
        painter.setPen(pen)
        painter.drawArc(rect, 0 * 16, 180 * 16)

        # 점수 트랙
        ratio = min(self._display_score / 100.0, 1.0)
        span = int(ratio * 180 * 16)
        if span > 0:
            pen.setColor(QColor(self._color))
            painter.setPen(pen)
            painter.drawArc(rect, 0 * 16, span * 16)

        # 점수 숫자 (중앙 하단)
        score_font = QFont()
        score_font.setPointSize(40)
        score_font.setBold(True)
        painter.setFont(score_font)
        painter.setPen(QColor(TEXT_PRI))
        score_text = f"{self._display_score:.0f}"
        fm = QFontMetrics(score_font)
        tw = fm.horizontalAdvance(score_text)
        painter.drawText(cx - tw // 2, cy - 10, score_text)

        # "점" 단위
        unit_font = QFont()
        unit_font.setPointSize(14)
        painter.setFont(unit_font)
        painter.setPen(QColor(TEXT_SEC))
        painter.drawText(cx + tw // 2 + 4, cy - 20, "점")

        # 등급 텍스트
        grade_font = QFont()
        grade_font.setPointSize(15)
        grade_font.setBold(True)
        painter.setFont(grade_font)
        painter.setPen(QColor(self._color))
        gfm = QFontMetrics(grade_font)
        gw = gfm.horizontalAdvance(self._grade)
        painter.drawText(cx - gw // 2, cy + 28, self._grade)

        # 0점·100점 레이블
        label_font = QFont()
        label_font.setPointSize(10)
        painter.setFont(label_font)
        painter.setPen(QColor(TEXT_DIM))
        painter.drawText(cx - radius - 10, cy + 16, "0")
        painter.drawText(cx + radius - 8, cy + 16, "100")

        painter.end()


# ── MetricCard ───────────────────────────────────────────────────────

class MetricCard(QWidget):
    """지표 이름 + 퍼센트 값 + 컬러 프로그레스바가 담긴 작은 카드"""

    def __init__(self, title: str, thresholds: list, parent=None):
        """
        thresholds: [(value, color), ...] 오름차순 (예: [(0.70, CAUTION), (0.80, DANGER)])
        """
        super().__init__(parent)
        self._thresholds = thresholds
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(160)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(6)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px;")
        self._layout.addWidget(self._title_lbl)

        self._value_lbl = QLabel("—")
        self._value_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 22px; font-weight: 700;")
        self._layout.addWidget(self._value_lbl)

        self._bar = _MiniBar()
        self._layout.addWidget(self._bar)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)

    def set_value(self, ratio: float):
        """ratio: 0.0 ~ 1.0 (소수)"""
        pct = ratio * 100
        color = COLOR_SAFE
        for threshold, col in self._thresholds:
            if ratio >= threshold:
                color = col
        self._value_lbl.setText(f"{pct:.1f}%")
        self._value_lbl.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 700;")
        self._bar.set_value(ratio, color)

    def set_empty(self):
        self._value_lbl.setText("—")
        self._value_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 22px; font-weight: 700;")
        self._bar.set_value(0, BORDER)


class _MiniBar(QWidget):
    """얇은 컬러 프로그레스바"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ratio = 0.0
        self._color = BORDER
        self.setFixedHeight(6)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_value(self, ratio: float, color: str):
        self._ratio = min(max(ratio, 0.0), 1.0)
        self._color = color
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # 배경
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BORDER))
        p.drawRoundedRect(0, 0, w, h, 3, 3)
        # 값
        fill_w = int(w * self._ratio)
        if fill_w > 0:
            p.setBrush(QColor(self._color))
            p.drawRoundedRect(0, 0, fill_w, h, 3, 3)
        p.end()


# ── CollapsibleSection ───────────────────────────────────────────────

class CollapsibleSection(QWidget):
    """클릭으로 내용을 접고 펼치는 섹션"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 헤더 버튼
        self._btn = QPushButton(f"▶  {title}")
        self._btn.setCheckable(True)
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_INPUT};
                color: {TEXT_SEC};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
                font-size: 12px;
            }}
            QPushButton:checked {{
                color: {TEXT_PRI};
                border-color: {BORDER_LT};
            }}
        """)
        self._btn.toggled.connect(self._on_toggle)
        outer.addWidget(self._btn)

        self._title = title

        # 내용 영역
        self._content = QWidget()
        self._content.setVisible(False)
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 4, 0, 0)
        self.inner_layout = content_layout
        outer.addWidget(self._content)

    def _on_toggle(self, checked: bool):
        self._content.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self._btn.setText(f"{arrow}  {self._title}")

    def add_widget(self, w):
        self.inner_layout.addWidget(w)
