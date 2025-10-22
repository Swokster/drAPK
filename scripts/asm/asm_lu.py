#!/usr/bin/env python3
import re, struct, pprint, sys
from OpCodes import FILE_HEADER, asm_to_code
'''
FUNC:  всё в квадратных скобках игнорируется. Формат строки задан жёстко.
CONST: номер переменной игнорируется (важен только их порядок), новые переменные можно вставлять внутри блока кода
код: содержимое строчки слева от ' ; ' игнорируется (важно: ';' должна выделяться пробелами)
комментарий: первым не пробельным символом в строке должен быть '#'
отладочная информация игнорируется
'''

DEBUG = 0

fname = sys.argv[1]
assert fname[-4:] == '.asm',  'Имя файла должно заканчиваться на .asm: %s'%fname
f_in = open(fname, 'r', encoding='utf-8')
fname_out = fname[:-4] + '.lu'  if len(sys.argv) < 3 else  sys.argv[2]
f_out = open(fname_out, 'wb')


def out_int(i):
    return struct.pack('<I', i)

def out_str(s):
    out = s.encode('utf-8') + b'\0'
    return out_int(len(out)) + out


consts = []
codes = []
func_levels = []    # стек, определяет сколько на каждом уровне иерархии осталось обработать функций

f_out.write(FILE_HEADER)
for line in f_in:
    line = line.rstrip()
    if DEBUG > 0:  print('LINE:', line)


    if line.startswith('FUNC '):
        m = re.match(r'FUNC \[[:\d ,]+\] \((.+)\) ;; ', line)
        assert m,  ['ERROR FUNC:', line]
        func_params = eval( m.group(1) )
        if DEBUG > 2:  print('func_params:', func_params)
        out = out_int(0) + struct.pack('<IIBBBB', *func_params)
        if DEBUG > 1:  print('out:', out)
        f_out.write(out)


    elif line.startswith('CONST '):
        # сначала надо выдать код, затем константы
        m = re.match(r'CONST \d+ (.+)', line)
        assert m,  ['ERROR CONST:', line]
        c = eval( m.group(1) )
        if DEBUG > 2:  print('m:', [c])
        if type(c) is float:
            out = b'\3' + struct.pack('<d', c)
        elif type(c) is str:
            out = b'\4' + out_str(c)
        else:
            out = {None:b'\0', False:b'\1\0', True:b'\1\1'}[c]
        if DEBUG > 1:  print('out:', out)
        consts.append(out)


    elif line.startswith('FUNCS_NUM: '):
        num = eval(line[11:])
        if DEBUG > 1:  print('FUNCS_NUM:', num)
        f_out.write(out_int(len(codes)))         # выдаём код, затем константы
        [ f_out.write(x)  for x in codes ]
        codes = []

        f_out.write(out_int(len(consts)))
        [ f_out.write(x)  for x in consts ]
        consts = []

        f_out.write(out_int(num))
        func_levels.append(num)
        while func_levels  and  func_levels[-1] == 0:
            [ f_out.write(out_int(0))  for _ in range(3) ]      # debug info. Это нужно вставить после кода/констант дочерних функций.
            func_levels.pop()
            if func_levels:
                func_levels[-1] -= 1


    elif line.lstrip().startswith('#'):
        continue


    elif ' ; ' in line:
        m = re.search(r' ; +(\w+ +[\d #-]+)$', line)
        codeline = m.group(1)
        if DEBUG > 2:  asm_to_code(codeline, debug=True)
        out = out_int( asm_to_code(codeline) )
        if DEBUG > 1:  print('out:', out)
        codes.append(out)


    else:
        assert line == '',  [line]


assert func_levels == [],  func_levels
