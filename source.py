import pandas as pd
from jinja2 import FileSystemLoader, Environment
import tempfile
from os import remove, rename
from os.path import splitext, split, exists, abspath, basename, join
import subprocess


def tex_to_pdf(tex_file, tex_dir):
    tex_file = abspath(tex_file)
    tex_dir = abspath(tex_dir)
    file_no_ext = splitext(tex_file)[0]
    with tempfile.TemporaryDirectory() as dir:
        subprocess.run(['lualatex',
                        '-synctex=1',
                    '-interaction=nonstopmode',
                    tex_file], cwd=tex_dir)


def csv_to_tex(csv_file, data_dir, tex_dir):
    csv_file = abspath(csv_file)
    tex_file_name = splitext(basename(csv_file))[0] + ".tex"
    tex_file = abspath(join(tex_dir, tex_file_name))
    work_data = pd.read_csv(csv_file)
    work_data[["start", "end"]] = work_data[["start", "end"]].apply(pd.to_datetime)
    work_data = work_data.sort_values("start", ascending=False)
    work_data["tex_code"] = work_data.apply(row_to_cv_event, axis=1)
    tex_output = "\n".join(work_data.tex_code.values)
    with open(tex_file, "w") as text_file:
        text_file.write(tex_output)
    print(f'wrote {tex_file}')
    return tex_file


def row_to_cv_event(row):
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
    return cv_event

