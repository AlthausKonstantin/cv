from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
TEX_DIR = PROJECT_DIR / "tex"
MAIN_TEX_FILE = TEX_DIR / "main.tex"
SECTIONS = ["experience", "education", "projects"]
LATEX_COMMANDS = {
    "projects": "cvproject",
    "experience": "cvevent",
    "education": "cvevent",
}
