#!/usr/bin/env python

import json
import shutil
import os
import glob
import sys

#pathname = os.path.dirname(sys.argv[0])        
#print('full path =', os.path.abspath(pathname)) 

dvb2ip_path='/etc/dvb2ip/'
dvblast_path=dvb2ip_path + 'dvblast/'
ffmpeg_path=dvb2ip_path + 'ffmpeg/'
udpxy_path=dvb2ip_path + 'udpxy/'
dirs=[dvblast_path, ffmpeg_path, udpxy_path]

## Stop service
os.system("service dvb2ip stop > /dev/null 2>&1")

## Remove old config files and links 
for dir in dirs:
    for file in glob.glob(dir + '/dvb2ip_*.conf') + glob.glob(dir + '/*.cfg'):
        os.remove(file)

for link in glob.glob("/etc/init/dvb2ip*"):
    os.remove(link)
####

#Load config file
with open(dvb2ip_path + 'dvb2ip.json', 'r') as f:
    config = json.load(f)

#Read ffmpeg pattern files
with open(ffmpeg_path + 'dvb2ip_ffmpeg_mpegts.pattern', 'r') as ffmpeg_mpegts_pattern_file:
    data_ffmpeg_mpegts_pattern = ffmpeg_mpegts_pattern_file.read()
with open(ffmpeg_path + 'dvb2ip_ffmpeg_hls.pattern', 'r') as ffmpeg_hls_pattern_file:
    data_ffmpeg_hls_pattern = ffmpeg_hls_pattern_file.read()

for adapter in config['adapters']:
    ## Create init file for each adaper
    #Copy pattern file for each adapter
    shutil.copyfile(dvblast_path + 'dvb2ip_dvblast.pattern', dvblast_path + 'dvb2ip_dvblast' + adapter + '.conf')

    #Create substitution dictionary
    repls = {'@@ADAPTER@@': adapter, '@@FREQUENCY@@': config['adapters'][adapter]['frequency'], '@@DISEQC@@': config['adapters'][adapter]['diseqc'], '@@POLARITY@@': config['adapters'][adapter]['polarity'], '@@SYMBOLRATE@@': config['adapters'][adapter]['symbol_rate']}

    #Read the adapter file
    with open(dvblast_path + 'dvb2ip_dvblast' + adapter + '.conf', 'r') as dvblast_file:
        data = dvblast_file.read()

    #Replace variables
    for key, value in repls.items():
        data = data.replace(key, value)

    #Write new data to adapter file
    with open(dvblast_path + 'dvb2ip_dvblast' + adapter + '.conf', 'w') as dvblast_file:
        dvblast_file.write(data)

    ## Create config files for each service 
    # dvblast adapter config file
    dvblast_adapter_file = open(dvblast_path + adapter + '.cfg', 'w')

    for service in config['adapters'][adapter]['services']:

        # ffmpeg config file
        #ffmpeg_file = open(ffmpeg_path + 'dvb2ip_ffmpeg_' + service['protocol'] + '_' + adapter + '_' + service['sid'] + '.conf', 'w')
	# JMM
	ffmpeg_file = open(ffmpeg_path + 'dvb2ip_ffmpeg' + adapter + '_' + service['sid'] + '.conf', 'w')
        print >> ffmpeg_file, 'description "dvb2ip-ffmpeg' + adapter + '"\n\nstart on started dvb2ip_dvblast' + adapter + '\nstop on (stopping dvb2ip_dvblast' + adapter + ' or runlevel [016])\n\nconsole log\nrespawn\n'
    	# JMM:
	print >> ffmpeg_file, 'pre-start script\n    crop=`timeout 10 ffmpeg -t 1 -i udp://@' + service['ip']+ ':' + service['port_dvblast'] + ' -vf cropdetect -f null - 2>&1 | awk \'/crop/ {print $NF}\'  | grep crop | uniq -D|tail -n 1`'
	print >> ffmpeg_file, '    if [ "$crop" ]; then\n\techo "crop=\\\"-vf $crop\\\"" > "/tmp/$UPSTART_JOB"\n    else\n\techo "crop=\\\"\\\"" > "/tmp/$UPSTART_JOB"\n    fi\nend script\n'
	print >> ffmpeg_file, 'script\n    . "/tmp/$UPSTART_JOB"'
        # /JMM

        #Write dvblast service file
        print >> dvblast_adapter_file, service['ip'] + ':' + service['port_dvblast'] + '@' + service['ip_lo'] + '/udp 1 ' + service['sid']

        #Create substitution dictionary for ffmpeg
        repls = {'@@IP@@': service['ip'], '@@PORT_DVBLAST@@': service['port_dvblast'], '@@PORT_FFMPEG@@': service['port_ffmpeg'], '@@PATH_HLS@@': service['path_hls'], '@@ADAPTER@@': adapter, '@@SID@@': service['sid']}

        #Replace variables
	if service['protocol'] == 'hls':
	    data = data_ffmpeg_hls_pattern
            os.system("mkdir -p /var/www/html/" + service['path_hls'])
	else:
	    data = data_ffmpeg_mpegts_pattern

        for key, value in repls.items():
            data = data.replace(key, value)

	#Write ffmpeg config file
        ffmpeg_file.write(data)

        if service['protocol'] == 'hls':
            print >> ffmpeg_file, 'end script\n\npost-stop script\n\trm /var/www/html/' + service['path_hls'] + '/* > /dev/null 2>&1\nend script'
        else:
            print >> ffmpeg_file, 'end script'

        ffmpeg_file.close()

    dvblast_adapter_file.close()


## UDPXY
#Copy pattern file for udpxy
shutil.copyfile(udpxy_path + 'dvb2ip_udpxy.pattern', udpxy_path + 'dvb2ip_udpxy.conf')

#Read udpxy config file
with open(udpxy_path + 'dvb2ip_udpxy.conf', 'r') as udpxy_file:
    data = udpxy_file.read()

#Create substitution dictionary
repls = {'@@PORT@@': config['udpxy']['port'], '@@CLIENTS@@': config['udpxy']['clients']}

#Replace variables
for key, value in repls.items():
    data = data.replace(key, value)

#Write new data to adapter file
with open(udpxy_path + 'dvb2ip_udpxy.conf', 'w') as udpxy_file:
    udpxy_file.write(data)





## Create links to config files         
for dir in dirs:
    for file in os.listdir(dir):
        if file.endswith(".conf"):
#            pass
            os.symlink(dir + file, '/etc/init/' + file)

os.symlink(dvb2ip_path + 'dvb2ip.conf', '/etc/init/dvb2ip.conf')

## Reload Upstart configuration                 
os.system("initctl reload-configuration")




