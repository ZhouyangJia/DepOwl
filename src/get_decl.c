//===--- get_decl.c - Extract declaration info from binary using DWARF ---===//
//
//  Author: Zhouyang Jia, PhD Candidate
//  Email: jiazhouyang@nudt.edu.cn
//
//===---------------------------------------------------------------------===//
//
//  This program outputs function/struct/union/enum declarations of a 
//  given binary file, which is compiled with DWARF debug info.
//
//  Usage: 
//
//      Step 1: install clang, and compile the target file test.c
//      $ sudo apt install clang-9 llvm-9
//      $ clang-9 -S -emit-llvm -g -O -Xclang -femit-debug-entry-values \
//          -o test.ll test.c
//      $ llc-9 test.ll -o test.o -filetype=obj
//
//      Step 2: install dependency, compile, and run the program
//      $ sudo apt install libdwarf-dev
//      $ gcc get_decl.c -ldwarf -o get_decl
//      $ ./get_decl test.o
// 
//===---------------------------------------------------------------------===//


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>

#include "libdwarf/dwarf.h"
#include "libdwarf/libdwarf.h"

#define MAX_STRING_LENGTH 1000


// read compilation units of a given Dwarf_Debug descriptor
void read_cu_list(
    Dwarf_Debug dbg);           // input Dwarf_Debug descriptor

// search die tree from the root node of a compilation unit
void search_die_tree(
    Dwarf_Debug dbg,            // input Dwarf_Debug descriptor
    Dwarf_Die in_die,           // input root node
    int in_level);              // current level of the tree

// print a given die node
void print_die_entry(
    Dwarf_Debug dbg,            // input Dwarf_Debug descriptor
    Dwarf_Die print_me,         // input node
    int level);                 // current level of the tree

// convert a type die to a string (do not unfold struct/union/enum)
void get_type_string(
    Dwarf_Debug dbg,            // input Dwarf_Debug descriptor
    Dwarf_Die type_die,         // input type die
    char* type_string);         // output string

// convert a given type of children die to a string
void get_children_string(
    Dwarf_Debug dbg,            // input Dwarf_Debug descriptor
    Dwarf_Die type_die,         // input parent die
    char* type_string,          // output string
    Dwarf_Half filter_tag);     // type of children


int main(int argc, char **argv) {
 
    int res = DW_DLV_ERROR;
    Dwarf_Handler errhand = 0;
    Dwarf_Ptr errarg = 0;
    Dwarf_Debug dbg = 0;
    Dwarf_Error error;
    Dwarf_Error *errp  = &error;
    char macho_real_path[MAX_STRING_LENGTH] = "";
    int fd;
    
    if ((fd = open(argv[1], O_RDONLY)) == -1) {
        printf("Usage: ./get_decl test.o\n");
        exit(1);
    }
    
    res = dwarf_init_b(fd, DW_DLC_READ, DW_GROUPNUMBER_ANY, 
        errhand, errarg, &dbg, errp);
    if(res != DW_DLV_OK) {
        printf("Giving up, cannot do DWARF processing\n");
        exit(1);
    }
    
    read_cu_list(dbg);
    return 0;
}


void read_cu_list(Dwarf_Debug dbg) {

    int res = DW_DLV_ERROR;
    Dwarf_Unsigned cu_header_length = 0;
    Dwarf_Half     version_stamp = 0;
    Dwarf_Unsigned abbrev_offset = 0;
    Dwarf_Half     address_size = 0;
    Dwarf_Half     offset_size = 0;
    Dwarf_Half     extension_size = 0;
    Dwarf_Sig8     signature;
    Dwarf_Unsigned typeoffset = 0;
    Dwarf_Unsigned next_cu_header = 0;
    Dwarf_Half     header_cu_type = DW_UT_compile;
    Dwarf_Error error = 0;
    Dwarf_Error *errp  = &error;
    
    while(1) {
        Dwarf_Die no_die = 0;
        Dwarf_Die cu_die = 0;
        memset(&signature, 0, sizeof(signature));

        res = dwarf_next_cu_header_d(dbg, 1, &cu_header_length,
            &version_stamp, &abbrev_offset, &address_size, &offset_size,
            &extension_size, &signature, &typeoffset, &next_cu_header,
            &header_cu_type, errp);
        if(res == DW_DLV_ERROR) {
            char *em = errp ? dwarf_errmsg(error) : "unknown error";
            printf("Error in dwarf_next_cu_header_d: %s\n", em);
            exit(1);
        }
        if(res == DW_DLV_NO_ENTRY) {
            return;
        }
        
        // According to libdwarf2.1.pdf, if no_die is NULL, the first 
        // die in the compilation-unit is returned to cu_die.
        res = dwarf_siblingof_b(dbg, no_die, 1, &cu_die, errp);
        if(res == DW_DLV_ERROR) {
            char *em = errp ? dwarf_errmsg(error) : "unknown error";
            printf("Error in dwarf_siblingof_b (level 0): %s\n", em);
            exit(1);
        }
        
        search_die_tree(dbg, cu_die, 0);
        dwarf_dealloc(dbg, cu_die, DW_DLA_DIE);
    }
}


void search_die_tree(Dwarf_Debug dbg, Dwarf_Die in_die, int in_level) {
    
    int res = DW_DLV_ERROR;
    Dwarf_Die cur_die = in_die;
    Dwarf_Die child = 0;
    Dwarf_Error error = 0;
    Dwarf_Error *errp = &error;

    print_die_entry(dbg, in_die, in_level);

    while(1) {
        Dwarf_Die sib_die = 0;
        res = dwarf_child(cur_die, &child, errp);
        if(res == DW_DLV_ERROR) {
            printf("Error in dwarf_child (level %d)\n", in_level);
            exit(1);
        }
        if(res == DW_DLV_OK) {
            search_die_tree(dbg, child, in_level+1);
            dwarf_dealloc(dbg, child, DW_DLA_DIE);
            child = 0;
        }
        
        res = dwarf_siblingof_b(dbg, cur_die, 1, &sib_die, errp);
        if(res == DW_DLV_ERROR) {
            char *em = errp ? dwarf_errmsg(error) : "unknown error";
            printf("Error in dwarf_siblingof_b (level %d): %s\n",
                in_level, em);
            exit(1);
        }
        if(res == DW_DLV_NO_ENTRY)
            break;
        
        if(cur_die != in_die) {
            dwarf_dealloc(dbg, cur_die, DW_DLA_DIE);
            cur_die = 0;
        }
        cur_die = sib_die;
        print_die_entry(dbg, cur_die, in_level);
    }
    return;
}


void print_die_entry(Dwarf_Debug dbg, Dwarf_Die print_me, int level) {

    int res = DW_DLV_ERROR;
    const char *tag_name = 0;
    Dwarf_Half tag = 0;
    Dwarf_Error error = 0;
    Dwarf_Error *errp = &error;

    res = dwarf_tag(print_me, &tag, errp) ||
        dwarf_get_TAG_name(tag, &tag_name);
    if(res == DW_DLV_OK) {
        //printf("\033[0m");
        //printf("<%d> %s\n", level, tag_name);
        //printf("\033[0;31m");
    }
    
    if(tag == DW_TAG_structure_type ||
        tag == DW_TAG_union_type ||
        tag == DW_TAG_enumeration_type) {
        
        char *type_name = 0;
        char field_string[MAX_STRING_LENGTH] = "";
        res = dwarf_diename(print_me, &type_name, errp);
        if(res == DW_DLV_OK) {
            if(tag == DW_TAG_structure_type){
                get_children_string(dbg, print_me, field_string, 
                    DW_TAG_member);
                printf("struct");
            }
            else if(tag == DW_TAG_union_type){
                get_children_string(dbg, print_me, field_string, 
                    DW_TAG_member);
                printf("union");
            }
            else if(tag == DW_TAG_enumeration_type){
                get_children_string(dbg, print_me, field_string, 
                    DW_TAG_enumerator);
                printf("enum");
            }
            printf(" %s {%s};\n", type_name, field_string);
            dwarf_dealloc(dbg, type_name, DW_DLA_STRING);
        }
        return;
    }

    if(tag == DW_TAG_subprogram) {
        char *die_name = "";
        Dwarf_Off type_offset = 0;
        Dwarf_Die type_die;
        res = dwarf_dietype_offset(print_me, &type_offset, errp) ||
            dwarf_offdie_b(dbg, type_offset, 1, &type_die, errp) ||
            dwarf_diename(print_me, &die_name, errp);
        if(res == DW_DLV_OK) {
            char return_string[MAX_STRING_LENGTH] = "";
            char parameter_string[MAX_STRING_LENGTH] = "";
            get_type_string(dbg, type_die, return_string);
            get_children_string(dbg, print_me, parameter_string, 
                DW_TAG_formal_parameter);
            printf("%s %s(%s);\n", return_string, die_name, 
                parameter_string);
            dwarf_dealloc(dbg, die_name, DW_DLA_STRING);
            dwarf_dealloc(dbg, type_die, DW_DLA_DIE);
        }
        return;
    }
}


void get_type_string(Dwarf_Debug dbg, Dwarf_Die type_die, 
    char* type_string) {

    int res = DW_DLV_ERROR;
    Dwarf_Half type_tag = 0;
    const char *tag_name = 0;
    Dwarf_Error error = 0;
    Dwarf_Error *errp = &error;
    res = dwarf_tag(type_die, &type_tag, errp);
    if(res != DW_DLV_OK)
        return;
        
    if(type_tag == DW_TAG_base_type) {
        char *type_name = 0;
        res = dwarf_diename(type_die, &type_name, errp);
        if(res == DW_DLV_OK) {
            strcat(type_string, type_name);
            dwarf_dealloc(dbg, type_name, DW_DLA_STRING);
        }
    }
    else if(type_tag == DW_TAG_pointer_type) {
        char mtype_string[MAX_STRING_LENGTH] = "";
        Dwarf_Off mtype_offset = 0;
        Dwarf_Die mtype_die;
        res = dwarf_dietype_offset(type_die, &mtype_offset, errp) ||
            dwarf_offdie_b(dbg, mtype_offset, 1, &mtype_die, errp);
        if(res == DW_DLV_OK) {
            get_type_string(dbg, mtype_die, mtype_string);
            strcat(type_string, mtype_string);
            strcat(type_string, "*");
            dwarf_dealloc(dbg, mtype_string, DW_DLA_DIE);
        }
    }
    else if(type_tag == DW_TAG_array_type) {
        char mtype_string[MAX_STRING_LENGTH] = "";
        char msize_string[MAX_STRING_LENGTH] = "";
        Dwarf_Off mtype_offset = 0;
        Dwarf_Die mtype_die;
        res = dwarf_dietype_offset(type_die, &mtype_offset, errp) ||
            dwarf_offdie_b(dbg, mtype_offset, 1, &mtype_die, errp);
        if(res == DW_DLV_OK) {
            get_type_string(dbg, mtype_die, mtype_string);
            strcat(type_string, mtype_string);
        }
        get_children_string(dbg, type_die, msize_string, 
            DW_TAG_subrange_type);
        strcat(type_string, msize_string);
    }
    else if(type_tag == DW_TAG_structure_type) {
        char *type_name = 0;
        res = dwarf_diename(type_die, &type_name, errp);
        if(res == DW_DLV_OK) {
            strcat(type_string, "struct ");
            strcat(type_string, type_name);
            dwarf_dealloc(dbg, type_name, DW_DLA_STRING);
        }
    }
}


void get_children_string(Dwarf_Debug dbg, Dwarf_Die type_die, 
    char* type_string, Dwarf_Half filter_tag) {

    int res = DW_DLV_ERROR;
    Dwarf_Error error = 0;
    Dwarf_Error *errp = &error;
    Dwarf_Half type_tag = 0;
    Dwarf_Die cur_die;
    Dwarf_Die sib_die;
    
    res = dwarf_child(type_die, &cur_die, errp) ||
        dwarf_tag(cur_die, &type_tag, errp);
    if(res != DW_DLV_OK)
        return;
        
    while(res == DW_DLV_OK) {
        if(type_tag == DW_TAG_subrange_type) {
            Dwarf_Attribute attr = 0;
            Dwarf_Unsigned msize;
            char msize_string[MAX_STRING_LENGTH] = "";
            dwarf_attr(cur_die, DW_AT_count, &attr, errp);
            dwarf_formudata(attr, &msize, errp);
            sprintf(msize_string, "[%llu]", msize);
            strcat(type_string, msize_string);
            dwarf_dealloc(dbg,attr,DW_DLA_ATTR);
        }
        else if(type_tag == DW_TAG_enumerator) {
            char *mname_string = "";
            Dwarf_Attribute attr = 0;
            Dwarf_Unsigned mvalue;
            char mvalue_string[MAX_STRING_LENGTH] = "";
            dwarf_diename(cur_die, &mname_string, errp);
            dwarf_attr(cur_die, DW_AT_const_value, &attr, errp);
            dwarf_formudata(attr, &mvalue, errp);
            sprintf(mvalue_string, "=%llu", mvalue);
            strcat(type_string, mname_string);
            strcat(type_string, mvalue_string);
            dwarf_dealloc(dbg, mname_string, DW_DLA_STRING);
        }
        else if(type_tag == DW_TAG_member) {
            char mtype_string[MAX_STRING_LENGTH] = "";
            Dwarf_Off mtype_offset = 0;
            Dwarf_Die mtype_die;
            dwarf_dietype_offset(cur_die, &mtype_offset, errp);
            dwarf_offdie_b(dbg, mtype_offset, 1, &mtype_die, errp);
            get_type_string(dbg, mtype_die, mtype_string);
            strcat(type_string, mtype_string);
            dwarf_dealloc(dbg, mtype_die, DW_DLA_DIE);
        }
        else if(type_tag == DW_TAG_formal_parameter) {
            char mtype_string[MAX_STRING_LENGTH] = "";
            Dwarf_Off mtype_offset = 0;
            Dwarf_Die mtype_die;
            dwarf_dietype_offset(cur_die, &mtype_offset, errp);
            dwarf_offdie_b(dbg, mtype_offset, 1, &mtype_die, errp);
            get_type_string(dbg, mtype_die, mtype_string);
            strcat(type_string, mtype_string);
            dwarf_dealloc(dbg, mtype_die, DW_DLA_DIE);
        }
        
        if(type_tag == filter_tag && type_tag != DW_TAG_subrange_type)
            strcat(type_string, ", ");
            
        res = dwarf_siblingof_b(dbg, cur_die, 1, &sib_die, errp);
        if(res == DW_DLV_NO_ENTRY){
        	if(type_string[strlen(type_string) - 2] == ',')
        		type_string[strlen(type_string) - 2] = '\0';
            break;
        }
        dwarf_dealloc(dbg, cur_die, DW_DLA_DIE);
        cur_die = sib_die;
        dwarf_tag(cur_die, &type_tag, errp);
    }
    dwarf_dealloc(dbg, cur_die, DW_DLA_DIE);
}

