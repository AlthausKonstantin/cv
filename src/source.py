import pandas as pd
import vobject
from pyshorteners import Shortener
from re import findall
from jinja2 import FileSystemLoader, Environment
import tempfile
import subprocess
from constants import SECTIONS
from constants import BIBLIOGRAPHY
from constants import VCARD
from constants import PHOTO
from constants import DATA_DIR
from constants import TEX_DIR
from constants import PROJECT_DIR
from constants import MAIN_TEX_FILE
from constants import LATEX_COMMANDS
from pathlib import Path


def compile_main():
    with tempfile.TemporaryDirectory() as dir:
        for i in range(2):
            # complie twice to get the references right
            subprocess.run(
                [
                    "lualatex",
                    "-synctex=1",
                    "--interaction=nonstopmode",
                    f"--output-directory={dir}",
                    MAIN_TEX_FILE,
                ],
                cwd=TEX_DIR,
            )
            if i == 0:
                subprocess.run(
                    [
                        "biber",
                        f"--output-directory={dir}",
                        "main",
                    ],
                    cwd=TEX_DIR,
                )
        output = Path(dir) / "main.pdf"
        output.rename(PROJECT_DIR / "cv.pdf")


def make_source_files():
    # make personal information
    personal_info = parser_personal_info(VCARD, PHOTO)
    fill_template(
        Path("templates/personal_info_template.tex"),
        personal_info,
        TEX_DIR / "personal_info.tex",
    )
    # make bibliography
    fill_template(
        Path("templates/bibliography_template.tex"),
        {"bibliography": BIBLIOGRAPHY},
        TEX_DIR / "bibliography.tex",
    )
    # make sections
    for sec in SECTIONS:
        csv_to_tex(sec, DATA_DIR, TEX_DIR)


def parser_personal_info(path_to_vcard: Path, path_to_photo: Path) -> dict:
    with open(path_to_vcard, "r") as f:
        vcard = vobject.readOne(f.read())
    for social_profile in vcard.contents["x-socialprofile"]:
        if social_profile.type_param == "linkedin":
            linkedin = social_profile.value
            linkedin = linkedin.replace("https://www.linkedin.com/in/", "")
            linkedin = linkedin.replace("/", "")
    github = None
    for url_idx, url in enumerate(vcard.contents["url"]):
        url_type = list(vcard.contents["x-ablabel"])[url_idx]
        if url_type.value.lower() == "github":
            github = url.value
            github = github.replace("https://github.com/", "")
            github = github.replace("/", "")
    personal_info = {
        "name": vcard.fn.value,
        "job_title": vcard.title.value,
        "email": vcard.email.value,
        "phone": vcard.tel.value,
        "location": f"{vcard.adr.value.city}, {vcard.adr.value.country}",
        "github": github,
        "linkedin": linkedin,
        "photo": path_to_photo.with_suffix('')
    }
    return personal_info


def fill_template(template: Path, data: dict, output: Path):
    env = Environment(loader=FileSystemLoader(template.parent),
                      variable_start_string="[[",
                      variable_end_string="]]")
    temp = env.get_template(template.name)
    output.write_text(temp.render(data))


def csv_to_tex(section, data_dir, tex_dir):
    csv_file = data_dir / f"{section}-Tabelle 1.csv"
    tex_file = tex_dir / f"{section}.tex"
    data = pd.read_csv(csv_file)
    data[["start", "end"]] = data[["start", "end"]].apply(pd.to_datetime)
    data = data.sort_values("start", ascending=False)
    latex_command = LATEX_COMMANDS[section]
    data["tex_code"] = data.apply(row_to_tex_code,
                                  axis=1,
                                  latex_command=latex_command)
    tex_output = "\n".join(data.tex_code.values)
    with open(tex_file, "w") as text_file:
        text_file.write(tex_output)
    print(f"wrote {tex_file}")
    return tex_file


def row_to_tex_code(row, latex_command="cvevent"):
    if latex_command == "cvevent":
        return make_cvevent(row)
    if latex_command == "cvproject":
        return make_cvproject(row)
    else:
        return ""


def make_cvproject(row):
    title = f"\\cvproject{{ {row.title} }}{{| {row.subtitle} }}"
    if pd.isnull(row.end):
        when = f"{{ {row.start:%m/%Y} -- now  }}"
    else:
        when = f"{{ {row.start:%m/%Y} -- {row.end:%m/%Y}  }}"
    row = row.replace(pd.NA, None)
    link_columns = [col for col in row.index if col.startswith("url")]
    links = "{{"
    for col in link_columns:
        url = row[col]
        url = shorten_url(url)
        icon_name = get_icon_for_link(url)
        links += f"\\printinfo{{ \\{icon_name} }}{{{url}}}[{url}]"
    links += "}}"
    check_for_duplicate_icons(links)
    description_cols = [col for col in row.index if col.startswith("descr")]
    what = "\\begin{itemize}"
    for col in description_cols:
        description_content = row[col]
        if description_content:
            what += "\n"
            what += f"\\item {row[col]}"
    what += "\n"
    what += "\\end{itemize}"
    tag_columns = [col for col in row.index if col.startswith("tag")]
    tags = "\\quad"
    for col in tag_columns:
        tag_content = row[col]
        if tag_content:
            tags += f"\\cvtag{{ {tag_content} }}"
    tags += "\\newline"
    cv_project = title + when + links
    cv_project += "\n"
    cv_project += what
    cv_project += "\n"
    cv_project += tags
    # cv_project = put_in_pagebreakfree_section(cv_project)
    return cv_project


def make_cvevent(row):
    title = f"\\cvevent{{ {row.title} }}{{| {row.employee} }}"
    if pd.isnull(row.end):
        when = f"{{ {row.start:%m/%Y} -- now  }}"
    else:
        when = f"{{ {row.start:%m/%Y} -- {row.end:%m/%Y}  }}"
    row = row.replace(pd.NA, None)
    where = f"{{ {row.location} }}" if row.location else "{}"
    industry = f"{{ {row.industry} }}" if row.industry else "{}"
    description_cols = [col for col in row.index if col.startswith("descr")]
    what = "\\begin{itemize}"
    for col in description_cols:
        description_content = row[col]
        if description_content:
            what += "\n"
            what += f"\\item {row[col]}"
    what += "\n"
    what += "\\end{itemize}"
    tag_columns = [col for col in row.index if col.startswith("tag")]
    tags = "\\quad"
    for col in tag_columns:
        tag_content = row[col]
        if tag_content:
            tags += f"\\cvtag{{ {tag_content} }}"
    tags += "\\newline"
    cv_event = title + when + where + industry
    cv_event += "\n"
    cv_event += what
    cv_event += "\n"
    cv_event += tags
    # cv_event = put_in_pagebreakfree_section(cv_event)
    return cv_event


def put_in_pagebreakfree_section(tex_code):
    output = '\\begin{breakfreeunit}\n'
    output += tex_code
    output += '\n\\end{breakfreeunit}'
    return output


def get_icon_for_link(url):
    if "github" in url:
        return "faGithub"
    else:
        return "faGlobe"


def check_for_duplicate_icons(tex_code):
    icons = findall(r"\\fa[A-Z]\w+", tex_code)
    assert len(icons) == len(set(icons)), "Duplicate url-icons look stupid"


def shorten_url(url):
    is_github_url = 'github.com' in url
    try:
        shortener = Shortener()
        if is_github_url:
            return shortener.gitio.short(url)
        else:
            return shortener.tinyurl.short(url)
    except Exception:
        return url
