int add(int x, int *y);

int add(int a, int *b)
{
    return a + *b;
}

struct Apple
{
    char color;
    Apple* size;
    char* name;
};

enum Bool
{
    TRUE = 0,
    FALSE
};

int a = 1;
int arr[3] = {1, 2, 3};

float get_pi(float x)
{
    if (x != 3.14)
        return 3.14;
    else
        return x;

    int i = 10;
    while (i--)
    {
        if (i > 5)
            continue;
        if (i == 1)
            return 3.14;
        else
        {
            break;
        }
    }
}

bool test()
{
    int a = 10, d = 3;
    int* b = &a;
    *b = 20;
    int c;
    if (a > 20)
        c = 3;
    else if (a == 10)
        c = 2;
    else
        c = 1;

    if (a++, d++, a == d);
    int arr[10];
    for (int i = 0; i < 10; i++)
        arr[i] = i;

    Apple apple = {'c', nullptr, "菠萝"};
    apple.name = "苹果";

    return c == add(a, b);
}

int main(void)
{
    Bool a;
    if (test())
        a = 1;
    else
        a = 0;
    return a;
}
