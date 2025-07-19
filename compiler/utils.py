from pathlib import Path

from tabulate import tabulate


def read_file(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
        return content


def write_file(content, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def print_table(table, file_path="temp", show=True, save=False):
    # ACTION表
    action_rows = []
    for state, actions in table.states.items():
        for token, (action, arg) in actions.items():
            if getattr(action, '__name__', str(action)) == "Shift":
                action_rows.append([state, token, "SHIFT", arg])
            elif getattr(action, '__name__', str(action)) == "Reduce":
                action_rows.append([state, token, "REDUCE", getattr(arg, 'origin', arg)])
            else:
                action_rows.append([state, token, str(action), arg])
    action_table = tabulate(action_rows,
                            headers=["State", "Token", "Action", "Arg"],
                            tablefmt="simple_grid",
                            numalign="center",
                            stralign="center")

    # GOTO表
    goto_rows = []
    for state, actions in table.states.items():
        for token, (action, arg) in actions.items():
            if getattr(action, '__name__', str(action)) == "Shift" and not token.islower():
                goto_rows.append([state, token, "GOTO", arg])
    goto_table = tabulate(goto_rows,
                          headers=["State", "Token", "Action", "Arg"],
                          tablefmt="simple_grid",
                          numalign="center",
                          stralign="center")

    # 打印
    if show:
        print(' ACTION '.center(40, '='))
        print(action_table)
        print()
        print('  GOTO  '.center(40, '='))
        print(goto_table)

    # 分别写入两个文件
    if save:
        action_path = Path(file_path) / "02 action_table.txt"
        goto_path = Path(file_path) / "02 goto_table.txt"
        write_file(action_table, action_path)
        write_file(goto_table, goto_path)
