int foo(int);

int remove_func();

struct remove_field_struct{
    int i;
    long j;
    double k;
    struct remove_field_struct* p;
    int remove_field;
};
int remove_field_func(struct remove_field_struct);
