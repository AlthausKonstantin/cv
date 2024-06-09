import pandas as pd
from re import sub
from yaml import safe_load
import vobject
from pyshorteners import Shortener
from re import findall
from jinja2 import FileSystemLoader, Environment
import tempfile
import subprocess
from constants import SUPPORTED_INFOFIELDS
from constants import BIBLIOGRAPHY_TEX_FILE, PERSONAL_INFO_TEX_FILE, SECTIONS
from constants import PERSONAL_INFO_TEMPLATE
from constants import BIBLIOGRAPHY_TEMPLATE
from constants import TAGS_FILE
from constants import TAGS_TEX_FILE
from constants import TAGS_TYPES
from constants import TAGS_SUBTYPES
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
        PERSONAL_INFO_TEMPLATE,
        personal_info,
        PERSONAL_INFO_TEX_FILE,
    )
    # make bibliography
    fill_template(
        BIBLIOGRAPHY_TEMPLATE,
        {"bibliography": BIBLIOGRAPHY},
        BIBLIOGRAPHY_TEX_FILE,
    )
    # make tags
    make_tags_tex(TAGS_FILE, TAGS_TEX_FILE, TAGS_TYPES, TAGS_SUBTYPES)
    # make main sections
    for sec in SECTIONS:
        yaml_to_tex(sec, DATA_DIR, TEX_DIR)


def make_tags_tex(tags_file: Path, tex_file: Path, tag_types: list, tag_subtypes: list):
    # read in yaml file
    with open(tags_file, "r") as f:
        tags = pd.json_normalize(safe_load(f))
    tags_by_type = tags.groupby(by="type")
    tex_output = ""
    for tag_type in tag_types:
        if tag_type not in tags_by_type.groups:
            continue
        group = tags_by_type.get_group(tag_type)
        group = group.groupby(by="subtype")
        section_title = f"\\cvsection{{ {tag_type} }}"
        subgroup_content_list = []
        for tag_subtype in tag_subtypes:
            if tag_subtype not in group.groups:
                continue
            subgroup = group.get_group(tag_subtype)
            subgroup["tex_code"] = subgroup.apply(row_to_tex_code,
                                                  axis=1,
                                                  latex_command="cvtag")
            subgroup = subgroup.sort_values(by="importance", ascending=False)
            subgroup_content = "\n".join(subgroup.tex_code.values)
            subgroup_content_list.append(subgroup_content)
        section_content = "\n\\medskip\n\n".join(subgroup_content_list)
        if not tex_output:
            tex_output = "\n".join([section_title, section_content])
        else:
            tex_output = "\n".join([tex_output, "\\medskip\n\n", section_title, section_content])
    with open(tex_file, "w") as f:
        f.write(tex_output)


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


def yaml_to_tex(section: str, data_dir: Path, tex_dir: Path) -> Path:
    yaml_file = data_dir / f"{section}.yaml"
    tex_file = tex_dir / f"{section}.tex"
    with open(yaml_file, "r") as f:
        data = pd.json_normalize(safe_load(f))
    data = data.where(pd.notnull(data), None)
    has_durations = "start" in data.columns
    has_durations &= "end" in data.columns
    if has_durations:
        data[["start", "end"]] = data[["start", "end"]].apply(pd.to_datetime)
        data = data.applymap(
            lambda x: clean_string(x) if isinstance(x, str) else x
        )
        data = data.sort_values("start", ascending=False)
    latex_command = LATEX_COMMANDS[section]
    data["tex_code"] = data.apply(row_to_tex_code,
                                  axis=1,
                                  latex_command=latex_command)
    tex_output = "\n\n".join(data.tex_code.values)
    with open(tex_file, "w") as text_file:
        text_file.write(tex_output)
    print(f"wrote {tex_file}")
    return tex_file


def row_to_tex_code(row, latex_command="cvevent"):
    if latex_command == "cvevent":
        return make_cvevent(row)
    if latex_command == "cvproject":
        return make_cvproject(row)
    if latex_command == "cvtag":
        return make_cvtag(row)
    if latex_command == "cvreference":
        return make_cvreference(row)
    else:
        return ""


def make_cvreference(row) -> str:
    who = row["name"]
    where = row.position
    phone = row.get("phone", "")
    mail = row.get("mail", "")
    ref = "\\cvreference"
    ref += f"{{ {who} }}"
    ref += f"{{ {where} }}"
    ref += f"{{ {phone} }}"
    ref += f"{{ {mail} }}"
    description = row.get("description", "")
    description = f"\\textcolor{{accent}}{{{description}}}"
    social_network = row.get("url.service", None)
    social_name = row.get("url.username", None)
    url = row.get("url.link", None)

    if social_network in SUPPORTED_INFOFIELDS:
        # cave, this f string is whitespace sensitive
        info = f"\\{social_network}{{{social_name}}}\\\\"
        info = "\n".join([info, description])
    elif url is not None:
        # cave, this f string is whitespace sensitive
        stripped_url = sub("https://", "", url)
        info = f"\\hompage{{{stripped_url}}}\\\\"
        info = "\n".join([info, description])
    else:
        info = description
    ref += f"{{ {info} }}"
    ref = put_in_pagebreakfree_section(ref)
    return ref


def make_cvtag(row):
    tag = f"\\cvtag{{ {row.title} }}"
    return tag


def make_cvproject(row):
    title = f"\\cvproject{{ {row.title} }}{{| {row.subtitle} }}"
    when = format_time_period(row.start, row.end)
    if row.urls:
        # pandas saves a dict in a list with one element
        links = linkdict_to_texcode(row.urls[0])
        links = "{{" + links + "}}"
    else:
        links = "{}"
    cv_project = title + when + links
    what = list_to_tex_list(row.description)
    tags = taglist_to_texcode(row.tag)
    tags += "\\newline"
    punchline = clean_string(row.punchline, mandatory_suffix="!")
    punchline = enclose_in_tex_environment(punchline, "quote")
    cv_project = "\n".join([cv_project, punchline, what, tags])
    return put_in_pagebreakfree_section(cv_project)


def make_cvevent(row):
    title = f"\\cvevent{{ {row.title} }}{{| {row.employee} }}"
    when = format_time_period(row.start, row.end)
    location = getattr(row, "location", "")
    where = f"{{ {location} }}" if location else "{}"
    industry = getattr(row, "industry", "")
    industry = f"{{ {industry} }}" if industry else "{}"
    cv_event = title + when + where + industry
    what = list_to_tex_list(row.description)
    tags = taglist_to_texcode(row.tag)
    if hasattr(row, "punchline"):
        punchline = clean_string(row.punchline, mandatory_suffix="!")
        punchline = enclose_in_tex_environment(punchline, "quote")
        cv_event = "\n".join([cv_event, punchline, what, tags])
    else:
        cv_event = "\n".join([cv_event, what, tags])
    return put_in_pagebreakfree_section(cv_event)


def clean_string(string: str, mandatory_suffix=None) -> str:
    string = string.strip()
    string = sub(r"\s+", " ", string)
    if mandatory_suffix:
        if not string.endswith(mandatory_suffix):
            string += mandatory_suffix
    return string


def format_time_period(start, end):
    if pd.isnull(end):
        return f"{{ {start:%m/%Y} -- now }}"
    else:
        return f"{{ {start:%m/%Y} -- {end:%m/%Y} }}"


def list_to_tex_list(data: list) -> str:
    if not data:
        return ""
    tex_list = "\\begin{itemize}"
    for item in data:
        item = clean_string(item, mandatory_suffix=".")
        tex_list += f"\n\\item {item}"
    tex_list += "\n\\end{itemize}"
    return tex_list


def taglist_to_texcode(data: list) -> str:
    if not data:
        return ""
    tex_list = ""
    for item in data:
        tex_list += f"\\cvtag{{ {item} }}"
    return tex_list


def linkdict_to_texcode(data: dict) -> str:
    if not data:
        return ""
    tex_list = ""
    for link_type, url in data.items():
        url = shorten_url(url)
        icon_name = get_icon_for_link(link_type)
        tex_list += f"\\printinfo{{ \\{icon_name} }}{{{url}}}[{url}]"
    return tex_list


def put_in_pagebreakfree_section(tex_code: str) -> str:
    output = '\\begin{breakfreeunit}\n'
    output += tex_code
    output += '\n\\end{breakfreeunit}'
    return output


def enclose_in_tex_environment(tex_code, environment):
    output = f'\\begin{{{environment}}}\n'
    output += tex_code
    output += f'\n\\end{{{environment}}}'
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
