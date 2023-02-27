import argparse
import sys
from typing import Optional, Sequence


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


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Classify and filter lines of text files, according to fizzbuzz.")
    parser.add_argument("in_file", type=str, help="input file to read")
    parser.add_argument("out_file", type=str, help="output file to write")
    parser.add_argument("operation", type=str, help="operation to perform", choices=["classify", "filter"])
    parser.add_argument("--substring", type=str, help="filter substring for lines to keep", default="fizz")
    args = parser.parse_args(argv)

    if args.operation == "classify":
        classify_lines(args.in_file, args.out_file)
    elif args.operation == "filter":
        filter_lines(args.in_file, args.out_file, args.substring)

    print("OK.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
