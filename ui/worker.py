"""QThread 기반 백그라운드 PDF 파싱 워커"""

from PyQt5.QtCore import QThread, pyqtSignal

from core.extractor import extract_text_from_pdf
from core.parser_registry import parse_registry
from core.parser_building import parse_building


class PDFWorker(QThread):
    """PDF 텍스트 추출 + 파싱을 백그라운드에서 실행.

    Signals:
        finished(object): 파싱 완료 — RegistryData 또는 BuildingData
        error(str): 오류 메시지
        progress(str): 진행 상태 메시지
    """

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, pdf_path: str, doc_type: str, parent=None):
        """
        Args:
            pdf_path: PDF 파일 경로
            doc_type: "registry" (등기부등본) | "building" (건축물대장)
        """
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.doc_type = doc_type

    def run(self):
        try:
            self.progress.emit("PDF 텍스트 추출 중...")
            text = extract_text_from_pdf(self.pdf_path)

            if not text.strip():
                self.error.emit(
                    "텍스트 추출 실패: 빈 결과\n"
                    "해결 방법: 터미널에서 아래 명령을 실행해 원인을 확인하세요.\n"
                    "  python debug_pdf.py \"파일경로.pdf\""
                )
                return

            if text.startswith("[암호화 PDF]"):
                self.error.emit(text)
                return

            if text.startswith("[텍스트 추출 실패]"):
                self.error.emit(
                    f"{text}\n"
                    "원인 확인: python debug_pdf.py \"파일경로.pdf\""
                )
                return

            self.progress.emit("항목 파싱 중...")
            if self.doc_type == "registry":
                result = parse_registry(text)
            else:
                result = parse_building(text)

            self.finished.emit(result)

        except FileNotFoundError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"처리 중 오류 발생: {e}")
