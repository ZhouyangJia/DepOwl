import xml.etree.ElementTree as ET
import glob
import openpyxl
import os

def add_row(row_data):
	global row_pos
	[LibName, ObjFile, PreVer, PostVer, Direction, 
		DataType, Symver, Severity] = row_data

	if '-test' in LibName:
		return
	if '.h' in DataType:
		return
	if 'PRIVATE_API' in Symver:
		return

	row_pos += 1
	table['A' + str(row_pos)] = LibName
	table['B' + str(row_pos)] = ObjFile
	table['C' + str(row_pos)] = PreVer
	table['D' + str(row_pos)] = PostVer
	table['E' + str(row_pos)] = Direction
	table['F' + str(row_pos)] = DataType
	table['G' + str(row_pos)] = Symver
	table['H' + str(row_pos)] = Severity

work = openpyxl.Workbook()
table = work.create_sheet("data", 0)
row_pos = 0
row_data = ["LibName", "ObjFile", "PreVer", "PostVer", "Direction", 
	"DataType", "Symver", "Severity"]
add_row(row_data)

for xml_file in glob.glob('compat_report/*/*/*/*/*.html'):
	#print xml_file
	
	fin = open(xml_file, 'r')
	fout = open('tmp.txt', 'w')
	for line in fin:
		fout.write(line.replace('&amp;', '&').replace('&', '&amp;'))
	os.system('mv tmp.txt '+xml_file)
	fin.close()
	fout.close()

	tree = ET.parse(xml_file)
	root = tree.getroot()
	
	LibName = xml_file.split('/')[1]
	Direction = ''
	if '-desc' in LibName:
		Direction = 'Backward'
		LibName = LibName.replace('-desc', '')
	if '-asc' in LibName:
		Direction = 'Forward'
		LibName = LibName.replace('-asc', '')

	[test_info, test_results, problem_summary, added_symbols, 
	removed_symbols, high_types, higt_symbols, medium_types, 
	medium_symbols, low_types, low_symbols, low_constants, 
	safe_types, safe_symbols, low_constants] = root
		
	PreVer = test_info.find('version1').find('number').text
	PostVer = test_info.find('version2').find('number').text
	ObjFile = test_results.find('libs').find('name').text
	
	src_obj = ObjFile
	tar_obj = ''
	if len(list(added_symbols)) != 0 and \
		len(list(added_symbols.find('header'))) != 0:
		tar_obj = added_symbols.find('header').find('library').get('name')
	if tar_obj != '':
		num_start = src_obj.find('.so.') + 4
		soname_end = src_obj[num_start:].find('.') + num_start
		soname1 = src_obj[:soname_end]
		num_start = tar_obj.find('.so.') + 4
		soname_end = tar_obj[num_start:].find('.') + num_start
		soname2 = tar_obj[:soname_end]
		if soname1 != soname2:
			continue

	prefix = [LibName, ObjFile, PreVer, PostVer, Direction]

	for header in removed_symbols:
		for name in header.find('library'):
			Symver = name.text
			row_data = prefix + ['None', Symver, 'SymRmv']
			add_row(row_data)
			
	for header in higt_symbols:
		for symbol in header.find('library'):
			Symver = symbol.get('name')
			row_data = prefix + ['None', Symver, 'SymHigh']
			add_row(row_data)
			
	for header in medium_symbols:
		for symbol in header.find('library'):
			Symver = symbol.get('name')
			row_data = prefix + ['None', Symver, 'SymMid']
			add_row(row_data)

	for header in high_types:
		for mtype in header:
			DataType = mtype.get('name')
			for symbol in mtype.find('affected'):
				Symver = symbol.get('name')
				row_data = prefix + [DataType, Symver, 'TypeHigh']
				add_row(row_data)

	for header in medium_types:
		for mtype in header:
			DataType = mtype.get('name')
			for symbol in mtype.find('affected'):
				Symver = symbol.get('name')
				row_data = prefix + [DataType, Symver, 'TypeMid']
				add_row(row_data)

work.save('symbols.xlsx')

