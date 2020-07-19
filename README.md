# DepOwl

A practical tool helping users prevent compatibility failures.

---

## HOWTO

### Prepare libraries
The directory **library/** provides an example of how to organize the libraries, including *zlib* and *glib* (used in the motivating examples in the paper).

### Generate *json* files
We need to generate *json* files to specify the available versions of the libraries. 
The files are further required by *abi-tracker* to perform backward incompatibility checking.

```
python py/generate_json.py -l zlib
python py/generate_json.py -l glib
```

The step will generate the directory **json/**, where each library has two *json* files, e.g., *zlib-asc.json* and *zlib-desc.json* for *zlib*. The two *json* files include the versions in an ascending and descending orders, respectively.


### Build libraries
DepOwl provides a script to compile history versions of the libraries. 
This script successfully compiles the libraries in Ubuntu 18.04 with gcc-5.5.

```
python py/build_lib.py -l zlib
python py/build_lib.py -l glib
```
If the script fails, please manually  compile the libraries with debug symbol, and install the binaries in the directory **build/library/version** (e.g. build/zlib/1.2.5.1).

### Detect incompatible library changes
DepOwl uses [*abi-tracker*](https://github.com/lvc/abi-tracker)
to detect incompatible library changes. A convinent method to install the tool is to use the [installer](https://github.com/lvc/installer) provided by the 
*abi-tracker* developers.
Moreover, *abi-tracker* requires [Universal Ctags](https://github.com/universal-ctags/ctags).
As *abi-tracker* reports results in webpages, it is a bit hard to parse the results. Thus, we change the output format into *xml*:

```
--- abi-tracker:2900    my $CompatOpt = "-bin -bin-report-path \"$BinReport\"";
+++ abi-tracker:2900    my $CompatOpt = "-xml -bin -bin-report-path \"$BinReport\"";
``` 

We may also need to escape the following left brace to let *perl* happy:

```
--- abi-dumper:3200    $N=~s/(\w){/$1 {/g;
+++ abi-dumper:3200    $N=~s/(\w)\{/$1 {/g;

```
Then, we can use *abi-tracker*:

```
abi-tracker -build json/zlib-asc.json
abi-tracker -build json/zlib-desc.json
abi-tracker -build json/glib-asc.json
abi-tracker -build json/glib-desc.json
```

*abi-tracker* outputs results in the directory **compat_report/**, DepOwl provides a script to parse the results:

```
python py/extract_report.py
```

This command will generate the excel file *symbols.xlsx*, which contains the interested library changes required by DepOwl.

### Detect potential depbugs (the filtering phase)

In this step, DepOwl selects all packages (from the given repository) that may potentially be affected by the above library changes.

```
python py/match_pkg.py
```

This step will generate the directory **packages/**, which contains the packages (downloaded by DepOwl) that are depended on the libraries (e.g., *zlib* or *glib*).
Also, DepOwl outputs the database file *depbug.db*, which contains the potential depbugs (in the table *potential_depbug*). 

The above command works on a test repository. Make the following change to run on the real-word repository shipped with ubuntu-19.10 (unzip repository/ubuntu-19.10.zip first, it may takes a long time to download the packages):

```
--- py/match_pkg.py:159    for pkg_file_name in glob.glob('repository/test/*.txt'):
+++ py/match_pkg.py:159    for pkg_file_name in glob.glob('repository/ubuntu-19.10/*.txt'):
```

### Confirm depbugs (the determining phase)

When analyzing application binaries (with debug symbols), extract API usages:

```
cd src

//Step 1: install clang, and compile the target file test.c
sudo apt install clang-9 llvm-9
clang-9 -S -emit-llvm -g -O -Xclang -femit-debug-entry-values -o test.ll test.c
llc-9 test.ll -o test.o -filetype=obj

//Step 2: install libdwarf, compile, and run the program
sudo apt install libdwarf-dev
gcc get_decl.c -ldwarf -o get_decl
./get_decl test.o
```

When taking source code as input, we need to get the source code:

```
python py/download_source.py
```

This command will generate the directory **sources/**, which contains the source code for each package.

Then, DepOwl analyze the source code by using [*srcML*](https://www.srcml.org/):

```
python py/src2srcml.py
```

This command transfers the source code to *xml* files located in the directory **xml/**.

Finally, DepOwl confirms depbugs by:

```
python py/confirm_symbol.py 2>/dev/null
```

The results are located in the table *confirmed_depbug*.

The depbugs may have duplicates. The follosing commands can deduplicate the results:

```
sqlite3 depbug.db

sqlite> .headers ON
sqlite> .mode column
sqlite> select distinct PkgName,PkgVer,Depname,DepVer,PostVer as BugVer
   ...> from confirmed_depbug;

PkgName     PkgVer      Depname     DepVer      BugVer    
----------  ----------  ----------  ----------  ----------
ccache      3.7.3-1     zlib1g      >= 1:1.1.4  1.2.5.2   
cockpit-br  202.1-1     libglib2.0  >= 2.37.6   2.39.1    
homebank    5.2.2-1     libglib2.0  >= 2.37.3   2.39.1    
mathgl      2.4.4-4     zlib1g      >= 1:1.2.0  1.2.5.2   
```

### That's it, have fun.