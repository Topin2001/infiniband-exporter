#!/usr/bin/env python3

import subprocess
import shlex
import re
import argparse
import logging

def load_name(file):
    with open('guid_2_name.txt', 'w+') as f:
        f.writelines(file)


def main():
    guid_parse_regex = r'^.*(0x\w+).+\"(.+) (.+)\"$'

    cmd = f'ibhosts'
    cmd_output = subprocess.check_output(shlex.split(cmd))
    lines = cmd_output.decode().split("\n")
    del lines[-1]

    load_name(node_name_map)

    for line in lines :
        parsed_guid_name = re.split(guid_parse_regex, line)
        with open('guid_2_name.txt', 'a+') as f:
            f.write(f'{parsed_guid_name[1]} {parsed_guid_name[2] + "_" + parsed_guid_name[3]}\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prometheus collector for a infiniband fabric')
    parser.add_argument(
        '--node-name-map',
        action='store',
        dest='node_name_map',
        default='./sw_name_map.txt',
        type=argparse.FileType('r'),
        help='node-name-map used by temp-exporter. Can also be set with env var NODE_NAME_MAP')
    parser.add_argument("--verbose", help="increase output verbosity",
                        action="store_true")


    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    if args.node_name_map:
        logging.debug('Using node_name_map provided in args: %s', args.node_name_map)
        node_name_map = args.node_name_map
    else:
        logging.debug('No lid-to-node_name_map was provided')
        node_name_map = None
    '''elif 'LID_TO_NAME_MAP' in os.environ:
        logging.debug('Using LID_TO_NAME_MAP provided in env vars: %s', os.environ['LID_TO_NAME_MAP'])
        lid_to_name_map = os.environ['LID_TO_NAME_MAP']'''
    logging.debug('Start of mapping generation')
    main()
    logging.debug('End of mapping generation')