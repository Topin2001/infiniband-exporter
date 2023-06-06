#/bin/sh

/usr/bin/python3 /home/tgalpin/running/info-exporter/info-exporter.py --port 9686 --node-name-map /home/tgalpin/running/info-exporter/guid_2_name.txt --can-reset-counter

/usr/bin/python3 /home/tgalpin/running/info-exporter/info-exporter.py --phy --link_state --asic_temp --node-name-map /home/tgalpin/running/info-exporter/guid_2_name.txt
