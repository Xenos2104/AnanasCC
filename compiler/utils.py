import os


def is_file(file_path):
    return os.path.isfile(file_path)


def read_file(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
        return content


def write_file(content, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
