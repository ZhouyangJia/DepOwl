import bs4
import requests
import sqlite3
import wget
import os, sys



def download_source(PkgName):
	pakcage_url = 'https://packages.ubuntu.com/eoan/' + PkgName
	page = None
	try:
		page = requests.get(pakcage_url)
		if not '200' in str(page):
			page = requests.get(pakcage_url)
	except:
		print 'Failed to request:',pakcage_url
		return
	if not '200' in str(page):
		print 'Failed to request:',pakcage_url
		return
	site_soup = bs4.BeautifulSoup(page.content, "html.parser")
	div_wrapper = site_soup.find('body').find('div', {'id':'wrapper'})
	div_content = div_wrapper.find('div', {'id':'content'})
	dif_pmoreinfo = div_content.find('div', {'id':'pmoreinfo'})
	ul = dif_pmoreinfo.find_all('ul')[1]
	for li in ul.find_all('li'):
		source_name = li.find('a').text
		if '.asc' in source_name or '.dsc' in source_name or \
			'.debian' in source_name:
			continue
		if 'orig' in source_name or '.tar.gz' in source_name or \
			'.tar.xz' in source_name or '.tar.bz2' in source_name:
			source_name = source_name[1:-1]
			source_url = li.find('a').get('href')
			if not os.path.isdir('./sources'):
				os.system('mkdir sources')
			if not os.path.exists('./sources/'+source_name):
				wget.download(source_url, './sources/'+source_name)
			#print PkgName, source_name
			print
			mapping_file.write(PkgName + ' ' + source_name + '\n')

'''
failed_file = open('pkg_src_mapping_failed.txt', 'r')
failed_pkgs = failed_file.readlines()
for failed_pkg in failed_pkgs:
	failed_pkg = failed_pkg.strip()
	failed_pkg = failed_pkg.split('/')[-1]
	download_source(failed_pkg)
failed_file.close()
exit()
'''

'''
mapping_file = open('pkg_src_map.txt', 'r')
mapping_lines = mapping_file.readlines()

pkg_set = set()
for mapping_line in mapping_lines:
	mapping_line = mapping_line.strip()
	[pkg, src] = mapping_line.split(' ')
	pkg_set.add(pkg)
'''

mapping_file = open('pkg_src_map.txt', 'w')
conn = sqlite3.connect('depbug.db')
cur = conn.cursor()
cur.execute("select distinct PkgName from potential_depbug")
rows = cur.fetchall()
count = 0
total = len(rows)
for row in rows:
	count += 1
	sys.stderr.write(str(count)+'/'+str(total)+'\r')
	sys.stderr.flush()
	PkgName = row[0]
	#if PkgName not in pkg_set:
	download_source(PkgName)
conn.close()
mapping_file.close()
