import os, sys, getopt, string, glob, json

lib_name = ""

def usage():
	print 'Usage: python ' + sys.argv[0] + ' -l glib'
	
if len(sys.argv) == 1:
	usage()
	exit(1)
	
# parse command line options and get lib_name
opts, args = getopt.getopt(sys.argv[1:], 'l:h')
for op, value in opts:
	if op == '-l':
		lib_name = value
	if op == '-h':
		usage()
		exit(0)
		
# get the version number from a given file
def get_version_number(lib_tar_file):
	number_str = lib_tar_file[lib_tar_file.rfind('-')+1:
		lib_tar_file.find('.tar')]
	if 'jpeg' in lib_tar_file:
		number_str = lib_tar_file[lib_tar_file.find('src.v')+5:
		lib_tar_file.find('.tar')]
	return number_str

# sort tar files
def get_sorted_list(lib_tar_list):

	# change gmp-5.1.0a.tar.xz, openssl-1.1.0f.tar.gz ...
	# into gmp-5.1.0.97.tar.xz, openssl-1.1.0.102.tar.gz ...
	for i in range(len(lib_tar_list)):
		check_pos = lib_tar_list[i].find('.tar')-1
		mchar = lib_tar_list[i][check_pos]
		if not mchar.isalpha():
			continue
		lib_tar_list[i] = lib_tar_list[i].replace(mchar+'.tar', 
			'.'+str(ord(mchar))+'.tar')
			
	sorted_list = sorted(lib_tar_list, 
		key=lambda s: tuple(map(int, (get_version_number(s).split(".")))))
	
	# change gmp-5.1.0.97.tar.xz, openssl-1.1.0.102.tar.gz ...
	# into gmp-5.1.0a.tar.xz, openssl-1.1.0f.tar.gz ...
	for i in range(len(sorted_list)):
		file_name = sorted_list[i][:sorted_list[i].find('.tar')]
		last_num = file_name[file_name.rfind('.')+1:]
		try:
			mchar = chr(int(last_num))
			if not mchar.isalpha():
				continue
			if not mchar.islower():
				continue
			sorted_list[i] = sorted_list[i].replace('.'+str(ord(mchar))+'.tar', 
				mchar+'.tar')
		except:
			pass
	return sorted_list

# generate version list
def generate_version_list(lib_tar_list):
	version_list = []
	for lib_tar_file in lib_tar_list:
		cur_version_dict = {}
		number_str = get_version_number(lib_tar_file)
		cur_version_dict['Number'] = number_str
		cur_version_dict['Source'] = 'library/'+lib_name+'/'+lib_tar_file
		cur_version_dict['Installed'] = 'build/'+lib_name+'/'+number_str
		version_list.append(cur_version_dict)
	return version_list

# collect tar files and sort
lib_tar_list = []
for lib_tar_file in glob.glob('library/'+lib_name+'/*'):
	lib_tar_list.append(os.path.basename(lib_tar_file))
lib_tar_list = get_sorted_list(lib_tar_list)

# generate json files (both asc and desc order)
os.system('mkdir -p json')
json_asc_file = open('json/' + lib_name+'-asc.json', "w")
json_desc_file = open('json/' + lib_name+'-desc.json', "w")

version_asc_list = generate_version_list(lib_tar_list)
version_desc_list = generate_version_list(reversed(lib_tar_list))

json_asc_file.write(json.dumps(
	{'Name':lib_name+'-asc','Versions':version_asc_list}, indent=4))
json_asc_file.write('\n')
json_desc_file.write(json.dumps(
	{'Name':lib_name+'-desc','Versions':version_desc_list}, indent=4))
json_desc_file.write('\n')
	
json_asc_file.close()
json_desc_file.close()

