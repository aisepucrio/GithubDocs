import argparse
import sys
import logging

#from src.load_configuration.load_conf import load_config
from util import solve_path_name
from log import *


parser = argparse.ArgumentParser()

parser.add_argument('-f', '--file', help='Input file path (use "-" or omit for stdin)', type=str, default='-')

parser.add_argument('-v', '--verbose', help='Verbose output level (0-2)', type=int, default=0)

args = parser.parse_args()

if args.verbose == 2:
    level = logging.DEBUG
elif args.verbose == 1:
    level = logging.INFO
else:
    level = logging.WARNING

CustomFormatter.setup_logging(level)

if args.file == '-' or args.file is None:
    logging.info("Reading input from stdin")
    input_text = sys.stdin.read()
else:
    args.file = str(solve_path_name(args.file))
    logging.info(f"Reading input from file: {args.file}")
    with open(args.file, 'r', encoding='utf-8') as fh:
        input_text = fh.read()

logging.info("Loading configuration...")

#config = load_config(input_text)

logging.success("Configuration loaded successfully.")