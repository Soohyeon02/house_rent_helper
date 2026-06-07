"""PDF 텍스트 추출 모듈.

pdfplumber / PyMuPDF 각각 다중 모드를 시도하고 가장 긴 결과를 반환한다.
정부24 등 특수 인코딩 PDF도 최대한 추출 시도한다.
"""

import re
from pathlib import Path


def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF 파일에서 전체 텍스트를 추출한다.

    pdfplumber 다중 모드 → PyMuPDF 다중 모드 순으로 시도하고
    더 많은 텍스트를 얻은 결과를 반환한다.

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        추출된 텍스트 문자열

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    # 암호화 여부 먼저 확인
    enc_msg = _check_encryption(pdf_path)
    if enc_msg:
        return enc_msg

    plumber_text = _extract_with_pdfplumber(pdf_path)
    mupdf_text   = _extract_with_pymupdf(pdf_path)
    miner_text   = _extract_with_pdfminer(pdf_path)   # 정부24 CIDFont 대응

    # 세 결과 중 가장 긴 텍스트 선택
    text = max([plumber_text, mupdf_text, miner_text], key=len)

    # 이미지 PDF일 경우 OCR 폴백 (정부24 문서출력 등)
    if not text.strip():
        text = _extract_with_ocr(pdf_path)

    if not text.strip():
        import platform as _platform
        _os = _platform.system()
        if _os == "Windows":
            _ocr_guide = (
                "  https://github.com/UB-Mannheim/tesseract/wiki 에서 설치 파일 다운로드\n"
                "  (설치 시 'Korean' 언어팩 체크 필수)\n"
                "  pip install pytesseract Pillow"
            )
        elif _os == "Darwin":
            _ocr_guide = (
                "  brew install tesseract tesseract-lang\n"
                "  pip install pytesseract Pillow"
            )
        else:
            _ocr_guide = (
                "  sudo apt-get install tesseract-ocr tesseract-ocr-kor\n"
                "  pip install pytesseract Pillow"
            )
        return (
            "[텍스트 추출 실패] 스캔된 이미지 PDF입니다.\n"
            "OCR을 사용하려면 다음을 설치하세요:\n"
            f"{_ocr_guide}"
        )

    return text


def _check_encryption(pdf_path: str) -> str:
    """암호화된 PDF이면 안내 메시지 반환. 정상이면 빈 문자열."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            # 빈 암호로 해제 시도 (일부 정부 PDF는 빈 암호로 잠김)
            if not doc.authenticate(""):
                doc.close()
                return "[암호화 PDF] 문서가 암호로 보호되어 있어 텍스트 추출이 불가합니다."
        doc.close()
    except Exception:
        pass
    return ""


def _extract_with_pdfplumber(pdf_path: str) -> str:
    """pdfplumber로 텍스트 추출. 3가지 방법을 시도해 가장 긴 결과 반환."""
    try:
        import pdfplumber
    except ImportError:
        return ""

    try:
        best = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = _plumber_extract_page(page)
                if len(page_text) > len(best):
                    best = page_text
                # 모든 페이지 텍스트 누적
            # 전체 문서 텍스트 수집
            all_pages = []
            for page in pdf.pages:
                all_pages.append(_plumber_extract_page(page))
            return "\n".join(all_pages)
    except Exception:
        return ""


def _plumber_extract_page(page) -> str:
    """단일 페이지에서 pdfplumber 3가지 방식으로 추출해 가장 긴 결과 반환."""
    candidates = []

    # 방법 1: 기본 extract_text
    try:
        t = page.extract_text()
        if t:
            candidates.append(t)
    except Exception:
        pass

    # 방법 2: 단어 단위 추출 (좌표 기반 — 회전/레이아웃 이슈 우회)
    try:
        words = page.extract_words()
        if words:
            t = " ".join(w["text"] for w in words)
            candidates.append(t)
    except Exception:
        pass

    # 방법 3: 허용 오차를 높인 extract_text (회전·간격 문제 완화)
    try:
        t = page.extract_text(x_tolerance=10, y_tolerance=10)
        if t:
            candidates.append(t)
    except Exception:
        pass

    return max(candidates, key=len) if candidates else ""


def _extract_with_pdfminer(pdf_path: str) -> str:
    """pdfminer.six로 텍스트 추출.

    정부24 등 CIDFont + ToUnicode 비표준 방식의 한국 정부 PDF에서
    pdfplumber / PyMuPDF가 실패할 때 pdfminer.six가 CMap을 직접 파싱해
    한글 텍스트를 추출할 수 있다.
    """
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        return ""

    try:
        text = extract_text(pdf_path) or ""
        return text
    except Exception:
        return ""


def _extract_with_ocr(pdf_path: str) -> str:
    """이미지 PDF에서 Tesseract OCR로 한글 텍스트 추출.

    pytesseract + Pillow + PyMuPDF가 모두 설치되어 있어야 한다.
    시스템에 Tesseract와 kor 언어팩이 설치되어 있어야 한다:
        brew install tesseract tesseract-lang
        pip install pytesseract Pillow
    """
    try:
        import io
        import fitz
        from PIL import Image
        import pytesseract
    except ImportError:
        return ""

    # Windows PATH 미등록 환경 대응: 공통 설치 경로 직접 지정
    try:
        from auto_setup import get_tesseract_cmd
        _cmd = get_tesseract_cmd()
        if _cmd:
            pytesseract.pytesseract.tesseract_cmd = _cmd
    except Exception:
        pass

    try:
        doc = fitz.open(pdf_path)
        pages = []
        for page in doc:
            # 300 DPI로 렌더링 (72pt 기준)
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            t = pytesseract.image_to_string(img, lang="kor+eng")
            pages.append(t)
        doc.close()
        return "\n\n".join(pages)
    except Exception:
        return ""


def _extract_with_pymupdf(pdf_path: str) -> str:
    """PyMuPDF(fitz)로 텍스트 추출. 3가지 모드를 시도해 가장 긴 결과 반환."""
    try:
        import fitz
    except ImportError:
        return ""

    try:
        all_pages = []
        doc = fitz.open(pdf_path)
        for page in doc:
            page_text = _fitz_extract_page(page)
            all_pages.append(page_text)
        doc.close()
        return "\n".join(all_pages)
    except Exception:
        return ""


def _fitz_extract_page(page) -> str:
    """단일 페이지에서 fitz 6가지 모드로 추출해 가장 긴 결과 반환.

    정부24 등 특수 인코딩 PDF를 위해 xml/html/rawdict 모드를 추가했다.
    """
    candidates = []

    # 모드 1: 기본 text
    try:
        t = page.get_text("text")
        if t.strip():
            candidates.append(t)
    except Exception:
        pass

    # 모드 2: blocks — 회전된 텍스트 블록도 읽힘
    try:
        blocks = page.get_text("blocks")
        parts = [b[4] for b in blocks if isinstance(b[4], str)]
        t = "\n".join(parts)
        if t.strip():
            candidates.append(t)
    except Exception:
        pass

    # 모드 3: dict — span 단위 추출 (폰트 인코딩 문제 우회)
    try:
        data = page.get_text("dict")
        parts = []
        for block in data.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    s = span.get("text", "")
                    if s.strip():
                        parts.append(s)
        t = " ".join(parts)
        if t.strip():
            candidates.append(t)
    except Exception:
        pass

    # 모드 4: xml — XML 파싱 후 텍스트 노드 수집 (정부24 PDF에서 효과적일 수 있음)
    try:
        import xml.etree.ElementTree as ET
        xml_str = page.get_text("xml")
        root = ET.fromstring(xml_str)
        t = " ".join(root.itertext()).strip()
        if t:
            candidates.append(t)
    except Exception:
        pass

    # 모드 5: html — HTML에서 태그 제거 후 텍스트 수집
    try:
        html_str = page.get_text("html")
        t = re.sub(r'<[^>]+>', ' ', html_str)
        t = re.sub(r'\s+', ' ', t).strip()
        if t:
            candidates.append(t)
    except Exception:
        pass

    # 모드 6: rawdict — char 단위 직접 수집 (ToUnicode 없는 폰트도 일부 처리)
    try:
        import json as _json
        data = page.get_text("rawdict")
        chars = []
        for block in data.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    for ch in span.get("chars", []):
                        c = ch.get("c", "")
                        if c and c.strip():
                            chars.append(c)
        t = "".join(chars)
        if t.strip():
            candidates.append(t)
    except Exception:
        pass

    return max(candidates, key=len) if candidates else ""
