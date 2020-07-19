#include "test.h"

int main(int argc, char** argv){
    
	enum weekday {monday, sunday} mday;
	enum flag {val1=4, val2=8} mflag;
	union data {int i;float f;char* p[10];char str[20][10];} mdata; 
	
	union data2 {int i;float f;char* p[10];char str[20][10];}; 

	int a;
	a = foo(a);

    int b;
	b = remove_func();

    int c;
    struct remove_field_struct d;
    d.remove_field = 1;
	c = remove_field_func(d);
	
	return 0;
}
