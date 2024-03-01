from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
TEX_DIR = PROJECT_DIR / "tex"
MAIN_TEX_FILE = TEX_DIR / "main.tex"
SECTIONS = ["experience", "education", "projects"]
TAGS_TEX_FILE = TEX_DIR / "tags.tex"
PERSONAL_INFO_TEX_FILE = TEX_DIR / "personal_info.tex"
BIBLIOGRAPHY_TEX_FILE = TEX_DIR / "bibliography.tex"
VCARD = DATA_DIR / 'KonstantinAlthaus.vcf'
TAGS_FILE = DATA_DIR / "tags.csv"
TAGS_SUBTYPES = ["Personal Trait", "Experience", "Skill"]
TAGS_TYPES = ["Strength", "Learning"]
TEMPLATES_DIR = PROJECT_DIR / "templates"
PERSONAL_INFO_TEMPLATE = TEMPLATES_DIR / "personal_info_template.tex"
BIBLIOGRAPHY_TEMPLATE = TEMPLATES_DIR / "bibliography_template.tex"
PHOTO = DATA_DIR / "KonstantinAlthaus.jpeg"
BIBLIOGRAPHY = DATA_DIR / "my_publications.bib"
LATEX_COMMANDS = {
    "projects": "cvproject",
    "experience": "cvevent",
    "education": "cvevent",
}
