"""Transform data from yaml files to tex files and compile the main tex file."""
from make_tex_code import compile_main, make_source_files

if __name__ == "__main__":
    make_source_files()
    compile_main()
