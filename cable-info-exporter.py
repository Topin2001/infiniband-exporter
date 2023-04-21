import csv
import logging
import argparse
import json


def csv_global_parser(csv_file_input):
    cable_info = []
    with open(csv_file_input, mode='r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        isCableInfoData = False
        for row in reader:
            if 'END_CABLE_INFO' in row :
                logging.debug('Now out of cable info table')
                isCableInfoData = False
            if isCableInfoData :
                cable_info.append(','.join(row))
            if 'START_CABLE_INFO' in row :
                logging.debug('Now in cable info table')
                isCableInfoData = True
    return cable_info

def cable_info_filter(cable_info):

    with open('request.json') as f:
        filtered_row = []
        filters = json.load(f)["filters"]
        reader = csv.DictReader(cable_info, delimiter=',')

        for row in reader :
            filter_row = {}
            for key,should_filter in filters.items():
                if should_filter:
                    filter_row[key] = row[key]
        
            filtered_row.append(filter_row)
    
    return filtered_row




if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prometheus collector for a infiniband fabric')
    parser.add_argument("--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument(
        '--csv-file-input',
        action='store',
        dest='csv_file_input',
        default='/var/tmp/ibdiagnet2/ibdiagnet2.db_csv',
        help='csv file used to gather data of different cable.')


    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        
    if args.csv_file_input:
        logging.debug(f'Using csv file input provided in args : {args.csv_file_input}')
        csv_file_input = args.csv_file_input
    else:
        logging.debug(f'Using default csv file input')
        csv_file_input = args.csv_file_input


        
    cable_info_row = csv_global_parser(csv_file_input)
    cable_info_filtered = cable_info_filter(cable_info_row)
    for cable_info in cable_info_filtered :
        print(cable_info)