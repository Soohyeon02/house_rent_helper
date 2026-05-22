"""PDF 텍스트 추출 진단 스크립트

사용법:
    python debug_pdf.py "파일경로.pdf"

각 추출 방법별 결과와 PDF 메타데이터를 출력해
어느 단계에서 실패하는지 정확히 파악할 수 있습니다.
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def hr(title=""):
    if title:
        print(f"\n{'─'*20} {title} {'─'*20}")
    else:
        print("─" * 60)


def preview(text: str, n: int = 120) -> str:
    """텍스트 앞 n자 미리보기"""
    if not text or not text.strip():
        return "(빈 문자열)"
    cleaned = text.strip().replace("\n", "↵")
    return cleaned[:n] + ("..." if len(cleaned) > n else "")


def diagnose(pdf_path: str):
    if not os.path.exists(pdf_path):
        print(f"[오류] 파일 없음: {pdf_path}")
        sys.exit(1)

    size_kb = os.path.getsize(pdf_path) / 1024
    print(f"\n{'='*60}")
    print(f"  PDF 진단 리포트")
    print(f"{'='*60}")
    print(f"파일: {os.path.basename(pdf_path)}")
    print(f"크기: {size_kb:.1f} KB")

    # ── fitz (PyMuPDF) 진단 ─────────────────────────────────────────
    hr("PyMuPDF(fitz) 진단")
    try:
        import fitz
        print(f"PyMuPDF 버전: {fitz.__version__}")

        doc = fitz.open(pdf_path)

        print(f"페이지 수   : {doc.page_count}")
        print(f"암호화 여부 : {doc.is_encrypted}")
        print(f"메타데이터  : {dict(list(doc.metadata.items())[:4])}")

        if doc.is_encrypted:
            print("[!] 암호화 PDF — 빈 암호로 인증 시도...")
            result = doc.authenticate("")
            print(f"    인증 결과: {'성공' if result else '실패'}")

        for page_num in range(min(doc.page_count, 3)):  # 최대 3페이지
            page = doc[page_num]
            hr(f"페이지 {page_num+1}")
            print(f"  크기    : {page.rect.width:.0f} x {page.rect.height:.0f} pt")
            print(f"  회전    : {page.rotation}°")

            # 이미지
            images = page.get_images()
            print(f"  이미지 수: {len(images)}")

            # 폰트
            fonts = page.get_fonts()
            if fonts:
                print(f"  폰트 ({len(fonts)}개):")
                for f in fonts[:5]:
                    # (xref, ext, type, basefont, name, encoding, referencer)
                    print(f"    - 타입:{f[2]}  이름:{f[3]}  인코딩:{f[5]}")
            else:
                print("  폰트: 없음")

            # ── 각 모드별 추출 ──
            modes = ["text", "blocks", "dict", "xml", "html", "rawdict", "json"]
            print(f"\n  [fitz 모드별 추출 결과]")
            for mode in modes:
                try:
                    if mode == "dict":
                        data = page.get_text("dict")
                        parts = []
                        for block in data.get("blocks", []):
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    s = span.get("text", "")
                                    if s.strip():
                                        parts.append(s)
                        t = " ".join(parts)
                    elif mode == "blocks":
                        blocks = page.get_text("blocks")
                        parts = [b[4] for b in blocks if isinstance(b[4], str)]
                        t = "\n".join(parts)
                    elif mode == "rawdict":
                        data = page.get_text("rawdict")
                        chars = []
                        for block in data.get("blocks", []):
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    for ch in span.get("chars", []):
                                        c = ch.get("c", "")
                                        if c:
                                            chars.append(c)
                        t = "".join(chars)
                    elif mode == "xml":
                        import xml.etree.ElementTree as ET
                        xml_str = page.get_text("xml")
                        try:
                            root = ET.fromstring(xml_str)
                            t = " ".join(root.itertext())
                        except Exception:
                            t = re.sub(r'<[^>]+>', ' ', xml_str)
                    elif mode == "html":
                        html_str = page.get_text("html")
                        t = re.sub(r'<[^>]+>', ' ', html_str)
                    elif mode == "json":
                        import json as json_mod
                        json_str = page.get_text("json")
                        data = json_mod.loads(json_str)
                        parts = []
                        for block in data.get("blocks", []):
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    s = span.get("text", "")
                                    if s.strip():
                                        parts.append(s)
                        t = " ".join(parts)
                    else:
                        t = page.get_text(mode)

                    char_count = len(t.strip())
                    status = f"{char_count}자" if char_count else "0자 (실패)"
                    print(f"    {mode:10s}: {status}")
                    if char_count > 0:
                        print(f"               미리보기: {preview(t, 100)}")

                except Exception as e:
                    print(f"    {mode:10s}: 오류 — {e}")

        doc.close()

    except ImportError:
        print("  [!] PyMuPDF 미설치 (pip install PyMuPDF)")
    except Exception as e:
        print(f"  [오류] {e}")

    # ── pdfplumber 진단 ──────────────────────────────────────────────
    hr("pdfplumber 진단")
    try:
        import pdfplumber
        print(f"pdfplumber 버전: {pdfplumber.__version__}")

        with pdfplumber.open(pdf_path) as pdf:
            print(f"페이지 수: {len(pdf.pages)}")

            for page_num, page in enumerate(pdf.pages[:3]):
                hr(f"페이지 {page_num+1}")
                print(f"  크기: {page.width:.0f} x {page.height:.0f} pt")

                methods = {
                    "extract_text()": lambda p: p.extract_text(),
                    "extract_text(x_tol=10)": lambda p: p.extract_text(x_tolerance=10, y_tolerance=10),
                    "extract_words()": lambda p: " ".join(w["text"] for w in p.extract_words()) if p.extract_words() else "",
                    "chars 직접": lambda p: "".join(c["text"] for c in p.chars) if p.chars else "",
                }
                print(f"\n  [pdfplumber 방식별 결과]")
                for name, fn in methods.items():
                    try:
                        t = fn(page) or ""
                        char_count = len(t.strip())
                        status = f"{char_count}자" if char_count else "0자 (실패)"
                        print(f"    {name:28s}: {status}")
                        if char_count > 0:
                            print(f"    {'':28s}  미리보기: {preview(t, 100)}")
                    except Exception as e:
                        print(f"    {name:28s}: 오류 — {e}")

    except ImportError:
        print("  [!] pdfplumber 미설치 (pip install pdfplumber)")
    except Exception as e:
        print(f"  [오류] {e}")

    # ── 최종 판정 ────────────────────────────────────────────────────
    hr("판정")
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            print("→ [암호화 PDF] 텍스트 추출 불가. DRM 해제 필요.")
        else:
            total_text = "".join(doc[i].get_text() for i in range(doc.page_count))
            images_total = sum(len(doc[i].get_images()) for i in range(doc.page_count))
            if len(total_text.strip()) > 100:
                print(f"→ [텍스트 추출 가능] fitz text 모드로 {len(total_text.strip())}자 추출됨.")
            elif images_total > 0:
                print(f"→ [이미지 PDF 의심] 텍스트 거의 없고 이미지 {images_total}개 감지. OCR 필요 가능성.")
            else:
                print("→ [미상] 텍스트도 이미지도 감지되지 않음. 폰트 인코딩 문제 또는 XObject form 가능성.")
        doc.close()
    except Exception as e:
        print(f"→ [오류] {e}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python debug_pdf.py <PDF파일경로>")
        sys.exit(1)
    diagnose(sys.argv[1])
