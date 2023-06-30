[![pipeline status](https://gitlab.cern.ch/tgalpin/cables-info-exporter/badges/master/pipeline.svg)](https://gitlab.cern.ch/tgalpin/cables-info-exporter/-/commits/master) 

[![Latest Release](https://gitlab.cern.ch/tgalpin/cables-info-exporter/-/badges/release.svg)](https://gitlab.cern.ch/tgalpin/cables-info-exporter/-/releases)


# Cables-info-exporter

## Update your node-name-map :

Use the name_map_gen script to generate the node_name_map file which can be read by the exporter.

```name_map_gen --csv_file/-c [--net_dis_file/-n] [--output_file/-o = node_name_map.cfg]```

The csv_file is the path to your csv file(s), with the container number separated with ```:```, like as following :

```name_map_gen -c IT3.csv:3 IT4.csv:4```


## Generate your own ibdiagnet.db_csv file :

You can choose to give a defined csv to the exporter, to generate it, you should use the following command :
```ibdiagnet --get_phy_info --disable_output default --enable_output db_csv```


## Start the exporter :

The exporter will export request data onto a webpage, in a pro;etheus format. Default port is 9685.

```python3 info-exporter.py [--port = 9685] [--node-name-map] [--csv-file-input = /var/tmp/ibdiagnet2/ibdiagnet2.db_csv] [--verbose] [--can-reset-counter] [--phy] [--link_state] [--asic_temp]```

where :

- node-name-map is a node_name_map file, like generated before
- csv-file-input is the file to parse if not the default one
- can reset counter allow the script to reset the counters of a port when one of those reach the top value
