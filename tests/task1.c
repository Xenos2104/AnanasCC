struct Student
{
    char* name;
    int num;
    int age;
    float score[5];
};

void main()
{
    int sum = 0;
    Student li = {"Li ping", 5, 18, {80, 90, 100, 86, 95}};
    for (int i = 0; i < 5; i++)
        sum += li.score[i];
    printf("%d ", sum);
}