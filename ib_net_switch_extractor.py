import re
import csv
import collections
import functools
import enum
import dataclasses
import argparse
import pandas as pd

class Device_type (enum.Enum):
	LEAF_SWITCH = 0
	SPINE_SWITCH = 1
	ECS_SWITCH = 2
	IPMI_SWITCH = 3
	STORAGE_SWITCH = 4
	SODIN = 5
	SOL40_SERVER = 6
	EB_SERVER = 7
	STORAGE_SERVER = 8
	JBOD_ENCLOSURE = 9
	UNKNOWN = 10

@dataclasses.dataclass(kw_only=True)
class Rack_device:
	rack: int = 0
	container: int = 0
	name: str = ''
	device_type: Device_type 
#device_type: Device_type = dataclass.field(init=False)

#	def __post_init__(self):


@dataclasses.dataclass(kw_only=True)
class Port:
	remote_guid: str = ''
	remote_host: str = ''
	remote_port: int = 0
	local_port: int = 0

@dataclasses.dataclass(kw_only=True)
class Switch:
	guid: str = ''
	radix: int = 0
	ports: dict[int, Port] = dataclasses.field(default_factory=dict)
	host_ports : list[int] = dataclasses.field(default_factory=list)
	switch_ports : list[int] = dataclasses.field(default_factory=list)

	def is_leaf(self) -> bool:
		return len(self.host_ports) != 0

	def is_spine(self) -> bool:
		return not self.is_leaf()


class Switch_parser :
	_header_re = re.compile('Switch\s+(?P<radix>[0-9]+)\s+"(?P<node_type>[HS])-(?P<guid>[a-f0-9]+)"')
	_port_re = re.compile('\[(?P<port>[0-9]+)\]\s+"(?P<node_type>[HS])-(?P<guid>[a-f0-9]+)"\[(?P<remote_port>[0-9]+)\].+\#\s+"(?P<remote_host>[A-Za-z0-9]+)')

	class Status (enum.Enum):
		HEADER = 0
		PORTS = 1

	def __init__(self, net_discover_file_name):
		self._file = open(net_discover_file_name, 'r')
		self._status = self.Status(Switch_parser.Status.HEADER)
		self._curr_sw = None
# spine switches are connected only to switches 
		self.spine_switches = []
# spine switches are connected only to switches and nodes
		self.leaf_switches = []

	
	def parse(self):
		for line in self._file.readlines():
			self._parse_line(line)
	
	def _parse_line(self, line: str):
		if (self._status == Switch_parser.Status.HEADER):
			re_match = self._match_header(line)
			if(re_match != None):
				self._parse_header(re_match)
		elif (self._status == Switch_parser.Status.PORTS):
			re_match = self._match_port(line)
			if(re_match != None):
				self._parse_port(re_match)

	def _parse_header(self, re_match):
		if(re_match.group('node_type') == 'S'):
			self._curr_sw = Switch(guid = re_match.group('guid'),
						radix=int(re_match.group('radix'))-1)
			self._status = Switch_parser.Status.PORTS

	def _parse_port(self, re_match):
		port_num = int(re_match.group('port'))
		port = Port(remote_guid=re_match.group('guid'),
				remote_port=int(re_match.group('remote_port')),
				local_port=int(re_match.group('port')),
				remote_host=re_match.group('remote_host'))
		self._curr_sw.ports[port_num] = port
		if(port_num <= self._curr_sw.radix):
			if(re_match.group('node_type') == 'S'):
				port.remote_host='switch'
				self._curr_sw.switch_ports.append(port)
			elif(re_match.group('node_type') == 'H'):
				self._curr_sw.host_ports.append(port)
		# last port reached close the switch parsing
		else:
			if (self._curr_sw.is_leaf()):
				self.leaf_switches.append(self._curr_sw)
			else:
				self.spine_switches.append(self._curr_sw)

			self._status = Switch_parser.Status.HEADER
			
	def _match_header(self,line):
		return Switch_parser._header_re.match(line)

	def _match_port(self,line):
		return Switch_parser._port_re.match(line)

# def match_funct(val, regex) :
# matches = [(dev_type, regex.search(str(val))) 
# for dev_type, regex in regex_list.items()]
# matches[0] = (matches[0], [matches[0].group()) if matches[0] else None
# return functools.reduce(lambda a, b:  b.group() if b else a, matches)
# return re_match.group() if re_match != None else val

class DC_parser:
	dev_regex = {}

	dev_regex[Device_type.LEAF_SWITCH] = re.compile('sw-s[0-9]r[0-9][0-9]-b1', re.IGNORECASE)
	dev_regex[Device_type.SPINE_SWITCH] = re.compile('sw-eb-[0-9][0-9]', re.IGNORECASE)
	dev_regex[Device_type.ECS_SWITCH] = re.compile('sw-s[0-9]r[0-9][0-9]-0[0-9]', re.IGNORECASE)
	dev_regex[Device_type.IPMI_SWITCH] = re.compile('sw-s[0-9]r[0-9][0-9]-m[0-9]', re.IGNORECASE)
	dev_regex[Device_type.STORAGE_SWITCH] = re.compile('sw-s[0-9]r[0-9][0-9]-d[0-9]', re.IGNORECASE)
	dev_regex[Device_type.SODIN] = re.compile('sodin[0-9][0-9]', re.IGNORECASE)
	dev_regex[Device_type.SOL40_SERVER] = re.compile('[a-z][a-z12]fe[0-9][0-9]', re.IGNORECASE)
	dev_regex[Device_type.EB_SERVER] = re.compile('[a-z][a-z12]eb[0-9][0-9]', re.IGNORECASE)
	dev_regex[Device_type.STORAGE_SERVER] = re.compile('bbdd[0-9][0-9]', re.IGNORECASE)
	dev_regex[Device_type.JBOD_ENCLOSURE] = re.compile('bbjbod[0-9][0-9]', re.IGNORECASE)

	def __init__(self):
		self.devices_list = []
		self.device_rack_unit_dict = collections.defaultdict(list)
		self.device_type_dict = {}


	def parse_container(self, csv_file_name, container):
		with open(csv_file_name, 'r') as csv_file:
			csv_reader = csv.DictReader(csv_file)
			for line in csv_reader:

				for dev_type, regex in DC_parser.dev_regex.items():
					device_line = {rack : regex.search(elem) for rack, elem in line.items()}
					tmp_dev_list = [Rack_device(rack=rack, container=container, name=re_match.group(),device_type=dev_type) for rack, re_match in device_line.items() if re_match != None]
					self.devices_list.extend(tmp_dev_list)

		self._update_geo_information()
	

	def _update_geo_information(self):
		# TODO improve this part
		for dev in self.devices_list:
			self.device_rack_unit_dict[(dev.container, dev.rack)].append(dev)

		for dev_type in Device_type:
			self.device_type_dict[dev_type] = [dev for dev in self.devices_list if dev.device_type == dev_type]






def match_leaf_switch_name(switch_list, dc_devs):
	for switch in switch_list:
		device = next((x for x in dc_devs.device_type_dict[Device_type.EB_SERVER] if switch.host_ports[0].remote_host.lower() == x.name.lower() ))
		

		switch_dev=next((x for x in dc_devs.device_rack_unit_dict[device.container, device.rack] if x.device_type == Device_type.LEAF_SWITCH))
		print(f'0x{switch.guid}', switch_dev.name)



def match_spine_switch_name(leaf_switch, dc_devs):
	guid_list = [elem.remote_guid for elem in sorted(leaf_switch.switch_ports, key = lambda a : a.local_port)][::2]
	names_list = sorted([sw.name for sw in dc_devs.device_type_dict[Device_type.SPINE_SWITCH]])
	for guid, name in zip(guid_list,names_list):
		print(f'0x{guid}', name)
		


#TODO @tgalpin write a proper main :)
def main():
	pippo = Switch_parser('net_dis.txt')
	pippo.parse()

	pappo = DC_parser()

	pappo.parse_container('/home/flavio/Downloads/LHCb data center - IT4 40P-200G-3 Tell40(1).csv',4)
	pappo.parse_container('/home/flavio/Downloads/LHCb data center - IT3 40P-200G-3 Tell40(1).csv',3)

# print(pappo.devices_list)
# print(pappo.device_type_dict[Device_type.LEAF_SWITCH])
# print(pappo.device_rack_unit_dict)

	match_leaf_switch_name(pippo.leaf_switches,pappo)
	match_spine_switch_name(pippo.leaf_switches[0],pappo)



if __name__ == '__main__':
	main()
