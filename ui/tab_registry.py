"""탭1 — 등기부등본 업로드 및 추출 결과"""

import os
import sys
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QTextEdit, QSizePolicy, QScrollArea,
    QDialog, QDialogButtonBox,
)
from PyQt5.QtCore import Qt, pyqtSignal

from models.data_models import RegistryData
from ui.styles import TEXT_PRI, TEXT_SEC, TEXT_DIM, ACCENT, BG_INPUT, BORDER, COLOR_SAFE
from ui.widgets import CardFrame, StatusBadge, LabelRow, CollapsibleSection
from ui.worker import PDFWorker


class TabRegistry(QWidget):
    """탭1: 등기부등본 PDF 업로드 + 추출 결과 편집"""

    data_ready = pyqtSignal(object)  # RegistryData 준비 완료 시그널

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

        # 스크롤 영역
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
        upload_card = CardFrame("등기부등본 PDF 업로드")
        layout.addWidget(upload_card)

        # 파일 선택 행
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

        # 상태 표시
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

        # 근저당 합계
        self._mortgage_edit = self._make_amount_edit()
        result_card.add_widget(LabelRow("선순위 근저당 합계", self._make_amount_row(self._mortgage_edit, "원")))

        # 임차보증금 합계
        self._lease_deposit_edit = self._make_amount_edit()
        result_card.add_widget(LabelRow("선순위 임차보증금", self._make_amount_row(self._lease_deposit_edit, "원")))

        # 배지 행
        badge_grid = QWidget()
        badge_grid.setAttribute(Qt.WA_TranslucentBackground)
        grid_layout = QVBoxLayout(badge_grid)
        grid_layout.setContentsMargins(0, 4, 0, 0)
        grid_layout.setSpacing(10)

        self._seizure_badge = StatusBadge()
        self._seizure_badge.set_unknown()
        grid_layout.addWidget(LabelRow("압류·경매개시", self._seizure_badge))

        self._trust_badge = StatusBadge()
        self._trust_badge.set_unknown()
        grid_layout.addWidget(LabelRow("신탁등기", self._trust_badge))

        self._transfer_badge = StatusBadge()
        self._transfer_badge.set_unknown()
        grid_layout.addWidget(LabelRow("최근 소유권 이전", self._transfer_badge))

        result_card.add_widget(badge_grid)

        # ── 파싱 노트 접힘 섹션 ──
        self._notes_section = CollapsibleSection("파싱 로그 (상세 보기)")
        layout.addWidget(self._notes_section)

        self._notes_text = QTextEdit()
        self._notes_text.setReadOnly(True)
        self._notes_text.setPlaceholderText("PDF 파싱 후 로그가 표시됩니다...")
        self._notes_text.setFixedHeight(120)
        self._notes_section.add_widget(self._notes_text)

        layout.addStretch()

    def _make_amount_edit(self) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText("0")
        edit.setAlignment(Qt.AlignRight)
        edit.textChanged.connect(self._on_manual_edit)
        return edit

    def _make_amount_row(self, edit: QLineEdit, unit: str) -> QWidget:
        w = QWidget()
        w.setAttribute(Qt.WA_TranslucentBackground)
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(edit, 1)
        u = QLabel(unit)
        u.setStyleSheet(f"color: {TEXT_SEC};")
        h.addWidget(u)
        return w

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "등기부등본 PDF 선택", "", "PDF 파일 (*.pdf)"
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

        self._worker = PDFWorker(path, "registry")
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(lambda msg: self._set_status(msg, ACCENT))
        self._worker.start()

    def _on_finished(self, registry_data: RegistryData):
        self.state.registry_data = registry_data
        self._update_display(registry_data)
        self._set_status("✓  추출 완료", COLOR_SAFE)
        self.data_ready.emit(registry_data)

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

    def _update_display(self, data: RegistryData):
        self._mortgage_edit.blockSignals(True)
        self._lease_deposit_edit.blockSignals(True)

        self._mortgage_edit.setText(f"{data.priority_mortgage_total:,.0f}")
        self._lease_deposit_edit.setText(f"{data.priority_lease_deposit_total:,.0f}")

        if data.has_seizure:
            self._seizure_badge.set_status(False, is_fatal=True, bad_label="있음")
        else:
            self._seizure_badge.set_status(True, ok_label="없음")

        if data.has_trust:
            self._trust_badge.set_status(False, is_fatal=True, bad_label="있음")
        else:
            self._trust_badge.set_status(True, ok_label="없음")

        if data.has_recent_ownership_transfer:
            self._transfer_badge.set_warning("있음 (주의)")
        else:
            self._transfer_badge.set_status(True, ok_label="없음")

        self._notes_text.setPlainText("\n".join(data.parse_notes))

        self._mortgage_edit.blockSignals(False)
        self._lease_deposit_edit.blockSignals(False)

    def _on_manual_edit(self):
        """수동 편집 시 state 업데이트"""
        if self.state.registry_data is None:
            self.state.registry_data = RegistryData()
        try:
            val = float(self._mortgage_edit.text().replace(",", "") or "0")
            self.state.registry_data.priority_mortgage_total = val
        except ValueError:
            pass
        try:
            val = float(self._lease_deposit_edit.text().replace(",", "") or "0")
            self.state.registry_data.priority_lease_deposit_total = val
        except ValueError:
            pass
        self.state.reset_results()

    def _set_status(self, msg: str, color: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
