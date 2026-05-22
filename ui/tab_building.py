"""탭2 — 건축물대장 업로드 및 추출 결과"""

import os
import sys
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QTextEdit, QSizePolicy, QScrollArea,
    QDialog, QDialogButtonBox,
)
from PyQt5.QtCore import Qt, pyqtSignal

from models.data_models import BuildingData
from ui.styles import TEXT_PRI, TEXT_SEC, TEXT_DIM, ACCENT, COLOR_SAFE
from ui.widgets import CardFrame, StatusBadge, LabelRow, CollapsibleSection
from ui.worker import PDFWorker


class TabBuilding(QWidget):
    """탭2: 건축물대장 PDF 업로드 + 추출 결과 편집"""

    data_ready = pyqtSignal(object)  # BuildingData 준비 완료 시그널

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._worker = None
        self._current_path = ""
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(16)
        scroll.setWidget(container)
        root.addWidget(scroll)

        # ── PDF 업로드 카드 ──
        upload_card = CardFrame("건축물대장 PDF 업로드")
        layout.addWidget(upload_card)

        file_row = QHBoxLayout()
        self._file_btn = QPushButton("  📂  파일 선택")
        self._file_btn.setFixedHeight(40)
        self._file_btn.setCursor(Qt.PointingHandCursor)
        self._file_btn.clicked.connect(self._browse_file)
        file_row.addWidget(self._file_btn)

        self._file_lbl = QLabel("파일을 선택해주세요")
        self._file_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self._file_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        file_row.addWidget(self._file_lbl, 1)
        upload_card.add_layout(file_row)

        self._status_lbl = QLabel("대기 중")
        self._status_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        upload_card.add_widget(self._status_lbl)

        self._diag_btn = QPushButton("🔍 진단 실행")
        self._diag_btn.setFixedHeight(32)
        self._diag_btn.setCursor(Qt.PointingHandCursor)
        self._diag_btn.setStyleSheet("font-size: 12px;")
        self._diag_btn.clicked.connect(self._run_diagnostics)
        self._diag_btn.setVisible(False)
        upload_card.add_widget(self._diag_btn)

        # ── 추출 결과 카드 ──
        result_card = CardFrame("추출 결과  (직접 수정 가능)")
        layout.addWidget(result_card)

        # 공시가격
        self._price_edit = QLineEdit()
        self._price_edit.setPlaceholderText("0  (미감지 시 직접 입력 필수)")
        self._price_edit.setAlignment(Qt.AlignRight)
        self._price_edit.textChanged.connect(self._on_manual_edit)

        price_row = QWidget()
        price_row.setAttribute(Qt.WA_TranslucentBackground)
        ph = QHBoxLayout(price_row)
        ph.setContentsMargins(0, 0, 0, 0)
        ph.addWidget(self._price_edit, 1)
        ph.addWidget(self._make_unit("원"))
        result_card.add_widget(LabelRow("공시가격", price_row))

        # 주용도
        self._use_lbl = QLabel("—")
        self._use_lbl.setStyleSheet(f"color: {TEXT_SEC};")
        result_card.add_widget(LabelRow("주용도", self._use_lbl))

        # 배지
        badge_area = QWidget()
        badge_area.setAttribute(Qt.WA_TranslucentBackground)
        bv = QVBoxLayout(badge_area)
        bv.setContentsMargins(0, 4, 0, 0)
        bv.setSpacing(10)

        self._illegal_badge = StatusBadge()
        self._illegal_badge.set_unknown()
        bv.addWidget(LabelRow("위반건축물", self._illegal_badge))

        self._residential_badge = StatusBadge()
        self._residential_badge.set_unknown()
        bv.addWidget(LabelRow("주거용 여부", self._residential_badge))

        result_card.add_widget(badge_area)

        # ── 공시가격 미입력 경고 ──
        self._price_warn = QLabel("⚠  공시가격이 없으면 전세가율·선순위 비중 계산이 불가합니다. 직접 입력해주세요.")
        self._price_warn.setStyleSheet("color: #d29922; font-size: 12px;")
        self._price_warn.setWordWrap(True)
        self._price_warn.setVisible(False)
        layout.addWidget(self._price_warn)

        # ── 파싱 노트 ──
        self._notes_section = CollapsibleSection("파싱 로그 (상세 보기)")
        layout.addWidget(self._notes_section)

        self._notes_text = QTextEdit()
        self._notes_text.setReadOnly(True)
        self._notes_text.setPlaceholderText("PDF 파싱 후 로그가 표시됩니다...")
        self._notes_text.setFixedHeight(120)
        self._notes_section.add_widget(self._notes_text)

        layout.addStretch()

    def _make_unit(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {TEXT_SEC};")
        return lbl

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "건축물대장 PDF 선택", "", "PDF 파일 (*.pdf)"
        )
        if path:
            self._start_extraction(path)

    def _start_extraction(self, path: str):
        self._current_path = path
        self._diag_btn.setVisible(False)
        filename = os.path.basename(path)
        self._file_lbl.setText(filename)
        self._file_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px;")
        self._set_status("추출 중...", ACCENT)

        if self._worker and self._worker.isRunning():
            self._worker.terminate()

        self._worker = PDFWorker(path, "building")
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(lambda msg: self._set_status(msg, ACCENT))
        self._worker.start()

    def _on_finished(self, building_data: BuildingData):
        self.state.building_data = building_data
        self._update_display(building_data)
        self._set_status("✓  추출 완료", COLOR_SAFE)
        self.data_ready.emit(building_data)

    def _on_error(self, msg: str):
        first_line = msg.split("\n")[0]
        self._set_status(f"✗  오류: {first_line}", "#f85149")
        self._diag_btn.setVisible(True)

    def _run_diagnostics(self):
        if not self._current_path:
            return
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        debug_script = os.path.join(project_root, "debug_pdf.py")
        result = subprocess.run(
            [sys.executable, debug_script, self._current_path],
            capture_output=True, text=True, cwd=project_root,
        )
        output = result.stdout + (result.stderr or "")

        dlg = QDialog(self)
        dlg.setWindowTitle("PDF 진단 결과")
        dlg.resize(700, 500)
        dlg_layout = QVBoxLayout(dlg)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(output or "(출력 없음)")
        text_edit.setStyleSheet("font-family: monospace; font-size: 12px;")
        dlg_layout.addWidget(text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.reject)
        dlg_layout.addWidget(buttons)

        dlg.exec_()

    def _update_display(self, data: BuildingData):
        self._price_edit.blockSignals(True)

        if data.published_price > 0:
            self._price_edit.setText(f"{data.published_price:,.0f}")
            self._price_warn.setVisible(False)
        else:
            self._price_edit.clear()
            self._price_warn.setVisible(True)

        self._use_lbl.setText(data.main_use or "미확인")

        self._illegal_badge.set_status(
            not data.is_illegal_building,
            ok_label="없음",
            bad_label="있음",
            is_fatal=True,
        )

        if data.is_residential:
            self._residential_badge.set_status(True, ok_label="주거용")
        elif data.is_non_residential:
            self._residential_badge.set_status(False, bad_label="비주거")
        else:
            self._residential_badge.set_unknown()

        self._notes_text.setPlainText("\n".join(data.parse_notes))
        self._price_edit.blockSignals(False)

    def _on_manual_edit(self):
        if self.state.building_data is None:
            self.state.building_data = BuildingData()
        try:
            val = float(self._price_edit.text().replace(",", "") or "0")
            self.state.building_data.published_price = val
            self._price_warn.setVisible(val == 0)
        except ValueError:
            pass
        self.state.reset_results()

    def _set_status(self, msg: str, color: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
