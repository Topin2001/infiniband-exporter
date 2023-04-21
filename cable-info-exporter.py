import csv
import logging
import argparse
import json


def csv_global_parser():
    cable_info = []
    with open('/var/tmp/ibdiagnet2/ibdiagnet2.db_csv', mode='r') as csvfile:
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


    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        
    cable_info_row = csv_global_parser()
    cable_info_filtered = cable_info_filter(cable_info_row)
    for cable_info in cable_info_filtered :
        print(cable_info)