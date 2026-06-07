"""자동 라이브러리 설치 및 Tesseract OCR 설치 안내 모듈.

main_gui.py 최상단에서 import 후 check_and_install()을 호출하면
requirements.txt의 패키지를 자동으로 설치한다.
"""

import importlib
import os
import subprocess
import sys
import shutil
import platform


# {import_name: pip_install_name}
REQUIRED_PACKAGES = {
    "PyQt5": "PyQt5>=5.15.0",
    "pdfplumber": "pdfplumber>=0.7.0",
    "fitz": "PyMuPDF>=1.16.0",
    "pdfminer": "pdfminer.six>=20200517",
    "pytesseract": "pytesseract>=0.3.8",
    "PIL": "Pillow>=8.0.0",
}


def check_and_install() -> None:
    """누락된 패키지를 pip으로 자동 설치한다."""
    missing = []
    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return

    print(f"[auto_setup] 누락된 패키지 설치 중: {', '.join(missing)}")
    for pip_name in missing:
        print(f"  -> pip install {pip_name}")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pip_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            print(f"  -> 설치 완료: {pip_name}")
        except subprocess.CalledProcessError as e:
            print(f"  -> 설치 실패: {pip_name} (오류 코드 {e.returncode})")


def _find_tesseract_windows() -> str | None:
    """Windows 일반 설치 경로에서 tesseract.exe를 탐색한다.

    Returns:
        실행 파일 경로 문자열, 없으면 None.
    """
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Programs", "Tesseract-OCR", "tesseract.exe",
        ),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def get_tesseract_cmd() -> str | None:
    """pytesseract에 설정할 Tesseract 실행 파일 경로를 반환한다.

    우선순위: PATH 탐색 → Windows 공통 경로 탐색 → None

    Returns:
        실행 파일 경로 문자열, 또는 None(PATH에 있거나 찾지 못한 경우).
    """
    found = shutil.which("tesseract")
    if found:
        return found
    if platform.system() == "Windows":
        return _find_tesseract_windows()
    return None


def check_tesseract() -> str | None:
    """Tesseract 바이너리 존재 여부를 확인하고, 없으면 안내 메시지를 반환한다.

    Returns:
        바이너리가 있으면 None, 없으면 설치 안내 문자열.
    """
    if shutil.which("tesseract") is not None:
        return None

    # PATH에 없어도 Windows 공통 설치 경로에서 찾으면 설치된 것으로 간주
    if platform.system() == "Windows" and _find_tesseract_windows() is not None:
        return None

    os_name = platform.system()
    if os_name == "Windows":
        install_guide = (
            "Windows: UB-Mannheim Tesseract 설치 파일을 다운로드하세요.\n"
            "  https://github.com/UB-Mannheim/tesseract/wiki\n"
            "설치 시 'Korean' 언어팩을 체크해야 합니다."
        )
    elif os_name == "Darwin":
        install_guide = "macOS: brew install tesseract tesseract-lang"
    else:
        install_guide = "Linux: sudo apt-get install tesseract-ocr tesseract-ocr-kor"

    return (
        "Tesseract OCR 바이너리를 찾을 수 없습니다.\n"
        "이미지 기반 PDF의 텍스트 추출이 제한됩니다.\n\n"
        f"{install_guide}"
    )
