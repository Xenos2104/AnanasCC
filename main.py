from compiler import Compiler

if __name__ == '__main__':
    compiler = Compiler('output')
    compiler.compile('main.c', execute=True)
    compiler.save('temp')
