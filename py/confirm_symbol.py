import glob
import sqlite3
import cxxfilt
import os, sys
from lxml import etree
from lxml.etree import XMLParser, parse
from wordsegment import load, segment
import gc

enum_problem = ['Enum_Member_Value']
field_problem = [
	'Field_Size', 
	'Moved_Field', 
	'Removed_Field', 
	'Removed_Field_And_Size', 
	'Removed_Field_And_Layout', 
	'Removed_Field_And_Layout_And_Size'
]
variable_problem = ['Global_Data_Type_And_Size']
para_problem = [
	'Removed_Parameter', 
	'Parameter_Became_Non_Const', 
	'Parameter_PointerLevel_Decreased', 
	'Parameter_PointerLevel_Increased'
]
ret_problem = [
	'Return_BaseType_And_Size', 
	'Return_Type_Became_Const', 
	'Return_Type_Became_Void'
]
no_problem = ['Symbol_Changed_Parameters']

private_type = [
	'struct ossl_init_settings_st',
	'struct _XDisplay',
	'struct bio_method_st',
	'struct _xmlXPathContext',
	'struct _GObjectClass'
]

conn = sqlite3.connect('depbug.db')
#conn.execute('drop table if exists depbug_confirm')
#stmt = 'create table depbug_confirm (ID integer primary key autoincrement, \
#	PkgName, PkgVer, Depname, DepVer, LibName, LibObject, PreVer, PostVer, \
#	Direction, Severity, Symbol)'
#conn.execute(stmt)
#conn.execute('create index if not exists id_index on depbug_confirm(ID)')

conn.execute('drop table if exists confirmed_depbug')
stmt = 'create table confirmed_depbug (ID integer primary key autoincrement, \
	PkgName, PkgVer, Depname, DepVer, LibName, LibObject, PreVer, PostVer, \
	Direction, Severity, Symbol)'
conn.execute(stmt)
conn.execute('create index if not exists id_index on confirmed_depbug(ID)')

def insert_depbug(table, symbol_info):
	if table == 'depbug_confirm':
		return
	if table == 'depbug_detect':
		table = 'confirmed_depbug'
	stmt = 'insert into '+table+' (PkgName, PkgVer, Depname, DepVer, \
		LibName, LibObject, PreVer, PostVer, Direction, Severity, Symbol) \
		values (?,?,?,?,?,?,?,?,?,?,?)'
	conn.execute(stmt, symbol_info)

# demangle lib_symver
def demangle_symbol(name):
	sym_name = name.replace('@@', '@')
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
	return sym_name

def get_symbol_problems():
	symbol_problem_dict = {}

	# read changed symbols from database
	cur = conn.cursor()
	cur.execute("select distinct LibName, LibObject, PreVer, PostVer, \
		Direction, Symbol from potential_depbug where Severity != 'SymRmv'")
	rows = cur.fetchall()
	for row in rows:
		row_data = [x.encode('ascii') for x in row]
		symbol_problem_dict[str(row_data)] = set()

	# find problems for each symbol
	for xml_file in glob.glob('compat_report/*/*/*/*/*.html'):
		tree = etree.parse(xml_file)
		root = tree.getroot()
		[test_info, test_results, problem_summary, added_symbols, 
		removed_symbols, high_types, higt_symbols, medium_types, 
		medium_symbols, low_types, low_symbols, low_constants, 
		safe_types, safe_symbols, low_constants] = root
		# collect key elements exclude Symver
		LibName = xml_file.split('/')[1]
		Direction = ''
		if '-desc' in LibName:
			Direction = 'Backward'
			LibName = LibName.replace('-desc', '')
		if '-asc' in LibName:
			Direction = 'Forward'
			LibName = LibName.replace('-asc', '')
		PreVer = test_info.find('version1').find('number').text
		PostVer = test_info.find('version2').find('number').text
		ObjFile = test_results.find('libs').find('name').text
		prefix = [LibName, ObjFile, PreVer, PostVer, Direction]
		# get Symver of symbols 
		symbol_header = [x for x in higt_symbols]
		symbol_header+= [x for x in medium_symbols]
		for header in symbol_header:
			for symbol in header.find('library'):
				Symver = demangle_symbol(symbol.get('name'))
				row_data = prefix + [Symver]
				row_data = [x.encode('ascii') for x in row_data]
				if not symbol_problem_dict.has_key(str(row_data)):
					continue
				if len(symbol_problem_dict[str(row_data)]) != 0:
					continue
				for problem in symbol.findall('problem'):
					problem_type = problem.get('id')
					change = problem.find('change')
					if problem_type in no_problem:
						prob = ('mangled', '')
						symbol_problem_dict[str(row_data)].add(prob)
					if problem_type in variable_problem:
						prob = ('variable', change.get('old_value'))
						symbol_problem_dict[str(row_data)].add(prob)
					if problem_type in para_problem:
						param_pos = change.get('param_pos')[:-2]
						op = change.get('old_value')
						if problem_type == 'Removed_Parameter':
							op = 'remove'
						prob = ('para', param_pos, op)
						symbol_problem_dict[str(row_data)].add(prob)
					if problem_type in ret_problem:
						op = ''
						if problem_type == 'Return_BaseType_And_Size':
							op = 'type'
						elif problem_type == 'Return_Type_Became_Const':
							op = 'const'
						elif problem_type == 'Return_Type_Became_Void':
							op = 'void'
						prob = ('ret', change.get('old_value'), op)
						symbol_problem_dict[str(row_data)].add(prob)

		# get Symver of data types 
		type_header = [x for x in high_types]
		type_header+= [x for x in medium_types]
		for header in type_header:
			for mtype in header:
				DataType = mtype.get('name')
				row_data = prefix + [DataType]
				row_data = [x.encode('ascii') for x in row_data]
				if not symbol_problem_dict.has_key(str(row_data)):
					continue
				if len(symbol_problem_dict[str(row_data)]) != 0:
					continue
				for problem in mtype.findall('problem'):
					problem_type = problem.get('id')
					change = problem.find('change')
					if problem_type in enum_problem:
						prob = ('enum', change.get('target'))
						symbol_problem_dict[str(row_data)].add(prob)
					if problem_type in field_problem:
						op = ''
						if problem_type == 'Field_Size':
							op = 'size'
						elif problem_type == 'Moved_Field':
							op = 'move'
						else:
							op = 'remove'
						prob = ('field', change.get('target'), op)
						symbol_problem_dict[str(row_data)].add(prob)

	return symbol_problem_dict

def confirm_para_problem(symbol_info, source, srcml_tree, symbol, problem):
	pos = problem[1]
	paratype = problem[2]
	ns = {'cpp': 'http://www.srcML.org/srcML/cpp', 
		'src': 'http://www.srcML.org/srcML/src'}

	if paratype == 'remove' or 'const' not in paratype:
		insert_depbug('depbug_confirm', symbol_info)
		sys.stderr.write(str(symbol_info)+'\n')
		sys.stderr.write('confirm: '+source+' '+symbol+' '+str(problem)+'\n')

	# get target function call
	for call in srcml_tree.xpath("//src:call/src:name[node()='"+symbol+"']", namespaces=ns):
		call = call.xpath("..", namespaces=ns)[0]

		# get the unit node
		filename = ''
		for unit in call.xpath("./ancestor::src:unit[@filename]", namespaces=ns):
			filename = unit.get('filename')
		if filename == '':
			continue

		# get the problem argument
		arg_var = ''
		for argument in call.xpath("./src:argument_list/src:argument["+pos+"]", namespaces=ns):
			for name in argument.xpath(".//src:name", namespaces=ns):
				arg_var = name.text
		if paratype != 'remove' and arg_var == '':
			continue

		# for Removed_Parameter, no target argument
		if paratype == 'remove':
			if arg_var == '':
				insert_depbug('depbug_detect', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('detect: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				return
			else:
				continue

		# get the types of the problem argument
		parent = call
		decl_types = []
		while not 'unit' in parent.tag:
			for decl_stmt in parent.xpath("./preceding-sibling::src:decl_stmt", namespaces=ns):
				for decl in decl_stmt.xpath(".//src:decl[src:name='"+arg_var+"']", namespaces=ns):
					decl_types.append(decl.xpath("./parent::*", namespaces=ns)[0])
			parent = parent.xpath("./parent::*", namespaces=ns)[0]
		if len(decl_types) == 0:
			continue
		decl_type = decl_types[0]

		# for Parameter_Became_Non_Const, check type name and type specifier
		if 'const' in paratype:
			non_const_type = paratype.replace('const','').strip()
			const = decl_type.xpath(".//src:specifier[node()='const']", namespaces=ns)
			if len(const) == 0:
				continue
			for typename in decl_type.xpath("./src:decl/src:type//src:name", namespaces=ns):
				if typename.text == non_const_type:
					insert_depbug('depbug_confirm', symbol_info)
					sys.stderr.write(str(symbol_info)+'\n')
					sys.stderr.write('confirm: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
					insert_depbug('depbug_detect', symbol_info)
					sys.stderr.write(str(symbol_info)+'\n')
					sys.stderr.write('detect: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
					return

		# for Parameter_PointerLevel_Increased/Decreased
		'''
		else:
			ptr_keyword = 0
			asterisk_keyword = 0
			for typename in decl_type.xpath("./src:type//src:name", namespaces=ns):
				if 'pointer' in typename:
					ptr_keyword = 1
			for modifier in decl_type.xpath("./src:type//src:modifier", namespaces=ns):
				if '*' in modifier:
					asterisk_keyword = 1
			if ptr_keyword + asterisk_keyword == int(paratype):
				insert_depbug('depbug_detect', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('detect: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				return
		'''

def confirm_ret_problem(symbol_info, source, srcml_tree, symbol, problem):
	ret_type = problem[1]
	op = problem[2]
	ns = {'cpp': 'http://www.srcML.org/srcML/cpp', 
		'src': 'http://www.srcML.org/srcML/src'}

	if op == 'type':
		insert_depbug('depbug_confirm', symbol_info)
		sys.stderr.write(str(symbol_info)+'\n')
		sys.stderr.write('confirm: '+source+' '+symbol+' '+str(problem)+'\n')

	# get target function call
	for call in srcml_tree.xpath("//src:call/src:name[node()='"+symbol+"']", namespaces=ns):
		call = call.xpath("..", namespaces=ns)[0]

		# get the unit node
		filename = ''
		for unit in call.xpath("./ancestor::src:unit[@filename]", namespaces=ns):
			filename = unit.get('filename')
		if filename == '':
			continue


		# for Return_Type_Became_Void
		if op == 'void':
			# bar(foo())
			for expr in call.xpath("./ancestor::src:argument", namespaces=ns):
				insert_depbug('depbug_confirm', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('confirm: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				insert_depbug('depbug_detect', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('detect: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				return
			# a = foo()
			operator = call.xpath("./preceding-sibling::src:operator[1]", namespaces=ns)
			if len(operator) != 0 and '=' == operator[0].text:
				insert_depbug('depbug_confirm', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('confirm: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				insert_depbug('depbug_detect', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('detect: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				return
			# int a = foo()
			for expr in call.xpath("./ancestor::src:init", namespaces=ns):
				insert_depbug('depbug_confirm', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('confirm: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				insert_depbug('depbug_detect', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('detect: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				return
			continue

		# if there is a ret_value, e.g., a = foo();
		has_ret = 0
		parent = call.xpath("./parent::*", namespaces=ns)[0]
		if parent.tag == '{http://www.srcML.org/srcML/src}expr':
			call = parent
		for expr in call.xpath("./parent::src:init", namespaces=ns):
			call = expr
			has_ret = 1
		for expr in call.xpath("./preceding-sibling::src:operator[node()='=']", namespaces=ns):
			call = expr
			has_ret = 1
		if has_ret == 0:
			continue


		# get the ret_var
		ret_var = ''
		for expr in call.xpath("./preceding-sibling::src:name", namespaces=ns):
			ret_var = expr.text
			for name in expr.xpath(".//src:name", namespaces=ns):
				ret_var = name.text
		if ret_var == '':
			continue
		
		# get the types of the problem ret_var
		parent = call
		decl_types = []
		while not 'unit' in parent.tag:
			if 'decl_stmt' in parent.tag:
				decl_types.append(parent)
			for decl_stmt in parent.xpath("./preceding-sibling::src:decl_stmt", namespaces=ns):
				for decl in decl_stmt.xpath(".//src:decl[src:name='"+ret_var+"']", namespaces=ns):
					decl_types.append(decl.xpath("./parent::*", namespaces=ns)[0])
			parent = parent.xpath("./parent::*", namespaces=ns)[0]
		if len(decl_types) == 0:
			continue
		decl_type = decl_types[0]

		# for Return_Type_Became_Const
		if op == 'const':
			const = decl_type.xpath(".//src:specifier[node()='const']", namespaces=ns)
			if len(const) == 0:
				insert_depbug('depbug_confirm', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('confirm: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				insert_depbug('depbug_detect', symbol_info)
				sys.stderr.write(str(symbol_info)+'\n')
				sys.stderr.write('detect: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
				return

		# for Return_BaseType
		if op == 'type':
			ret_type = ret_type.replace('unsigned', '').strip()
			for name in decl_type.xpath(".//src:name", namespaces=ns):
				if name.text == ret_type:
					insert_depbug('depbug_detect', symbol_info)
					sys.stderr.write(str(symbol_info)+'\n')
					sys.stderr.write('detect: '+source+' '+filename+' '+symbol+' '+str(problem)+'\n')
					return
	return 0

def confirm_field_problem(symbol_info, source, srcml_tree, symbol, problem):
	field = problem[1]
	op = problem[2]
	ns = {'cpp': 'http://www.srcML.org/srcML/cpp', 
		'src': 'http://www.srcML.org/srcML/src'}

	symbol = symbol.split(' ')[-1].split(':')[-1]
	# get field name
	for name in srcml_tree.xpath("//src:name", namespaces=ns):
		if field != name.text:
			continue

		# get operator
		operator = name.xpath("./preceding-sibling::src:operator[1]", namespaces=ns)
		if len(operator) == 0:
			continue
		operator = operator[0]
		if '->' != operator.text and '.' != operator.text:
			continue

		# get struct variable
		variable = operator.xpath("./preceding-sibling::src:name[1]", namespaces=ns)
		if len(variable) == 0:
			continue
		variable = variable[0]
		if variable.text == None:
			continue

		# get the types of the struct variable
		parent = variable
		decl_types = []
		while not 'unit' in parent.tag:
			for decl_stmt in parent.xpath("./preceding-sibling::src:decl_stmt", namespaces=ns):
				for decl in decl_stmt.xpath(".//src:decl[src:name='"+variable.text+"']", namespaces=ns):
					decl_types.append(decl.xpath("./parent::*", namespaces=ns)[0])
			parent = parent.xpath("./parent::*", namespaces=ns)[0]
		if len(decl_types) == 0:
			continue
		decl_type = decl_types[0]

		# match the struct types
		for typename in decl_type.xpath("./src:decl/src:type//src:name", namespaces=ns):
			if typename.text == None:
				continue
			sym_kw_list = segment(symbol)
			def_kw_list = segment(typename.text)
			for sym_kw in sym_kw_list:
				if len(sym_kw) < 3:
					continue
				for def_kw in def_kw_list:
					if len(def_kw) < 3:
						continue
					if sym_kw in def_kw or def_kw in sym_kw:
						unit = name.xpath("./ancestor::src:unit[@filename]", namespaces=ns)[0]
						insert_depbug('depbug_confirm', symbol_info)
						sys.stderr.write(str(symbol_info)+'\n')
						sys.stderr.write('confirm: '+source+' '+unit.get('filename')+' '+symbol+' '+str(problem)+'\n')
						if op == 'remove':
							insert_depbug('depbug_detect', symbol_info)
							sys.stderr.write(str(symbol_info)+'\n')
							sys.stderr.write('detect: '+source+' '+unit.get('filename')+' '+symbol+' '+str(problem)+'\n')
						return

def confirm_enum_problem(symbol_info, source, srcml_tree, symbol, problem):
	enum = problem[1]
	ns = {'cpp': 'http://www.srcML.org/srcML/cpp', 
		'src': 'http://www.srcML.org/srcML/src'}

	for name in srcml_tree.xpath("//src:name", namespaces=ns):
		if enum == name.text:
			unit = name.xpath("./ancestor::src:unit[@filename]", namespaces=ns)[0]
			insert_depbug('depbug_confirm', symbol_info)
			sys.stderr.write(str(symbol_info)+'\n')
			sys.stderr.write('confirm: '+source+' '+unit.get('filename')+' '+symbol+' '+str(problem)+'\n')
			return

def confirmed(symbol_info, source, symbol, problem):
	global last_source
	global srcml_tree
	global count

	# build srcml_tree
	if not os.path.exists('xml/'+source+'.xml'):
		return
	try:
		if source != last_source:
			p = XMLParser(huge_tree=True)
			sys.stderr.write('['+str(count)+'] Parse xml/'+source+'.xml ... \n')
			srcml_tree = etree.parse('xml/'+source+'.xml', parser=p)
			last_source = source
	except:
		sys.stderr.write('Failed to build srcml tree: xml/'+source+'.xml\n')
		return

	problem_type = problem[0]
	try:
		if problem_type == 'mangled':
			insert_depbug('depbug_confirm', symbol_info)
			sys.stderr.write(str(symbol_info)+'\n')
			sys.stderr.write('confirm: '+source+' '+symbol+' '+str(problem)+'\n')
			insert_depbug('depbug_detect', symbol_info)
			sys.stderr.write(str(symbol_info)+'\n')
			sys.stderr.write('detect: '+source+' '+symbol+' '+str(problem)+'\n')
		elif problem_type == 'variable':
			insert_depbug('depbug_confirm', symbol_info)
			sys.stderr.write(str(symbol_info)+'\n')
			sys.stderr.write('confirm: '+source+' '+symbol+' '+str(problem)+'\n')
		elif problem_type == 'enum':
			confirm_enum_problem(symbol_info, source, srcml_tree, symbol, problem)
		elif problem_type == 'field':
			confirm_field_problem(symbol_info, source, srcml_tree, symbol, problem)
		elif problem_type == 'ret':
			if 'const' in problem[2]:
				return
			confirm_ret_problem(symbol_info, source, srcml_tree, symbol, problem)
		elif problem_type == 'para':
			if 'const' in problem[2]:
				return
			confirm_para_problem(symbol_info, source, srcml_tree, symbol, problem)
	except:
		sys.stderr.write('Failed to confirm problem: '+source+' '+str(symbol_info)+' '+str(problem)+'\n')
	
	sys.stderr.flush()
	gc.collect()

def check_source_package(symbol_problem_dict):
	global last_source
	global count

	last_source = ''
	comfirmed_row = []

	# read package-source mapping
	pkg_src_dict = {}
	mapping_file = open('pkg_src_map.txt', 'r')
	mapping_lines = mapping_file.readlines()
	mapping_file.close()
	for mapping_line in mapping_lines:
		mapping_line = mapping_line.strip()
		[package, source] = mapping_line.split(' ')
		pkg_src_dict[package] = source

	# check instances for the current source package
	conn = sqlite3.connect('depbug.db')
	cur = conn.cursor()
	cur.execute("select * from potential_depbug order by PkgName")
	rows = cur.fetchall()
	conn.close()
	load()
	tmp = 0
	for row in rows:
		count += 1
		row_data = [x.encode('ascii') for x in row[1:]]
		[PkgName, PkgVer, DepName, DepVer, LibName, LibObject, 
			PreVer, PostVer, Direction, Severity, Symver] = row_data

		if Severity == 'SymRmv':
			insert_depbug('depbug_confirm', row_data)
			insert_depbug('depbug_detect', row_data)
			continue

		if not pkg_src_dict.has_key(PkgName):
			continue
		source = pkg_src_dict[PkgName]
		my_key = [LibName, LibObject, PreVer, PostVer, Direction, Symver]
		if not symbol_problem_dict.has_key(str(my_key)):
			continue
		symbol = Symver.split('@')[0]
		# skip private data type
		if symbol in private_type:
			continue
		# break if any problem is comfirmed
		for problem in symbol_problem_dict[str(my_key)]:
			confirmed(row_data, source, symbol, problem)

count = 0
symbol_problem_dict = get_symbol_problems()
check_source_package(symbol_problem_dict)
conn.commit()
conn.close()
