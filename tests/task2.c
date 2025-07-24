int main(void)
{
    bool ok = false;

    int a = 1, b = 2;
    if (a > 100 && b > 200)
        ok = true;
    else
    {
        for (int i = 1;; i++)
        {
            a += a * i;
            b += b * i;
            if (a > 100 && b > 200)
            {
                ok = true;
                break;
            }
        }
    }
    if (ok)
        printf("%d", a);
    return 0;
}
