# Cables-info-exporter

## Update your node-name-map :

Use the guid-to-name.y script to generate the guid_2_name.txt file with can be read by the exporter.
It take 2 argument :
1. The guid - switch link file (sw-node-name-map.txt by default)
2. The verbose level (none or full)

```python3 guid-to-name.py [--node-name-map = ./sw-name-map.txt] [--verbose]```


## Generate your own ibdiagnet.db_csv file :

You can choose to give a defined csv to the exporter, to generate it, you should use the following command :
```ibdiagnet --get_phy_info --disable_output default --enable_output db_csv```


## Start the exporter :

The exporter will export request data onto a webpage, in a pro;etheus format. Default port is 9685.

```python3 info-exporter.py [--port = 9685] [--node-name-map] [--csv-file-input = /var/tmp/ibdiagnet2/ibdiagnet2.db_csv] [--verbose] [--can-reset-counter]```

where :

- node-name-map is the guid_2_name.txt file like generated before
- csv-file-input is the file to parse if not the default one
- can reset counter allow the script to reset the counters of a port when one of those reach the top value