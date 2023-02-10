def classify(number):
    suffix = ""
    if number % 3 == 0:
        suffix = suffix + "fizz"
    
    if number % 5 == 0:
        suffix = suffix + "buzz"

    return suffix

def append(line):
    number = int(line)
    suffix = classify(number)
    if (suffix):
        return f"{line} {suffix}"
    else:
        return line

def classify_lines(in_file, out_file):
    with open(out_file, 'w') as out_f:
        with open(in_file) as in_f:
            for in_line in in_f:
                out_line = append(in_line.strip()) + "\n"
                out_f.write(out_line)

def filter_lines(in_file, out_file, substring):
    with open(out_file, 'w') as out_f:
        with open(in_file) as in_f:
            for in_line in in_f:
                if substring in in_line:
                    out_f.write(in_line)
