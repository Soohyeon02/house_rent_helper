"""GUI 진입점

사용:
    python main_gui.py  # 필요한 패키지는 자동으로 설치됩니다
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가 (패키지 임포트용)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 필요 패키지 자동 설치 (다른 import보다 먼저 실행)
import auto_setup
auto_setup.check_and_install()

from PyQt5.QtWidgets import QApplication, QMessageBox
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

    # Tesseract OCR 설치 여부 확인 — 없으면 경고 다이얼로그 표시
    tesseract_warning = auto_setup.check_tesseract()
    if tesseract_warning:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Tesseract OCR 미설치")
        msg.setText(tesseract_warning)
        msg.exec_()

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
