import csv
import logging
import argparse
import json
import time

from prometheus_client.core import GaugeMetricFamily
from prometheus_client import make_wsgi_app
from wsgiref.simple_server import make_server, WSGIRequestHandler


def csv_global_parser(csv_file_input):
    cable_info = []
    pm_info = []
    temp_sensing = []
    try:
        with open(csv_file_input, mode='r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            isCableInfoData = False
            isTempSensingData = False
            isPmInfoData = False
            for row in reader:
                if 'END_CABLE_INFO' in row:
                    logging.debug('Now out of cable info table')
                    isCableInfoData = False
                if isCableInfoData:
                    cable_info.append(','.join(row))
                if 'START_CABLE_INFO' in row:
                    logging.debug('Now in cable info table')
                    isCableInfoData = True
                if 'END_TEMP_SENSING' in row:
                    logging.debug('Now out of temp sensing table')
                    isTempSensingData = False
                if isTempSensingData:
                    temp_sensing.append(','.join(row))
                if 'START_TEMP_SENSING' in row:
                    logging.debug('Now in temp sensing table')
                    isTempSensingData = True
                if 'END_PM_INFO' in row:
                    logging.debug('Now out of pm info table')
                    isPmInfoData = False
                if isPmInfoData:
                    pm_info.append(','.join(row))
                if 'START_PM_INFO' in row:
                    logging.debug('Now in pm info table')
                    isPmInfoData = True
    except Exception as e:
        logging.error(f"Error while reading the CSV file: {e}")
        raise ParsingError("Error while parsing the CSV file")
    return cable_info, pm_info, temp_sensing


def cable_info_filter(cable_info):
    try:
        with open('request.json') as f:
            filtered_row = []
            label = []
            value = []
            filters = json.load(f)["cable_info_filters"]
            reader = csv.DictReader(cable_info, delimiter=',')
            for key, type in filters.items():
                if type == 'value':
                    value.append(key)
                else:
                    label.append(key)
            for row in reader:
                filter_row = {}
                for key, type in filters.items():
                    filter_row[key.lower()] = row[key].lower()
                filtered_row.append(filter_row)
    except Exception as e:
        logging.error(f"Error while filtering the cable info: {e}")
        raise ParsingError("Error while filtering the cable info")
    return filtered_row, value, label

def pm_info_filter(pm_info):
    try:
        with open('request.json') as f:
            filtered_row = []
            label = []
            value = []
            filters = json.load(f)["pm_info_filters"]
            reader = csv.DictReader(pm_info, delimiter=',')
            for key, type in filters.items():
                if type == 'value':
                    value.append(key)
                else:
                    label.append(key)
            for row in reader:
                filter_row = {}
                for key, type in filters.items():
                    filter_row[key.lower()] = row[key].lower()
                filtered_row.append(filter_row)
    except Exception as e:
        logging.error(f"Error while filtering the cable info: {e}")
        raise ParsingError("Error while filtering the cable info")
    return filtered_row, value, label

def temp_sensing_filter(temp_sensing):
    try:
        with open('request.json') as f:
            filtered_row = []
            filters = json.load(f)["temp_sensing_filters"]
            reader = csv.DictReader(temp_sensing, delimiter=',')
            for row in reader:
                filter_row = {}
                for key, type in filters.items():
                    filter_row[key.lower()] = row[key].lower()
                filtered_row.append(filter_row)
    except Exception as e:
        logging.error(f"Error while filtering the temp sensing: {e}")
        raise ParsingError("Error while filtering the temp sensing")
    return filtered_row


def double_rm(myList):
    result = []
    marker = set()

    for l in myList:
        ll = l.lower()
        if ll not in marker:   # test presence
            marker.add(ll)
            result.append(l)   # preserve order
    
    return result

def join_csv(ldict1, ldict2):
    for dic1 in ldict1:
        for dic2 in ldict2:
            if dic1['nodeguid'] == dic2['nodeguid'] and dic1['portnum'] == dic2['portnumber']:
                dic1.update(dic2)
    return(ldict1)

class ParsingError(Exception):
    pass

class InfinibandCollector(object):
    def __init__(self, labels, values, cable_info_filtered, node_name_map):
        self.labels = labels
        self.values = values
        self.cable_info_filtered = cable_info_filtered
        self.node_name_map = node_name_map

        self.scrape_with_errors = False
        self.metrics = {}
        self.gauge = {}

        for value in values :
            self.gauge[f'{value}'] = {
                    'help': f'Device current {value}.'
            }


    def init_metrics(self):

        for value in self.gauge:
            self.metrics[value] = GaugeMetricFamily(
                'infiniband_' + value.lower(),
                self.gauge[value]['help'],
                labels = self.labels
            )

    def data_link(self):

        for cable_info in cable_info_filtered :
            name = ""
            if self.node_name_map :
                with open(self.node_name_map, 'r') as file:
                    datas = file.readlines()
                    for data in datas:
                        if cable_info['nodeguid'] in data:
                            name = data.split(" ")[1]
            cable_info['nodename'] = name
            self.label_values = []
            self.value_values = 0
            for label in self.labels:
                self.label_values.append(cable_info[label.lower()])
            for value in self.gauge:
                label_values = self.label_values
                try :
                    self.value_values = int(cable_info[value.lower()])
                except ValueError:
                    logging.error(f'The value {value} is not an int.')

                self.metrics[value].add_metric(label_values, self.value_values)


    def collect(self):

        logging.debug('Start of collection cycle')

        self.scrape_with_errors = False
        
        scrape_duration = GaugeMetricFamily(
            'infiniband_scrape_duration_seconds',
            'Number of seconds taken to collect and parse the stats.')
        scrape_start = time.time()
        scrape_ok = GaugeMetricFamily(
            'infiniband_scrape_ok',
            'Indicates with a 1 if the scrape was successful and complete, '
            'otherwise 0 on any non critical errors detected '
            'e.g. ignored lines from ibqueryerrors STDERR or parsing errors.')

        self.init_metrics()

        self.data_link()
        
        for value in self.gauge:
            yield self.metrics[value]

        scrape_duration.add_metric([], time.time() - scrape_start)
        yield scrape_duration

        if self.scrape_with_errors:
            scrape_ok.add_metric([], 0)
        else:
            scrape_ok.add_metric([], 1)
        yield scrape_ok

        logging.debug('End of collection cycle')


class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


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
    parser.add_argument(
        '--port',
        type=int,
        default=9685,
        help='Collector http port, default is 9685')
    parser.add_argument(
        '--node-name-map',
        action='store',
        dest='node_name_map',
        help='Node name map used by ibqueryerrors. Can also be set with env \
var NODE_NAME_MAP')


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
    
    if args.node_name_map:
        logging.debug('Using node-name-map provided in args: %s', args.node_name_map)
        node_name_map = args.node_name_map
    else:
        logging.debug('No node-name-map was provided')
        node_name_map = None


        
    cable_info_raw, pm_info_raw, temp_sensing_raw = csv_global_parser(csv_file_input)

    cable_info_filtered, cable_info_values, cable_info_labels = cable_info_filter(cable_info_raw)
    temp_sensing_filtered = temp_sensing_filter(temp_sensing_raw)
    pm_info_filtered, pm_info_values, pm_info_labels = pm_info_filter(pm_info_raw)

    info_merged = join_csv(cable_info_filtered, pm_info_filtered)
    
    merged_info_labels = double_rm(cable_info_labels + pm_info_labels)
    merged_info_values = double_rm(cable_info_values + pm_info_values)

    merged_info_labels.append('NodeName')
    app = make_wsgi_app(InfinibandCollector(
        labels=merged_info_labels, values=merged_info_values, cable_info_filtered=info_merged, node_name_map=node_name_map))
    httpd = make_server('', args.port, app,
                        handler_class=NoLoggingWSGIRequestHandler)
    httpd.serve_forever()
