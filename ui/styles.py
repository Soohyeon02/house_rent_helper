"""다크 테마 색상 팔레트 및 QSS 스타일시트"""

# ── 색상 팔레트 ──────────────────────────────────────────────────────
BG_DEEP    = "#0d1117"   # 앱 전체 배경
BG_CARD    = "#161b22"   # 카드/패널 배경
BG_INPUT   = "#21262d"   # 입력 필드 배경
BG_HOVER   = "#2d333b"   # 호버 상태
BORDER     = "#30363d"   # 테두리
BORDER_LT  = "#444c56"   # 밝은 테두리
ACCENT     = "#58a6ff"   # 강조 (파란계열)
ACCENT_DIM = "#1f6feb"   # 버튼 호버

TEXT_PRI   = "#e6edf3"   # 주 텍스트
TEXT_SEC   = "#8b949e"   # 보조 텍스트
TEXT_DIM   = "#484f58"   # 비활성 텍스트

# 등급 색상
COLOR_SAFE      = "#3fb950"   # 안전 (초록)
COLOR_SAFE_BG   = "#0d2818"
COLOR_CAUTION   = "#d29922"   # 주의 (노랑)
COLOR_CAUTION_BG= "#2b1d00"
COLOR_DANGER    = "#f85149"   # 위험 (빨강)
COLOR_DANGER_BG = "#2d0f0e"
COLOR_FATAL     = "#bc8cff"   # 매우위험 (자주)
COLOR_FATAL_BG  = "#1e0a3c"

GRADE_COLORS = {
    "안전":     (COLOR_SAFE,    COLOR_SAFE_BG),
    "주의":     (COLOR_CAUTION, COLOR_CAUTION_BG),
    "위험":     (COLOR_DANGER,  COLOR_DANGER_BG),
    "매우 위험": (COLOR_FATAL,   COLOR_FATAL_BG),
}


def get_grade_color(grade_value: str) -> str:
    """등급 문자열에서 전경색 반환"""
    return GRADE_COLORS.get(grade_value, (ACCENT, BG_CARD))[0]


APP_STYLE = f"""
/* ── 전체 기본 ── */
QMainWindow, QDialog {{
    background-color: {BG_DEEP};
}}
QWidget {{
    background-color: {BG_DEEP};
    color: {TEXT_PRI};
    font-family: "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif;
    font-size: 13px;
}}

/* ── 탭 위젯 ── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background-color: {BG_DEEP};
    margin-top: -1px;
}}
QTabBar {{
    background-color: transparent;
}}
QTabBar::tab {{
    background-color: {BG_INPUT};
    color: {TEXT_SEC};
    border: 1px solid {BORDER};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 10px 24px;
    margin-right: 3px;
    font-size: 13px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background-color: {BG_HOVER};
    color: {TEXT_PRI};
}}

/* ── 버튼 ── */
QPushButton {{
    background-color: {BG_INPUT};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER_LT};
}}
QPushButton:pressed {{
    background-color: {BG_DEEP};
}}
QPushButton#primary {{
    background-color: {ACCENT};
    color: #ffffff;
    border: none;
    font-weight: 600;
    font-size: 14px;
    padding: 12px 32px;
    border-radius: 8px;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT_DIM};
}}
QPushButton#primary:pressed {{
    background-color: #1158c7;
}}

/* ── 입력 필드 ── */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {ACCENT_DIM};
}}
QLineEdit:focus, QSpinBox:focus {{
    border-color: {ACCENT};
    outline: none;
}}
QLineEdit:disabled, QSpinBox:disabled {{
    color: {TEXT_DIM};
    background-color: {BG_DEEP};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 0;
    border: none;
}}

/* ── 슬라이더 ── */
QSlider::groove:horizontal {{
    height: 4px;
    background-color: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background-color: {ACCENT};
    border: 2px solid {BG_CARD};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background-color: {ACCENT};
    border-radius: 2px;
}}

/* ── 라디오 버튼, 체크박스 ── */
QRadioButton, QCheckBox {{
    color: {TEXT_PRI};
    spacing: 8px;
}}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {BORDER_LT};
    border-radius: 8px;
    background-color: {BG_INPUT};
}}
QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox::indicator {{
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* ── 스크롤바 ── */
QScrollBar:vertical {{
    background-color: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER_LT};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_SEC};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    height: 6px;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER_LT};
    border-radius: 3px;
}}

/* ── 구분선 ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {BORDER};
}}

/* ── 텍스트 에디터 (파싱 노트) ── */
QTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_SEC};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
    font-family: "SF Mono", "Consolas", monospace;
}}

/* ── 툴팁 ── */
QToolTip {{
    background-color: {BG_HOVER};
    color: {TEXT_PRI};
    border: 1px solid {BORDER_LT};
    border-radius: 4px;
    padding: 4px 8px;
}}

/* ── 라벨 ── */
QLabel {{
    background-color: transparent;
}}
"""
