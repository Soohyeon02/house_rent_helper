"""GUI 진입점

사용:
    pip install PyQt5 pdfplumber PyMuPDF
    python main_gui.py
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가 (패키지 임포트용)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# 고해상도 디스플레이 지원 — QApplication 생성 전에 설정해야 함
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from ui.app import MainWindow


def main():
    app = QApplication(sys.argv)

    # 기본 폰트
    font = QFont()
    font.setFamily("Apple SD Gothic Neo")
    font.setPointSize(13)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
