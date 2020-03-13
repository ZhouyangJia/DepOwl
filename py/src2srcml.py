import os, sys
import glob

for tar_file in glob.glob('sources/*'):
	if '.xml' in tar_file:
		continue
	if os.path.exists(tar_file+'.xml'):
		continue
	os.system('mkdir -p xml/')
	xml_file = 'xml' + tar_file[7:] + '.xml'
	cmd = 'srcml '+tar_file+' -o '+xml_file
	print cmd
	os.system(cmd)