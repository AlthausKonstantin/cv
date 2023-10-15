from source import *

data_dir = './data/'
tex_dir = './tex/'
csv_files = [ './data/experience.csv', './data/education.csv']
for csv_file in csv_files:
    tex_file = csv_to_tex(csv_file, data_dir, tex_dir)
pdf_file = tex_to_pdf('tex/main.tex', tex_dir)

