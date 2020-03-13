import os, sys, string
import glob
import cxxfilt
import urllib
import subprocess
import pandas as pd
import sqlite3
from pandas import ExcelWriter
from pandas import ExcelFile
#import cProfile

pkg_lib_dict = {
	"libglib2.0-0":"glib",
	"zlib1g":"zlib",
	"libqt5core5a":"qtbase",
	"libgmp10":"gmp",
	"libx11-6":"x11",
	"libqt5gui5":"qtbase",
	"libqt5widgets5":"qtbase",
	"libgtk-3-0":"gtk3",
	"libgdk-pixbuf2.0-0":"gdk",
	"libcairo2":"cairo",
	"libssl1.1":"ssl",
	"libpango-1.0-0":"pango",
	"libxml2":"xml2",
	"libtinfo6":"ncurses",
	"libpng16-16":"png",
	"libkf5i18n5":"ki18n",
	"libkf5coreaddons5":"kcoreaddons",
	"libqt5network5":"qtbase",
	"libmpfr6":"mpfr",
	"libkf5configcore5":"kconfig",
	"libqt5dbus5":"qtbase",
	"libjpeg8":"jpeg",
	"dconf-gsettings-backend":"dconf",
	"libmpc3":"mpc",
	"libxext6":"xext",
	"libisl21":"isl",
	"libpangocairo-1.0-0":"pango",
	"libsqlite3-0":"sqlite",
	"libkf5widgetsaddons5":"kwidgetsaddons",
	"libqt5xml5":"qtbase",
	"libsdl1.2debian":"sdl",
	"libasound2":"alsa"
}

soname_pkg_dict = {
	"libgio-2.0.so.0":"libglib2.0-0",
	"libglib-2.0.so.0":"libglib2.0-0",
	"libgmodule-2.0.so.0":"libglib2.0-0",
	"libgobject-2.0.so.0":"libglib2.0-0",
	"libgthread-2.0.so.0":"libglib2.0-0",
	"libz.so.1":"zlib1g",
	"libQt5Core.so.5":"libqt5core5a",
	"libgmp.so.10":"libgmp10",
	"libX11.so.6":"libx11-6",
	"libQt5Gui.so.5":"libqt5gui5",
	"libQt5XcbQpa.so.5":"libqt5gui5",
	"libQt5EglFsKmsSupport.so.5":"libqt5gui5",
	"libQt5EglFSDeviceIntegration.so.5":"libqt5gui5",
	"libQt5Widgets.so.5":"libqt5widgets5",
	"libgdk-3.so.0":"libgtk-3-0",
	"libgtk-3.so.0":"libgtk-3-0",
	"libgdk_pixbuf-2.0.so.0":"libgdk-pixbuf2.0-0",
	"libgdk_pixbuf_xlib-2.0.so.0":"libgdk-pixbuf2.0-0",
	"libcairo.so.2":"libcairo2",
	"libssl.so.1.1":"libssl1.1",
	"libcrypto.so.1.1":"libssl1.1",
	"libpango-1.0.so.0":"libpango-1.0-0",
	"libxml2.so.2":"libxml2",
	"libtinfo.so.6":"libtinfo6",
	"libpng16.so.16":"libpng16-16",
	"libKF5I18n.so.5":"libkf5i18n5",
	"libKF5CoreAddons.so.5":"libkf5coreaddons5",
	"libQt5Network.so.5":"libqt5network5",
	"libmpfr.so.6":"libmpfr6",
	"libKF5ConfigCore.so.5":"libkf5configcore5",
	"libQt5DBus.so.5":"libqt5dbus5",
	"libdconfsettings.so":"dconf-gsettings-backend",
	"libmpc.so.3":"libmpc3",
	"libXext.so.6":"libxext6",
	"libisl.so.21":"libisl21",
	"libpangocairo-1.0.so.0":"libpangocairo-1.0-0",
	"libsqlite3.so.0":"libsqlite3-0",
	"libKF5WidgetsAddons.so.5":"libkf5widgetsaddons5",
	"libQt5Xml.so.5":"libqt5xml5",
	"libSDL-1.2.so.0":"libsdl1.2debian",
	"libasound.so.2":"libasound2"
}


#############################################################
##### Read lib_data and build the following data struct #####
#############################################################

# library name-object dictionary:
#	key: name
#	value: object set of the given library name
lib_name_obj_dict = {}

# library object-version dictionary:
#	key: object
#	value: version-pair set of the given library soname
lib_obj_ver_dict = {}

# library version-symbol dictionary:
#	key: (object, old version, new version)
#	value: symbol-version set of the given library version
lib_ver_sym_dict = {}

# library symbol-severity dictionary:
#	key: (object, old version, new version, symbol-version)
#	value: direct/severity/data-type of the given library symbol
lib_sym_severity_dict = {}

# read symbol-change data of libraries and update the above dictionaries
lib_data_file = pd.read_excel('symbols.xlsx', sheet_name='data')
for i in lib_data_file.index:
	lib_data_line = []
	for j in range(len(lib_data_file.columns)):
		columns_key = lib_data_file.columns[j]
		row_data = str(lib_data_file[columns_key][i])
		lib_data_line.append(row_data)

	[lib_name, lib_object, lib_version_old, lib_version_new, lib_direct, 
		lib_data_type, lib_symver, lib_severity] = lib_data_line
	lib_symver = lib_symver.replace('@@', '@')
	
	if not lib_name_obj_dict.has_key(lib_name):
		lib_name_obj_dict[lib_name] = set()
	lib_name_obj_dict[lib_name].add(lib_object)

	if not lib_obj_ver_dict.has_key(lib_object):
		lib_obj_ver_dict[lib_object] = set()
	my_value = (lib_version_old, lib_version_new)
	lib_obj_ver_dict[lib_object].add(my_value)
		
	my_key = (lib_object, lib_version_old, lib_version_new)
	if not lib_ver_sym_dict.has_key(my_key):
		lib_ver_sym_dict[my_key] = set()
	lib_ver_sym_dict[my_key].add(lib_symver)
	
	my_key = (lib_object, lib_version_old, lib_version_new, lib_symver)
	lib_sym_severity_dict[my_key] = [lib_direct, lib_severity, lib_data_type]
	
#print lib_name_obj_dict
#print lib_obj_ver_dict
#print lib_ver_sym_dict
#print lib_sym_severity_dict

########################################################################
##### Read debian package info and build the following data struct #####
########################################################################

# package list, each item contains four package fields: 
#	(name, version, dependencies, url)
pkg_info_list = []

for pkg_file_name in glob.glob('repository/test/*.txt'):
	if 'restricted' in pkg_file_name:
		continue
	if 'multiverse' in pkg_file_name:
		continue

	pkg_file = open(pkg_file_name, 'r')
	pkg_lines = pkg_file.readlines()
	pkg_file.close()

	# keywords of interested fields
	pkg_keywords = ['Package: ', 'Version: ', 'Depends: ', 'Filename: ']
	pkg_fields = [''] * len(pkg_keywords)

	for pkg_line in pkg_lines:
		pkg_line = pkg_line.strip()

		# extract interested fields
		for i in range(len(pkg_keywords)):
			if len(pkg_line) > len(pkg_keywords[i]) and \
				pkg_keywords[i] == pkg_line[:len(pkg_keywords[i])]:
				pkg_fields[i] = pkg_line[len(pkg_keywords[i]):]

		# now we have a breaking line in the package file
		if len(pkg_line) == 0:
			[pkg_name, pkg_version, pkg_deps, pkg_url] = pkg_fields
			pkg_info_list.append((pkg_name, pkg_version, pkg_deps, pkg_url))
			pkg_fields = [''] * len(pkg_keywords)
			
#print pkg_info_list

########################################################################
##### Check whether a debian package is effected by any abi change #####
########################################################################

# count package number
current = 0
total = len(pkg_info_list)

# record symbol set required by current package, avoid redundant analysis
current_symbol_set = set()
has_got_symbol_set = 0

# record soname set required by current package, avoid redundant analysis
current_soname_set = set()
has_got_soname_set = 0

# output to sqlite3 database
conn = sqlite3.connect('depbug.db')
conn.execute('drop table if exists potential_depbug')
stmt = 'create table potential_depbug (ID integer primary key autoincrement, \
	PkgName, PkgVer, Depname, DepVer, LibName, LibObject, PreVer, PostVer, \
	Direction, Severity, Symbol)'
conn.execute(stmt)
conn.execute('create index if not exists id_index on potential_depbug(ID)')

# a datatype may have many affected symbols, only output once to database
has_output_datatype = set()

# utility function: output a potential dep-bug to database
def output_to_database(symbol_info):
	[pkg_name, pkg_version, pkg_dep_name, pkg_dep_version, 
		lib_name, lib_object, lib_version_old, lib_version_new, lib_direct, 
		lib_symver, lib_severity, lib_data_type] = symbol_info
	
	symbol_info = [pkg_name, pkg_version, pkg_dep_name, pkg_dep_version, \
		lib_name, lib_object, lib_version_old, lib_version_new, \
		lib_direct, lib_severity]
	
	# demangle lib_symver
	sym_name = lib_symver
	sym_ver = ''
	if '@' in sym_name:
		[sym_name, sym_ver] = sym_name.split('@')
	try:
		sym_name = cxxfilt.demangle(sym_name)
	except:
		pass
	if sym_ver != '':
		sym_name = sym_name + '@' + sym_ver
	lib_symver = sym_name
		
	# direct symbol
	if lib_data_type == 'None':
		symbol_info.append(lib_symver)
	# indirect symbol
	else:
		symbol_info.append(lib_data_type)
		# first output
		if str(symbol_info) not in has_output_datatype:
			has_output_datatype.add(str(symbol_info))
		# already output
		else:
			symbol_info = []
	if symbol_info == []:
		return
	
	# insert symbol_info into database
	stmt = 'insert into potential_depbug (PkgName, PkgVer, Depname, DepVer, \
		LibName, LibObject, PreVer, PostVer, Direction, Severity, Symbol) \
		values (?,?,?,?,?,?,?,?,?,?,?)'
	conn.execute(stmt, symbol_info)

# utility function: download a given package
def download_package(pkg_url):
	if not os.path.isdir('./packages'):
		os.system('mkdir packages')
	package_file = os.path.basename(pkg_url)
	if os.path.exists('./packages/'+package_file):
		return
	os.chdir('./packages')
	url = 'http://archive.ubuntu.com/ubuntu/' + pkg_url
	try:
		dl_cmd = 'wget -q ' + url
		dl_proc = subprocess.Popen(dl_cmd, shell=True)
		dl_proc.wait()
	except:
		sys.stderr.write('Failed to download ' + url + '\n')
		sys.stderr.flush()
	os.chdir('..')

# utility function: get symbol set required by a given package
def get_symbol_set(pkg_url):
	# download the package
	download_package(pkg_url)
	package_file = './packages/'+os.path.basename(pkg_url)
	
	# extract the package and get symbol list for each file
	dep_symbol_set = set()
	if os.path.isdir('tmp'):
		os.system('sudo rm -rf tmp')
	os.system('mkdir tmp')
	ret = os.system('dpkg -x ' + package_file + ' ./tmp')
	if ret != 0:
		os.system('rm ' + package_file)
		download_package(pkg_url)
		os.system('dpkg -x ' + package_file + ' ./tmp')
	files = []
	for root, dirnames, filenames in os.walk('./tmp'):
		for filename in filenames:
			files.append(os.path.join(root, filename))
	for mfile in files:
		if not 'bin' in mfile:
			if not 'lib' in mfile or not '.so' in mfile:
				continue 
		nm_cmd = 'readelf -Ws ' + mfile + ' 2>/dev/null | grep UND'
		nm_proc = subprocess.Popen(nm_cmd, shell=True, stdout=subprocess.PIPE)
		dep_symbol = nm_proc.communicate()[0]
		dep_symbol_list = dep_symbol.split('\n')
		for dep_symbol in dep_symbol_list:
			if '(' in dep_symbol:
				dep_symbol = dep_symbol.split('(')[0].strip()
			if ' ' in dep_symbol:
				dep_symbol = dep_symbol.split(' ')[-1]
			msymbol = dep_symbol.replace('@@', '@')
			dep_symbol_set.add(msymbol)
	os.system('rm -rf tmp')
	return dep_symbol_set

# utility function: get soname set required by a given package
def get_soname_set(pkg_url):
	# download the dep package
	download_package(pkg_url)
	package_file = './packages/'+os.path.basename(pkg_url)

	# extract the package and get soname list for each file
	dep_soname_set = set()
	if os.path.isdir('tmp'):
		os.system('sudo rm -rf tmp')
	os.system('mkdir tmp')
	ret = os.system('dpkg -x ' + package_file + ' ./tmp')
	if ret != 0:
		os.system('rm ' + package_file)
		download_package(pkg_url)
		os.system('dpkg -x ' + package_file + ' ./tmp')
	files = []
	for root, dirnames, filenames in os.walk('./tmp'):
		for filename in filenames:
			files.append(os.path.join(root, filename))
	for mfile in files:
		if not 'bin' in mfile:
			if not 'lib' in mfile or not '.so' in mfile:
				continue 
		dump_cmd = 'objdump -p '+mfile+' 2>/dev/null | grep NEEDED'
		dump_proc = subprocess.Popen(dump_cmd, shell=True, 
			stdout=subprocess.PIPE)
		dep_soname = dump_proc.communicate()[0]
		dep_soname_list = dep_soname.split('\n')
		for dep_soname in dep_soname_list:
			dep_soname = dep_soname.strip().split(' ')[-1]
			if dep_soname != '':
				dep_soname_set.add(dep_soname)
	os.system('rm -rf tmp')
	return dep_soname_set

### Step 4: match the symbols in current package and lib_data
def match_dep_symbol(pkg_info):
	global current, total, has_got_symbol_set, current_symbol_set
	[pkg_name, pkg_version, pkg_dep_name, pkg_dep_version, lib_name, 
		lib_object, lib_version_old, lib_version_new, pkg_url] = pkg_info
	
	# match dep_symbol and lib_symbol
	if has_got_symbol_set == 0:
		current_symbol_set = get_symbol_set(pkg_url)
		has_got_symbol_set = 1
	my_key = (lib_object, lib_version_old, lib_version_new)
	if not lib_ver_sym_dict.has_key(my_key):
		return
		
	matched_symbol_set = current_symbol_set & lib_ver_sym_dict[my_key]
	for matched_symbol in matched_symbol_set:
		my_key = (lib_object, lib_version_old, lib_version_new, matched_symbol)
		if not lib_sym_severity_dict.has_key(my_key):
			continue
		[lib_direct, lib_severity, lib_data_type] = \
			lib_sym_severity_dict[my_key]
		pkg_info = [pkg_name, pkg_version, pkg_dep_name, pkg_dep_version, 
			lib_name, lib_object, lib_version_old, lib_version_new, lib_direct,
			matched_symbol, lib_severity, lib_data_type]
		print '['+str(current)+'/'+str(total)+'] Step 4', str(pkg_info)
		output_to_database(pkg_info)

### Step 3: compare dependency versions and abi-change versions in lib_data
def match_dep_version(pkg_info):
	global current, total
	[pkg_name, pkg_version, pkg_dep_name, pkg_dep_version, 
		lib_name, lib_object, pkg_url] = pkg_info
	if not lib_obj_ver_dict.has_key(lib_object):
		return
	lib_version_pair_set = lib_obj_ver_dict[lib_object]
		
	# no pkg_dep_version, any version in the lib_data will be matched
	if pkg_dep_version == '':
		for lib_version_pair in lib_version_pair_set:
			(lib_version_old, lib_version_new) = lib_version_pair
			pkg_info = [pkg_name, pkg_version, pkg_dep_name, pkg_dep_version, 
				lib_name, lib_object, lib_version_old, lib_version_new]
			print '['+str(current)+'/'+str(total)+'] Step 3', str(pkg_info)
			match_dep_symbol(pkg_info+[pkg_url])
		return
		
	# skip the fixed dep version
	if not ' ' in pkg_dep_version:
		return
	[pkg_dep_op, pkg_dep_value] = pkg_dep_version.split(' ')
	
	# ignore the epoch value in version number
	if ':' in pkg_dep_value:
		pkg_dep_value = pkg_dep_value.split(':')[-1]
		
	# match pkg_dep_value and lib_version
	cmp_op = ''
	if pkg_dep_op == '>=':
		cmp_op = 'ge'
	elif pkg_dep_op == '>>':
		cmp_op = 'gt'
	elif pkg_dep_op == '<=':
		cmp_op = 'le'
	elif pkg_dep_op == '<<':
		cmp_op = 'lt'
	if cmp_op == '':
		return
	for lib_version_pair in lib_version_pair_set:
		(lib_version_old, lib_version_new) = lib_version_pair
		cmp_old_cmd = 'dpkg --compare-versions ' + lib_version_old + ' ' +\
				cmp_op + ' ' + pkg_dep_value + ' 2>/dev/null'
		cmp_old_proc = subprocess.Popen(cmp_old_cmd, shell=True)
		cmp_old_proc.wait()
		cmp_new_cmd = 'dpkg --compare-versions ' + lib_version_new + ' ' +\
				cmp_op + ' ' + pkg_dep_value + ' 2>/dev/null'
		cmp_new_proc = subprocess.Popen(cmp_new_cmd, shell=True)
		cmp_new_proc.wait()
		if cmp_old_proc.returncode == 0 and cmp_new_proc.returncode == 0:
			pkg_info = [pkg_name, pkg_version, pkg_dep_name, pkg_dep_version, 
				lib_name, lib_object, lib_version_old, lib_version_new]
			print '['+str(current)+'/'+str(total)+'] Step 3', str(pkg_info)
			match_dep_symbol(pkg_info+[pkg_url])
	
### Step 2: if the soname of the dependency matches lib_data
def match_dep_soname(pkg_info):
	global current, total, has_got_soname_set, current_soname_set
	[pkg_name, pkg_version, pkg_dep_name, pkg_dep_version, lib_name, 
		pkg_url] = pkg_info
	if not lib_name_obj_dict.has_key(lib_name):
		return

	# match dep_soname and lib_object, e.g., libfoo.so.1 : libfoo.so.1.2
	if has_got_soname_set == 0:
		current_soname_set = get_soname_set(pkg_url)
		has_got_soname_set = 1
	lib_object_set = lib_name_obj_dict[lib_name]
	for current_soname in current_soname_set:
		if not soname_pkg_dict.has_key(current_soname):
			continue
		if soname_pkg_dict[current_soname] != pkg_dep_name:
			continue
		for lib_object in lib_object_set:
			if current_soname in lib_object:
				pkg_info = [pkg_name, pkg_version, pkg_dep_name, 
					pkg_dep_version, lib_name, lib_object]
				print '['+str(current)+'/'+str(total)+'] Step 2', str(pkg_info)
				match_dep_version(pkg_info+[pkg_url])

### Step 1: if there is a dependency matches lib_data
def match_dep_name(pkg_info):
	global current, total
	[pkg_name, pkg_version, pkg_deps, pkg_url] = pkg_info

	# split the dependency field
	pkg_dep_list = []
	pkg_dep_raw_list = pkg_deps.split(',')
	for pkg_dep in pkg_dep_raw_list:
		pkg_dep = pkg_dep.strip()
		if pkg_dep == '':
			continue
		#in case of 'libfoo | libbar', we split it
		if '|' in pkg_dep:
			raw_deps = pkg_dep.split('|')
			for raw_dep in raw_deps:
				raw_dep = raw_dep.strip()
				pkg_dep_list.append(raw_dep)
		else:
			pkg_dep_list.append(pkg_dep)

	# match pkg_dep_name and lib_name
	for pkg_dep in pkg_dep_list:
		# get name and version for each pkg_dep
		pkg_dep_name = pkg_dep
		pkg_dep_version = ''
		if ' ' in pkg_dep:
			pkg_dep_name = pkg_dep[:pkg_dep.find(' ')].strip()
			pkg_dep_version = pkg_dep[pkg_dep.find(' ')+2:-1].strip()
		
		# if the package depends on one of our target libraries
		if pkg_lib_dict.has_key(pkg_dep_name):
			pkg_info = [pkg_name, pkg_version, pkg_dep_name, 
				pkg_dep_version, pkg_lib_dict[pkg_dep_name]]
			print '['+str(current)+'/'+str(total)+'] Step 1', str(pkg_info)
			match_dep_soname(pkg_info+[pkg_url])

### Step 0: examine each package
def filter_packages(pkg_info_list):
	global current, total, has_got_symbol_set, has_got_soname_set
	for pkg_info in pkg_info_list:
		current += 1
		has_got_symbol_set = 0
		has_got_soname_set = 0
		match_dep_name(pkg_info)
	conn.commit()
	conn.close()

### Entrance
#cProfile.run('filter_packages(pkg_info_list)')
filter_packages(pkg_info_list)
	
