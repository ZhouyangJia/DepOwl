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
		
def get_config_cmd(build_system, root_path, build_path):
	config_cmd = ''
	if build_system == 'cmake':
		if lib_name == 'ki18n':
			config_cmd = "CFLAGS='-g -Og' cmake . -DCMAKE_BUILD_TYPE=debug "
			config_cmd+= "-DBUILD_WITH_QTSCRIPT=OFF "
			config_cmd+= "-DBUILD_TESTING=OFF -DCMAKE_INSTALL_PREFIX:PATH="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
		if lib_name == 'kwidgetsaddons':
			config_cmd = "CFLAGS='-g -Og' cmake . -DCMAKE_BUILD_TYPE=debug "
			config_cmd+= "-DBUILD_WITH_QTSCRIPT=OFF -DQt5UiTools_DIR=/usr/lib/x86_64-linux-gnu/cmake/Qt5UiTools "
			config_cmd+= "-DBUILD_TESTING=OFF -DCMAKE_INSTALL_PREFIX:PATH="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
		else:
			config_cmd = "CFLAGS='-g -Og' cmake . -DCMAKE_BUILD_TYPE=debug "
			config_cmd+= "-DBUILD_TESTING=OFF -DCMAKE_INSTALL_PREFIX:PATH="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
	elif build_system == 'configure':
		if lib_name == 'qtbase':
			config_cmd = "./configure -opensource -confirm-license"
			config_cmd+= " -debug --prefix="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
		elif lib_name == 'ncurses':
			config_cmd = "CPPFLAGS='-P' CFLAGS='-g -Og' ./configure "
			config_cmd+= "--with-shared --with-cxx-shared --prefix="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
		elif lib_name == 'sdl':
			config_cmd = "CC='gcc-4.8' CFLAGS='-g -Og' ./configure "
			config_cmd+= "--disable-video-x11 --prefix="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
		elif lib_name == 'mpc':
			config_cmd = "CFLAGS='-g -Og' ./configure \
			--with-mpfr=/home/zhouyang/Desktop/specbug/build/mpfr/3.1.6"
			config_cmd+= " --prefix="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
		elif lib_name == 'cairo':
			config_cmd = "CFLAGS='-g -Og' CC='gcc -g -Og' "
			config_cmd+= "./configure --prefix="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
		else:
			config_cmd = "CFLAGS='-g -Og' ./configure --prefix="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
	elif build_system == 'config':
		config_cmd = "CFLAGS='-g -Og' ./config -d --prefix="
		config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
	elif build_system == 'autogen.sh':
		config_cmd = './autogen.sh >/dev/null 2>&1 && '
		config_cmd+= "CFLAGS='-g' ./configure --prefix="
		config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
	elif build_system == 'meson.build':
		if lib_name == 'dconf':
			config_cmd = "sed '/subdir..test../d' meson.build > meson.buildtmp"
			config_cmd+= " && mv meson.buildtmp meson.build && "
			config_cmd+= "meson _build --buildtype=debug -Dman=false --prefix="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
		if lib_name == 'gtk3':
			config_cmd= "meson _build --buildtype=debug -Dmedia=none --prefix="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
		else:
			config_cmd= "meson _build --buildtype=debug -Dman=false --prefix="
			config_cmd+= root_path + '/' + build_path + ' >/dev/null 2>&1'
	return config_cmd
		
def get_build_cmd(build_system, root_path, build_path):
	build_cmd = ''
	if build_system == 'meson.build':
		build_cmd = 'ninja -C _build install >/dev/null 2>&1'
	else:
		build_cmd = 'make >/dev/null 2>&1 && make install >/dev/null 2>&1'
	return build_cmd
			
json_file = open('json/' + lib_name+'-desc.json', 'r');
json_data = json.load(json_file)
current = 0
total = len(json_data['Versions'])
for version in json_data['Versions']:
	current += 1
	source_path = version['Source']
	version_number = version['Number']
	build_path = version['Installed']
	tar_name = os.path.basename(source_path)
	src_dir = tar_name[:tar_name.find('.tar')]
	if 'jpeg' in src_dir:
		src_dir = src_dir.replace('src.v', '-')
	if 'gmp' in src_dir:
		if src_dir[-1] == 'a':
			src_dir = src_dir[:-1]
	if 'sqlite' in src_dir:
		src_dir = 'sqlite'
	cur_path = os.getcwd()
	# prepare to auto build
	sys.stderr.write('['+str(current)+'/'+str(total)+'] compiling ' 
		+ tar_name + '\n')
	os.system('tar xf ' + source_path)
	os.system('mkdir -p ' + cur_path + '/' + build_path)
	os.chdir(src_dir)
	
	# get config and build commands
	config_cmd = ''
	build_cmd = ''
	if os.path.isfile('CMakeLists.txt'):
		config_cmd = get_config_cmd('cmake', cur_path, build_path)
		build_cmd = get_build_cmd('cmake', cur_path, build_path)
	elif os.path.isfile('configure'):
		config_cmd = get_config_cmd('configure', cur_path, build_path)
		build_cmd = get_build_cmd('configure', cur_path, build_path)
	elif os.path.isfile('config'):
		config_cmd = get_config_cmd('config', cur_path, build_path)
		build_cmd = get_build_cmd('config', cur_path, build_path)
	elif os.path.isfile('autogen.sh'):
		config_cmd = get_config_cmd('autogen.sh', cur_path, build_path)
		build_cmd = get_build_cmd('autogen.sh', cur_path, build_path)
	elif os.path.isfile('meson.build'):
		config_cmd = get_config_cmd('meson.build', cur_path, build_path)
		build_cmd = get_build_cmd('meson.build', cur_path, build_path)

	# config
	sys.stderr.write('    ' + config_cmd + ' ... ')
	ret = os.system(config_cmd)
	if ret == 0:
		sys.stderr.write('Success\n')
	else:
		sys.stderr.write('Failed\n')
	
	# build
	sys.stderr.write('    ' + build_cmd + ' ... ')
	ret = os.system(build_cmd)
	if ret == 0:
		sys.stderr.write('Success\n')
	else:
		sys.stderr.write('Failed\n')
	os.chdir('..')
	os.system('rm -rf ' + src_dir)
	
	
