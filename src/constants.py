from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
TEX_DIR = PROJECT_DIR / "tex"
MAIN_TEX_FILE = TEX_DIR / "main.tex"
SECTIONS = ["experience", "education", "projects"]
VCARD = DATA_DIR / 'KonstantinAlthaus.vcf'
TEMPLATES_DIR = PROJECT_DIR / "templates"
PERSONAL_INFO_TEMPLATE = TEMPLATES_DIR / "personal_info_template.tex"
PHOTO = DATA_DIR / "KonstantinAlthaus.jpeg"
LATEX_COMMANDS = {
    "projects": "cvproject",
    "experience": "cvevent",
    "education": "cvevent",
}
