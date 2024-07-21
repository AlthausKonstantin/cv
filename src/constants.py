from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
TEX_DIR = PROJECT_DIR / "tex"
TEMPLATES_DIR = PROJECT_DIR / "templates"

MAIN_TEX_FILE = TEX_DIR / "main.tex"
TAGS_TEX_FILE = TEX_DIR / "tags.tex"
PERSONAL_INFO_TEX_FILE = TEX_DIR / "personal_info.tex"
BIBLIOGRAPHY_TEX_FILE = TEX_DIR / "bibliography.tex"

VCARD = DATA_DIR / "KonstantinAlthaus.vcf"
PHOTO = DATA_DIR / "KonstantinAlthaus.jpeg"

BIBLIOGRAPHY_TEMPLATE = TEMPLATES_DIR / "bibliography_template.tex"
BIBLIOGRAPHY = DATA_DIR / "my_publications.bib"

TAGS_FILE = DATA_DIR / "tags.yaml"
TAGS_TYPES = ["Strength", "Learning"]
TAGS_SUBTYPES = ["Personal Trait", "Experience", "Skill"]

PERSONAL_INFO_TEMPLATE = TEMPLATES_DIR / "personal_info_template.tex"

SUPPORTED_INFOFIELDS = ["xing", "linkedin"]
SECTIONS = ["experience", "education", "projects", "references"]
LATEX_COMMANDS = {
    "projects": "cvproject",
    "experience": "cvevent",
    "education": "cvevent",
    "references": "cvreference",
}

OUTPUT = f"CV Althaus {datetime.now().strftime('%Y-%m')}"
OUTPUT_PATH = PROJECT_DIR / f"{OUTPUT}.pdf"

SOPS_ENCRYPTION_FLAG = "sops"
SOPS_PRIVATE_KEY_ENV = "SOPS_AGE_KEY"
