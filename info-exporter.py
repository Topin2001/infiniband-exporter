import csv
import logging
import argparse
import json
import re
import shlex
import subprocess
import time

from prometheus_client.core import GaugeMetricFamily
from prometheus_client import make_wsgi_app
from wsgiref.simple_server import make_server, WSGIRequestHandler


class ParsingError(Exception):
    pass

class InfinibandCollector(object):

    def csv_global_parser(self, csv_file_input):
        if csv_file_input == "/var/tmp/ibdiagnet2/ibdiagnet2.db_csv":
            logging.debug(f'Start file generation process')
            try:
                cmd = f'ibdiagnet --get_phy_info --disable_output default --enable_output db_csv'
                subprocess.run(shlex.split(cmd),
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            except FileNotFoundError as e:
                self.scrape_with_errors = True
                logging.error(f'An error occured with the generation of the csv : {e}')
            logging.debug(f'End of file generation process')
        cable_info = []
        pm_info = []
        temp_sensing = []
        link_info = []
        fan_info = []
        power_info = []
        try:
            with open(csv_file_input, mode='r') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                isCableInfoData = False
                isTempSensingData = False
                isPmInfoData = False
                isLinkInfo = False
                isFanInfo = False
                isPowerInfo = False
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
                    if 'END_LINKS' in row:
                        logging.debug('Now out of link info table')
                        isLinkInfo = False
                    if isLinkInfo:
                        link_info.append(','.join(row))
                    if 'START_LINKS' in row:
                        logging.debug('Now in link info table')
                        isLinkInfo = True
                    if 'END_FANS_SPEED' in row:
                        logging.debug('Now out of fan info table')
                        isFanInfo = False
                    if isFanInfo:
                        fan_info.append(','.join(row))
                    if 'START_FANS_SPEED' in row:
                        logging.debug('Now in fan info table')
                        isFanInfo = True
                    if 'END_POWER_SUPPLIES' in row:
                        logging.debug('Now out of power info table')
                        isPowerInfo = False
                    if isPowerInfo:
                        power_info.append(','.join(row))
                    if 'START_POWER_SUPPLIES' in row:
                        logging.debug('Now in fan info table')
                        isPowerInfo = True

        except Exception as e:
            logging.critical(f"Error while reading the CSV file: {e}")
            self.scrape_with_errors = True
        return cable_info, pm_info, temp_sensing, link_info, fan_info, power_info

    def data_filter(self, filter, info):
        filtered_row = []
        label = []
        value = []
        try:
            with open('request.json') as f:
                filters = json.load(f)[filter]
                if filter == "cable_info_filters" and 'NodeGuid' not in filters:
                    filters['NodeGuid'] = 'label'
                if filter == "cable_info_filters" and 'PortNum' not in filters:
                    filters['PortNum'] = 'label'
                if filter == "pm_info_filters" and 'NodeGUID' not in filters:
                    filters['NodeGUID'] = 'label'
                if filter == "pm_info_filters" and 'PortNumber' not in filters:
                    filters['PortNumber'] = 'label'
                if filter == "temp_sensing_filters" and 'NodeGUID' not in filters:
                    filters['NodeGUID'] = 'label'
                if filter == "fan_info_filters" and 'NodeGUID' not in filters:
                    filters['NodeGUID'] = 'label'
                if filter == "fan_info_filters" and 'FanIndex' not in filters:
                    filters['FanIndex'] = 'label'
                if filter == "power_info_filter" and 'NodeGuid' not in filters:
                    filters['NodeGuid'] = 'label'
                if filter == "power_info_filter" and 'PSUIndex' not in filters:
                    filters['PSUIndex'] = 'label'
                
                reader = csv.DictReader(info, delimiter=',')
                for row in reader:
                    filter_row = {}
                    for key, type in filters.items():
                        try:
                            filter_row[key.lower()] = row[key].lower()
                            if type == 'label':
                                if key not in label :
                                    label.append(key)
                            elif type == 'value':
                                if key not in value:
                                    value.append(key)
                            else :
                                logging.warning(f"The type '{type}' of '{key} 'is not recognise, setting as a value by default")
                                self.scrape_with_errors = True
                                value.append(key)
                        except KeyError :
                            logging.error(f'The key {key} was not recognise')
                            self.scrape_with_errors = True
                            continue
                    filtered_row.append(filter_row)
        except Exception as e:
            logging.error(f"Error while filtering the cable info: {e}")
            self.scrape_with_errors = True
        return filtered_row, value, label

    def double_rm(self, myList):
        result = []
        marker = set()

        for l in myList:
            ll = l.lower()
            if ll not in marker:   # test presence
                marker.add(ll)
                result.append(l)   # preserve order

        return result

    def join_csv(self, ldict1, ldict2):
        for dic1 in ldict1:
            for dic2 in ldict2:
                if dic1['nodeguid'] == dic2['nodeguid'] and dic1['portnum'] == dic2['portnumber']:
                    dic1.update(dic2)
        return(ldict1)

    def get_csv_value(self):

        self.cable_info_raw, self.pm_info_raw, self.temp_sensing_raw, self.link_info_raw, self.fan_info_raw, self.power_info_raw = self.csv_global_parser(self.csv_file_input)

        self.cable_info_filtered, self.cable_info_values, self.cable_info_labels = self.data_filter("cable_info_filters", self.cable_info_raw)
        self.temp_sensing_filtered, self.temp_sensing_values, self.temp_sensing_labels = self.data_filter("temp_sensing_filters", self.temp_sensing_raw)
        self.pm_info_filtered, self.pm_info_values, self.pm_info_labels = self.data_filter("pm_info_filters", self.pm_info_raw)
        self.fan_info_filtered, self.fan_info_values, self.fan_info_labels = self.data_filter("fan_info_filter", self.fan_info_raw)
        self.power_info_filtered, self.power_info_values, self.power_info_labels = self.data_filter("power_info_filter", self.power_info_raw)

        self.info_merged = self.join_csv(self.cable_info_filtered, self.pm_info_filtered)

        self.merged_info_labels = self.double_rm(self.cable_info_labels + self.pm_info_labels)
        self.merged_info_values = self.double_rm(self.cable_info_values + self.pm_info_values)

        if 'NodeGuid' not in self.merged_info_labels:
            self.merged_info_labels.append('NodeGuid')
        
        if 'PortNumber' not in self.merged_info_labels:
            self.merged_info_labels.append('PortNumber')

        if 'PortNum' in self.merged_info_labels:
            self.merged_info_labels.remove('PortNum')

        if 'NodeGUID' in self.merged_info_labels:
            self.merged_info_labels.remove('NodeGUID')

        self.temp_sensing_labels.append('NodeName')
        self.fan_info_labels.append('NodeName')
        self.power_info_labels.append('NodeName')
        self.merged_info_labels.extend(['NodeName', 'RemoteGuid', 'RemoteName', 'RemotePort'])

    def link_connexion(self, lguid, lport):
        rguid = ''
        rport = ''
        for line in csv.DictReader(self.link_info_raw, delimiter=','):
            if line['NodeGuid1'] == lguid and line['PortNum1'] == lport :
                rguid = line['NodeGuid2']
                rport = line['PortNum2']
        if rguid == '':
            for line in csv.DictReader(self.link_info_raw, delimiter=','):
                if line['NodeGuid2'] == lguid and line['PortNum2'] == lport :
                    rguid = line['NodeGuid1']
                    rport = line['PortNum1']
        return rguid, rport

    def __init__(self, node_name_map, csv_file_input, can_reset_counter):

        self.can_reset_counter = can_reset_counter
        self.node_name_map = node_name_map
        self.csv_file_input = csv_file_input
        
        self.get_csv_value()

        self.scrape_with_errors = False
        self.metrics = {}
        self.device_temp = {}
        self.gauge = {}

        self.device_temp['device_temperature'] = {
            'help': 'Device current temperature'
        }

        self.link_info = {
            'Link_State': {
                'help': 'Link current state.',
            }
        }

        self.power_info = {
            'power_state': {
                'help': 'Power current state.',
            }
        }

        self.fan_info = {
            'fan_speed':{
                'help':'Fan current speed'
            }
        }

        self.link_info_regex = r'^(?P<LGuid>0x\w+)\s+\"\s*(?P<LName>[\w\-_ ]+)\"\s+\d+\s+(?P<LPort>\d+)\[\s+\]\s+\=+\(\s+.+(?P<State>Active|Down)\/\s*(?P<P_State>\w+)(?:.+(?P<RGuid>0x\w+)\s+\d+\s+(?P<RPort>\d+)\[\s+\]\s*\"\s*(?P<RName>[\w\-_ ]+).*|(?:()().*))$'

        for value in self.merged_info_values :
            self.gauge[f'{value}'] = {
                    'help': f'Device/Cable current {value}.'
            }
        
        self.counter_info = {
            'LinkDownedCounterExt': {
                'bits': 8,
            },
            'SymbolErrorCounterExt': {
                'bits': 16,
            },
            'PortXmitConstraintErrorsExt': {
                'bits': 16,
            },
            'PortSwLifetimeLimitDiscards': {
                'bits': 16,
            },
            'PortXmitDiscardsExt': {
                'bits': 16,
            },
            'PortSwHOQLifetimeLimitDiscards': {
                'bits': 16,
            },
            'PortXmitWaitExt': {
                'bits': 64,
            },
            'PortXmitDataExtended': {
                'bits': 64,
            },
            'PortRcvDataExtended': {
                'bits': 64,
            },
            'PortXmitPktsExtended': {
                'bits': 64,
            },
            'PortRcvPktsExtended': {
                'bits': 64,
            },
            'PortRcvErrorsExt': {
                'bits': 16,
            },
            'PortUnicastXmitPkts': {
                'bits': 64,
            },
            'PortUnicastRcvPkts': {
                'bits': 64,
            },
            'PortMulticastXmitPkts': {
                'bits': 64,
            },
            'PortMulticastRcvPkts': {
                'bits': 64,
            },
            'PortBufferOverrunErrors': {
                'bits': 16,
            },
            'PortLocalPhysicalErrors': {
                'bits': 16,
            },
            'PortRcvRemotePhysicalErrorsExt': {
                'bits': 16,
            },
            'PortInactiveDiscards': {
                'bits': 32, #change from 16
            },
            'PortDLIDMappingErrors': {
                'bits': 32, #change from 16
            },
            'LinkErrorRecoveryCounterExt': {
                'bits': 8,
            },
            'LocalLinkIntegrityErrorsExt': {
                'bits': 4,
            },
            'VL15DroppedExt': {
                'bits': 16,
            },
            'PortNeighborMTUDiscards': {
                'bits': 16,
            },
            'PortRcvConstraintErrorsExt': {
                'bits': 16,
            },
            'ExcessiveBufferOverrunErrorsExt': {
                'bits': 16,
            }
        }

    def init_metrics(self):

        for value in self.gauge:
            self.metrics[value] = GaugeMetricFamily(
                'infiniband_' + value.lower(),
                self.gauge[value]['help'],
                labels = self.merged_info_labels
            )

        for value in self.power_info:
            self.metrics[value] =GaugeMetricFamily(
                'infiniband_' + value.lower(),
                self.power_info[value]['help'],
                labels = [
                    'NodeGuid',
                    'PSUIndex',
                    'NodeName'
                ]
            )
        
        for value in self.fan_info:
            self.metrics[value] = GaugeMetricFamily(
                'infiniband_' + value.lower(),
                self.fan_info[value]['help'],
                labels = [
                    'NodeGuid',
                    'FanIndex',
                    'NodeName'
                ]
            )
        
        for value in self.device_temp:
            self.metrics[value] = GaugeMetricFamily(
                'infiniband_' + value.lower(),
                self.device_temp[value]['help'],
                labels = [
                'NodeGuid',
                'NodeName'
                ]
            )

        for link_name in self.link_info:
            self.metrics[link_name] = GaugeMetricFamily(
                'infiniband_' + link_name.lower(),
                self.link_info[link_name]['help'],
                labels=[
                    'NodeName',
                    'NodeGuid',
                    'PortNumber',
                    'state',
                    'physical_state',
                    'RemoteGuid',
                    'RemotePort',
                    'RemoteName'
                ]
            )

    def chunks(self, x, n):
        for i in range(0, len(x), n):
            yield x[i:i + n]

    def reset_counter(self, guid, port, reason):
        name = guid
        if self.node_name_map :
                with open(self.node_name_map, 'r') as file:
                    datas = file.readlines()
                    for data in datas:
                        if guid in data:
                            name = data.split(" ")[1].rstrip("\n")
        if self.can_reset_counter:
            logging.info('Reseting counters on %s port %s, due to %s',  # noqa: E501
                         name,
                         port,
                         reason)
            process = subprocess.Popen(['perfquery', '-R', '-G', guid, port],
                                       stdout=subprocess.PIPE)
            stdtout = process.communicate()
        else:
            logging.warning('Counters on %s port %s due to %s is overload',  # noqa: E501
                            name,
                            port,
                            reason)

    def parse_state(self, item):

        try :
            port = f"{int(item[2]):02}"
        except ValueError:
            logging.error(f"The port given is not an int : {item[2]}")
            port = "Unknown"

        try :
            rport = f"{int(item[6]):02}"
        except TypeError :
            rport = "Unknown"
        except ValueError:
            logging.error(f"The port given is neither null or an int : {item[6]}")
            rport = "Unknown"

            
        for link in self.link_info:
            label_values = [
                item[1], #local_guid
                item[0], #local_name
                port, #local_port
                item[3], #state
                item[4], #physical_state
                item[5] or "Unknown", #remote_gu id 
                rport, #remote_port
                item[7] or "Unknown"] #remote_name

            self.metrics[link].add_metric(label_values, 1 if (item[3] == 'Active' and item[4] == 'LinkUp') else 0)

    def process_state(self, item):

        if not isinstance(item, list):
            raise RuntimeError('Wrong data type passed for item: {}'.format(type(item)))

        if len(item) != 11:
            raise ParsingError('Item data incomplete:\n{}'.format(item[0]))

        self.parse_state(item)

    def data_link(self):

        for cable_info in self.info_merged :
            name = ""
            remotename = ""
            remoteguid, remoteport = self.link_connexion(cable_info['nodeguid'], cable_info['portnum'])
            cable_info['remoteport'] = f"{int(remoteport):02}"
            cable_info['portnumber'] = f"{int(cable_info['portnumber']):02}"
            cable_info['remoteguid'] = remoteguid
            if self.node_name_map :
                with open(self.node_name_map, 'r') as file:
                    datas = file.readlines()
                    for data in datas:
                        if cable_info['nodeguid'] in data:
                            name = data.split(" ")[1].rstrip("\n")
                        if cable_info['remoteguid'] in data and cable_info['remoteguid'] != "":
                            remotename = data.split(" ")[1].rstrip("\n")
            cable_info['nodename'] = name
            cable_info['remotename'] = remotename
            self.label_values = []
            self.value_values = 0
            for label in self.merged_info_labels:
                self.label_values.append(cable_info[label.lower()])
            for value in self.gauge:
                try :
                    self.value_values = int(cable_info[value.lower()].rstrip('c'))
                    if value in self.counter_info:
                        if self.value_values >= 2 ** (self.counter_info[value]['bits']-1):
                            self.reset_counter(cable_info['nodeguid'], cable_info['portnum'], value)
                except ValueError:
                    logging.debug(f'The value {value} is not an int.')

                self.metrics[value].add_metric(self.label_values, self.value_values)

    def temp_link(self):
        for temp_info in self.temp_sensing_filtered :
            name = ""
            if self.node_name_map :
                with open(self.node_name_map, 'r') as file:
                    datas = file.readlines()
                    for data in datas:
                        if temp_info['nodeguid'] in data:
                            name = data.split(" ")[1].rstrip("\n")
            temp_info['nodename'] = name
            self.label_values = []
            self.value_values = 0
            for label in self.temp_sensing_labels:
                self.label_values.append(temp_info[label.lower()])
            for value in self.device_temp:
                label_values = self.label_values
                try :
                    self.value_values = int(temp_info['currenttemperature'])
                except ValueError:
                    logging.error(f'The value {value} is not an int.')

                self.metrics[value].add_metric(label_values, self.value_values)

    def fan_link(self):
        for fan_info in self.fan_info_filtered :
            name = ""
            fan_info['sensorindex'] = f"{int(fan_info['sensorindex']):02}"
            if self.node_name_map :
                with open(self.node_name_map, 'r') as file:
                    datas = file.readlines()
                    for data in datas:
                        if fan_info['nodeguid'] in data:
                            name = data.split(" ")[1].rstrip("\n")
            fan_info['nodename'] = name
            self.label_values = []
            self.value_values = 0
            for label in self.fan_info_labels:
                self.label_values.append(fan_info[label.lower()])
            for value in self.fan_info:
                label_values = self.label_values
                try :
                    self.value_values = int(fan_info['fanspeed'])
                except ValueError:
                    logging.error(f'The value {value} is not an int.')

                self.metrics[value].add_metric(label_values, self.value_values)

    def power_link(self):
        for power_info in self.power_info_filtered :
            name = ""
            power_info['psuindex'] = f"{int(power_info['psuindex']):02}"
            if self.node_name_map :
                with open(self.node_name_map, 'r') as file:
                    datas = file.readlines()
                    for data in datas:
                        if power_info['nodeguid'] in data:
                            name = data.split(" ")[1].rstrip("\n")
            power_info['nodename'] = name
            self.label_values = []
            self.value_values = 0
            for label in self.power_info_labels:
                self.label_values.append(power_info[label.lower()])
            for value in self.power_info:
                label_values = self.label_values
                try :
                    self.value_values = 1 if power_info['dcstate'] == 'ok' else 0
                except ValueError:
                    logging.error(f'The value {value} is not an int.')

                self.metrics[value].add_metric(label_values, self.value_values)

    def collect(self):

        logging.debug('Start of collection cycle')

        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        print(f'{current_time}Scrape start')
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

        self.get_csv_value()

        self.init_metrics()

        self.data_link()
        
        self.temp_link()

        self.fan_link()

        self.power_link()

        for value in self.gauge:
            yield self.metrics[value]

        for value in self.device_temp:
            yield self.metrics[value]

        for value in self.fan_info:
            yield self.metrics[value]

        for value in self.power_info:
            yield self.metrics[value]
        
        iblinkinfo_stdout = ""
        iblinkinfo_args = [
            'iblinkinfo',
            '--verbose',
            '--line']
        if self.node_name_map:
            iblinkinfo_args.append('--node-name-map')
            iblinkinfo_args.append(self.node_name_map)
        process = subprocess.Popen(iblinkinfo_args,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        process_stdout, process_stderr = process.communicate()
        iblinkinfo_stdout = process_stdout.decode("utf-8")
        if process_stderr:
            iblinkinfo_stderr = process_stderr.decode("utf-8")
            
            logging.warning("STDERR output retrieved from iblinkinfo:\n%s",
                iblinkinfo_stderr)
            self.scrape_with_errors = True

        content = re.split(self.link_info_regex,
                           iblinkinfo_stdout,
                           flags=re.MULTILINE)
        try:

            if not content:
                raise ParsingError('Input content is empty.')

            if not isinstance(content, list):
                raise RuntimeError('Input content should be a list.')

            # Drop first line that is empty on successful regex split():
            if content[0] == '':
                del content[0]
            else:
                raise ParsingError('Inconsistent input content detected:\n{}'.format(content[0]))

            input_data_chunks = self.chunks(content, 11)

            for data_chunk in input_data_chunks:
                self.process_state(data_chunk)

            for link_name in self.link_info:
                yield self.metrics[link_name]

        except ParsingError as e:
            logging.error(e)
            self.scrape_with_errors = True

        scrape_duration.add_metric([], time.time() - scrape_start)
        yield scrape_duration

        if self.scrape_with_errors:
            scrape_ok.add_metric([], 0)
        else:
            scrape_ok.add_metric([], 1)
        yield scrape_ok

        logging.debug('End of collection cycle')
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        print(f'{current_time}Scrape end in {scrape_duration}')



class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass

def main():
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
        help='Node name map used by ibqueryerrors.')
    parser.add_argument(
        '--can-reset-counter',
        dest='can_reset_counter',
        help='Will reset counter as required when maxed out.',
        action='store_true')


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
    
    if args.can_reset_counter:
        logging.debug('can_reset_counter provided in args')
        can_reset_counter = True
    else:
        logging.debug('Counters will not reset automatically')
        can_reset_counter = False


    app = make_wsgi_app(InfinibandCollector(node_name_map=node_name_map, csv_file_input=csv_file_input, can_reset_counter=can_reset_counter))
    httpd = make_server('', args.port, app,
                        handler_class=NoLoggingWSGIRequestHandler)
    httpd.serve_forever()

if __name__ == '__main__':
    main()