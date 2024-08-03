""" Functions to decrypt, load and arrange data in tex source code. """
import subprocess
from shutil import move
import tempfile
import warnings
from os import environ
from pathlib import Path
from re import compile, findall, sub
from typing import Callable

import pandas as pd
import vobject
from jinja2 import Environment, FileSystemLoader
from pyshorteners import Shortener
from yaml import safe_load

from constants import (BIBLIOGRAPHY, BIBLIOGRAPHY_TEMPLATE,
                       BIBLIOGRAPHY_TEX_FILE, DATA_DIR, LATEX_COMMANDS,
                       MAIN_TEX_FILE, OUTPUT, OUTPUT_DIR, PERSONAL_INFO_TEMPLATE,
                       PERSONAL_INFO_TEX_FILE, PHOTO, PROJECT_DIR, SECTIONS,
                       SOPS_ENCRYPTION_FLAG, SOPS_PRIVATE_KEY_ENV,
                       SUPPORTED_INFOFIELDS, TAGS_FILE, TAGS_SUBTYPES,
                       TAGS_TEX_FILE, TAGS_TYPES, TEX_DIR, VCARD)


def compile_main() -> None:
    """Compile main.tex with lualatex and biber to get references right."""
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
        if not OUTPUT_DIR.exists():
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        else:
            for file in OUTPUT_DIR.glob("*"):
                file.unlink()
        move(output, OUTPUT_DIR / OUTPUT)


def make_source_files() -> None:
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


def read_yaml(path: Path, idx_data_col_name="title") -> pd.DataFrame:
    """
    Read yaml file and return it as pandas dataframe.

    If data is encrypted, return it as string with 4 bullets.
    """
    data_dict = read_encrypted_yaml(path)
    if SOPS_ENCRYPTION_FLAG in data_dict:
        # format encrypted strings
        encryption_info = data_dict[SOPS_ENCRYPTION_FLAG]
        enc_keys_pattern = encryption_info.get("encrypted_regex", "*")
        enc_keys_regex = compile(enc_keys_pattern)

        def enc_filter(x):
            return bool(enc_keys_regex.match(x))

        def encrypted_output(x):
            return 4 * "\\bullet"

        del data_dict[SOPS_ENCRYPTION_FLAG]
        data_dict = traverse_nested_dict(data_dict, enc_filter, encrypted_output)
    # add highest level keys to dicts
    data_list = [d | {idx_data_col_name: k} for k, d in data_dict.items()]
    # return data as pandas dataframe
    data = pd.DataFrame(data_list)
    return data


def read_encrypted_yaml(path: Path) -> dict:
    """
    Load yaml file and decrypt it with sops.

    If encryption fails, load and return original file
    """
    # check if private key is available
    if SOPS_PRIVATE_KEY_ENV not in environ:
        with open(path, "r") as f:
            return safe_load(f)
    # decrypt file
    try:
        decrypted = subprocess.run(
            ["sops", "--decrypt", path],
            capture_output=True,
            check=True,
        )
        return safe_load(decrypted.stdout)
    except subprocess.CalledProcessError:
        with open(path, "r") as f:
            return safe_load(f)


def traverse_nested_dict(
    data: dict, filter: Callable, operation: Callable, output=None
) -> dict:
    """Recursively apply operation to all keys matching the filter."""
    if output is None:
        output = {}
    for key, value in data.items():
        if filter(key):
            output[key] = operation(value)
        elif isinstance(value, dict):
            output[key] = traverse_nested_dict(value, filter, operation)
        else:
            output[key] = value
    return output


def make_tags_tex(tags_file: Path, tex_file: Path, tag_types: list, tag_subtypes: list) -> None:
    """Arrange tags from yaml file in groups and subgroups as LaTeX code."""
    tags = read_yaml(tags_file)
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
            with warnings.catch_warnings(action="ignore"):
                subgroup["tex_code"] = subgroup.apply(
                    row_to_tex_code,
                    axis=1,
                    latex_command="cvtag",
                    options={"color": "accent"},
                )
            subgroup = subgroup.sort_values(by="importance", ascending=False)
            subgroup_content = "\n".join(subgroup.tex_code.values)
            subgroup_content_list.append(subgroup_content)
        section_content = "\n\\medskip\n\n".join(subgroup_content_list)
        if not tex_output:
            tex_output = "\n".join([section_title, section_content])
        else:
            tex_output = "\n".join(
                [tex_output, "\\medskip\n\n", section_title, section_content]
            )
    with open(tex_file, "w") as f:
        f.write(tex_output)


def parser_personal_info(path_to_vcard: Path, path_to_photo: Path) -> dict:
    """Parse vcard and arrange personal info in a dict."""
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
        "photo": path_to_photo.with_suffix(""),
    }
    return personal_info


def fill_template(template: Path, data: dict, output: Path) -> None:
    """Fill template file with data and save them as LaTeX file"""
    env = Environment(
        loader=FileSystemLoader(template.parent),
        variable_start_string="[[",
        variable_end_string="]]",
    )
    temp = env.get_template(template.name)
    output.write_text(temp.render(data))


def yaml_to_tex(section: str, data_dir: Path, tex_dir: Path) -> Path:
    """
    Open yaml file as dataframe and convert rows to tex code.

    The section governs the latex command used to format the data.
    """

    yaml_file = data_dir / f"{section}.yaml"
    tex_file = tex_dir / f"{section}.tex"
    data = read_yaml(yaml_file)
    data = data.where(pd.notnull(data), None)
    has_durations = "start" in data.columns
    has_durations &= "end" in data.columns
    if has_durations:
        data[["start", "end"]] = data[["start", "end"]].apply(pd.to_datetime)
        data = data.applymap(lambda x: clean_string(x) if isinstance(x, str) else x)
        data = data.sort_values("start", ascending=False)
    latex_command = LATEX_COMMANDS[section]
    data["tex_code"] = data.apply(row_to_tex_code, axis=1, latex_command=latex_command)
    tex_output = "\n\\bigskip\n".join(data.tex_code.values)
    with open(tex_file, "w") as text_file:
        text_file.write(tex_output)
    print(f"wrote {tex_file}")
    return tex_file


def row_to_tex_code(row: pd.Series, latex_command="cvevent", options=None) -> str:
    """Dispatch row to the correct function based on the latex command."""
    if latex_command == "cvevent":
        return make_cvevent(row, options=options)
    if latex_command == "cvproject":
        return make_cvproject(row, options=options)
    if latex_command == "cvtag":
        return make_cvtag(row, options=options)
    if latex_command == "cvreference":
        return make_cvreference(row, options=options)
    else:
        return ""


def make_cvreference(row: pd.Series, options=None) -> str:
    """Convert the data in row to a cvreverence tex code."""
    who = row["title"]
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


def make_cvtag(row: pd.Series, options=None) -> str:
    """Convert the data in row to a cvtag tex code."""
    if options is None:
        tag = f"\\cvtag{{ {row.title} }}"
    else:
        if "color" in options.keys():
            tag = f"\\cvtagaccent{{ {row.title} }}"
        else:
            tag = f"\\cvtag{{ {row.title} }}"
    return tag


def make_cvproject(row: pd.Series, options=None) -> str:
    """Convert the data in row to a cvproject tex code."""
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
    punchline = clean_string(row.punchline, mandatory_suffix="!")
    punchline = enclose_in_tex_environment(punchline, "quote")
    cv_project = "\n".join([cv_project, punchline, what, tags])
    return put_in_pagebreakfree_section(cv_project)


def make_cvevent(row: pd.Series, options=None) -> str:
    """Convert the data in row to cvevent tex code"""
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
    """Remove unnecessary whitespace and add suffix if not present."""
    string = string.strip()
    string = sub(r"\s+", " ", string)
    if mandatory_suffix:
        if not string.endswith(mandatory_suffix):
            string += mandatory_suffix
    return string


def format_time_period(start, end) -> str:
    """Make duration string from start and end."""
    if pd.isnull(end):
        return f"{{ {start:%m/%Y} -- now }}"
    else:
        return f"{{ {start:%m/%Y} -- {end:%m/%Y} }}"


def list_to_tex_list(data: list) -> str:
    """Arrange content in list in tex itemize environment."""
    if not data:
        return ""
    tex_list = "\\begin{itemize}"
    for item in data:
        item = clean_string(item, mandatory_suffix=".")
        tex_list += f"\n\\item {item}"
    tex_list += "\n\\end{itemize}"
    return tex_list


def taglist_to_texcode(data: list) -> str:
    """Apply special formatting to inline tag lists."""
    if not data:
        return ""
    tex_list = ""
    for item in data:
        tex_list += f"\\cvtag{{ {item} }}"
    tex_list = enclose_in_tex_environment(tex_list, "spacing", kwarg="0.5")
    return tex_list


def linkdict_to_texcode(data: dict) -> str:
    """Make a list of printinfo tex code commands."""
    if not data:
        return ""
    tex_list = ""
    for link_type, url in data.items():
        url = shorten_url(url)
        icon_name = get_icon_for_link(link_type)
        tex_list += f"\\printinfo{{ \\{icon_name} }}{{{url}}}[{url}]"
    return tex_list


def put_in_pagebreakfree_section(tex_code: str) -> str:
    """Enclose tex_code in page-break free environment"""
    output = "\\begin{breakfreeunit}\n"
    output += tex_code
    output += "\n\\end{breakfreeunit}"
    return output


def enclose_in_tex_environment(tex_code: str, environment: str, kwarg=None) -> str:
    """Enclose tex_code in environment command."""
    if kwarg:
        output = f"\\begin{{{environment}}}{{{kwarg}}}\n"
    else:
        output = f"\\begin{{{environment}}}\n"
    output += tex_code
    output += f"\n\\end{{{environment}}}"
    return output


def get_icon_for_link(url: str) -> str:
    """Return icon for url."""
    if "github" in url:
        return "faGithub"
    else:
        return "faGlobe"


def check_for_duplicate_icons(tex_code: str) -> str:
    """Check if tex_code has multiple occurrences of the same icon."""
    icons = findall(r"\\fa[A-Z]\w+", tex_code)
    assert len(icons) == len(set(icons)), "Duplicate url-icons look stupid"


def shorten_url(url: str) -> str:
    """Make a tiny url."""
    is_github_url = "github.com" in url
    try:
        shortener = Shortener()
        if is_github_url:
            return shortener.gitio.short(url)
        else:
            return shortener.tinyurl.short(url)
    except Exception:
        return url
