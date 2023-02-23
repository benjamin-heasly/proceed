import argparse
import sys
from typing import Optional, Sequence

from fizzbuzz import fizzbuzz

# python3 -m pipeline_stuff.fizzbuzz.fizzbuzz_runner tests/fizzbuzz/fixture_files/classify_in.txt ./thingy.txt classify
# python3 -m pipeline_stuff.fizzbuzz.fizzbuzz_runner ./thingy.txt ./thingy2.txt filter --substring fizz
# python3 -m pipeline_stuff.fizzbuzz.fizzbuzz_runner ./thingy2.txt ./thingy3.txt filter --substring buzz

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Classify and filter lines of text files, according to fizzbuzz.")
    parser.add_argument("in_file", type=str, help="input file to read")
    parser.add_argument("out_file", type=str, help="output file to write")
    parser.add_argument("operation", type=str, help="operation to perform", choices=["classify", "filter"])
    parser.add_argument("--substring", type=str, help="filter substring for lines to keep", default="fizz")
    args = parser.parse_args(argv)

    if args.operation == "classify":
        fizzbuzz.classify_lines(args.in_file, args.out_file)
    elif args.operation == "filter":
        fizzbuzz.filter_lines(args.in_file, args.out_file, args.substring)

    return 0


if __name__ == '__main__':
    sys.exit(main())
