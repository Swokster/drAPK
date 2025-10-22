#!/usr/bin/env python3
import re, struct, pprint, sys, collections
from OpCodes import opcodes, FILE_HEADER

SHOW_CONSTS = False         # -c
DEBUG = 0                   # -d
HEX_EDITOR_VALUES = False   # -x
CONCISE = False             # -C

def f_init():
    global SHOW_CONSTS, DEBUG, HEX_EDITOR_VALUES, CONCISE, f_in, f_out
    names = sys.argv[1:]
    if '-c' in names:  SHOW_CONSTS = True
    if '-d' in names:  DEBUG = 99
    if '-x' in names:  HEX_EDITOR_VALUES = True
    if '-C' in names:  CONCISE = True
    names = [ s  for s in names  if s not in ('-c', '-d', '-x', '-C') ]
    if not names:  print('usage:  %s  [-c] [-d] [-x] [-C]  filename.lu  [filename_out|-]\n-c -- to show constants (required for future assemble)\n-d -- enable debugging\n-x -- include hex code\n-C -- concise output' % sys.argv[0]);  exit(0)

    fname = names[0]
    assert fname[-3:] == '.lu',  'Имя файла должно заканчиваться на .lu: %s'%fname
    f_in = open(fname, 'rb')
    if len(names) > 1:
        f_out = open(names[1], 'w', encoding='utf-8')  if names[1] != '-' else  sys.stdout
    else:
        f_out = open(fname[:-3] + '.asm', 'w', encoding='utf-8')
f_init()


file_header = f_in.read(12)
assert FILE_HEADER == file_header,  file_header
file_offset = 12


def get_int(f_in):     # unsigned int
    global file_offset
    file_offset += 4
    return struct.unpack('<I', f_in.read(4)) [0]

def get_str(f_in):
    global file_offset
    slen = get_int(f_in)
    if slen==0:  return None    # это не настоящий тип None, а признак несуществующей строки
    file_offset += slen
    s = f_in.read(slen)
    assert s[-1] == 0,  s
    return s[:-1].decode('utf-8')


def disasm(code, consts):
    op = code & 0x3F
    return opcodes[op].disasm(code, consts)

def get_code(f_in):
    code_len = get_int(f_in)
    code = [ get_int(f_in)  for _ in range(code_len) ]
    assert code[-1] == 8388638,  code[-1]   # стандартный 'Return 0 1 0'
#    return code[:-1]
    return code


def get_consts(f_in):
    def get_one_const(f_in):
        global file_offset
        file_offset += 1
        c_type = ord( f_in.read(1) )
        if c_type == 0:
            return None
        elif c_type == 1:
            file_offset += 1
            b = ord( f_in.read(1) )
            assert b in (0,1),  b
            return bool(b)
        elif c_type == 3:
            file_offset += 8
            return struct.unpack('<d', f_in.read(8))[0]
        elif c_type == 4:
            return get_str(f_in)
        else:
            assert False,  [c_type]
    consts_num = get_int(f_in)
    consts = [ get_one_const(f_in)  for _ in range(consts_num) ]
    if SHOW_CONSTS:
        for i,v in enumerate(consts):
            print('CONST', i, v.__repr__(), file=f_out)
    return consts


def calc_indents(codelines):
    '''В lua-5.1 нет CONTINUE. Только BREAK.'''
    c = codelines
    gotoes = collections.defaultdict(set)   # {'FORStart': {3}, 'FORend': {12}, 'TFor': {20}, 'if': {7}, 'jmp': {8, 9, 16, 21}}
    cycles = []     # список начальных и конечных (включительно) позиций циклов [[3, 14], [18, 23], [24, 29], [30, 34]]
    stack = []      # стек переходов if:  [(7, 12), (25, 30), (36, 42), (40, 45), (43, 48)]
    for i,line in enumerate(c):
        if line.gotoes[0]:              # варианты значений line.gotoes: ['',0],  ['jmp',-5],  ['if',1]
            line.gotoes[1] += i+1
            gotoes[ line.gotoes[0] ].add( i )
        else:
            line.gotoes[1] = ''

    for i in set( gotoes['FORStart'] ):    # i - номер строки с FORStart;  j - FORend;   jmp отсутствуют
        j = c[i].gotoes[1]
        assert j > i
        x,k = c[j].gotoes
        assert x == 'FORend'
        assert k == i+1
        for _ in range(i+1, j+1):  c[_].indent += 1
        cycles.append([i,j])
        gotoes['FORend'] -= {j}
        gotoes['FORStart'] -= {i}
    assert gotoes['FORend'] == set()

    for i in set( gotoes['TFor'] ):    # i - номер строки с TFOR;  в i+1 д.б. jmp с отрицат.смещением;  j - начало цикла;  j-1 - первый jmp на TFOR
        x,j = c[i+1].gotoes
        assert x == 'jmp'
        assert j < i
        assert c[j-1].gotoes == ['jmp', i]
        for _ in range(j, i+2):  c[_].indent += 1
        cycles.append([j-1,i+1])
        gotoes['jmp'] -= {i+1, j-1}
        gotoes['TFor'] -= {i}
        c[j-1].full = 'TFOR:  ' + c[j-1].full

    for i in set( gotoes['jmp'] ):  # Обработка while, repeat-until. Все они оканчиваются jmp с отрицат.смещением.
        j = c[i].gotoes[1]
        if j > i:  continue
        for _ in range(j+1, i+1):  c[_].indent += 1
        cycles.append([j,i])
        gotoes['jmp'] -= {i}
        if c[i-1].gotoes[0] == 'if':    # repeat-until
            gotoes['if'] -= {i-1}
            c[j].full = 'REPEAT: ' + c[j].full
        else:                           # while. Внутренний if исполняет роль break.
            c[j].full = 'WHILE: ' + c[j].full

    for i in set( gotoes['jmp'] ):
        for j,k in cycles:
            if j < i < k  and  c[i].gotoes[1] == k+1:
                c[i].full = 'BREAK: ' + c[i].full
                if c[i-1].gotoes != ['if', i+1]:        # удаляем одинокие break (не являющиеся частью while: там if-jmp)
                    gotoes['jmp'] -= {i}

    # Остались только if с положит.смещением и одинокие jmp-else.
    for i in set( gotoes['if'] ):  # i - номер строки с IF;  j - куда переходит i+1 jmp;  если есть ELSE, на j-1 месте должен быть jmp
        assert i+1 in gotoes['jmp']
        x,j = c[i+1].gotoes
        assert i < j,  [i,j]
        for _ in range(i+2, j):  c[_].indent += 1
        gotoes['if'] -= {i}
        gotoes['jmp'] -= {i+1}
        stack.append( (i,j) )

    # оставшиеся jmp должны быть else (есть исключения)
    for i in set( gotoes['jmp'] ):
        j = c[i].gotoes[1]
        assert i < j,  [i,j]
        if i+1 in [ j  for i,j in stack ]:
            c[i].indent -= 1
            c[i].full = 'ELSE: ' + c[i].full
            gotoes['jmp'] -= {i}
            gotoes['else'].add(i+1)
        elif i+2 in [ j  for i,j in stack ]  and c[i+1].gotoes == ['LoadB1',i+3]:     # else на второй LoadB0 из пары
            c[i].indent -= 1
            c[i].full = 'ELSE2: ' + c[i].full
            gotoes['jmp'] -= {i}
            gotoes['else'].add(i+2)
        else:
            c[i].full = 'IF-TRUE-ELSE: ' + c[i].full    # в конструкции if true then ... оператор if опускается, остаётся только else (даже если пустой).
        for _ in range(i+1, j):  c[_].indent += 1

    stack2 = []
    if DEBUG:
        print('STACK:', sorted(stack))
    for j,i in sorted(stack):   # i - куда, j - откуда
        stack2.append([i, str(j)])
        while len(stack2) > 1:
            if stack2[-2][0] == j+2:
                if DEBUG:
                    print('ОбъединяемX:', stack2)
                stack2[-1][1] = '%s %s x' % (stack2[-2][1], stack2[-1][1])
                stack2.pop(-2)
                if DEBUG:
                    print('   --->     ', stack2)
                continue
            if stack2[-2][0] == stack2[-1][0]:
                if DEBUG:
                    print('ОбъединяемY:', stack2)
                stack2[-2][1] += ' %s y' % stack2[-1][1]
                stack2.pop(-1)
                if DEBUG:
                    print('   --->     ', stack2)
                continue
            break


    if DEBUG:
        for i,j in cycles:
            c[i].comment = c[j+1].comment = ''
    for i,j in stack2:
        if ' ' in j:
            c[i].comment = ''
        if DEBUG:  print('#', [i, j], file=f_out)
    for i,j in stack2:  # отдельным циклом, чтобы наверняка не было перекрытия с предыдущими
        if ' ' in j:
            k = re.findall(r'\d+', j)
            c[ int(k[0]) ].comment = '\t# %s: %s' % (i,j)

    gotoes = { x:y  for x,y in gotoes.items()  if y }
    if 0 or DEBUG:
        print('#blocks:', sorted(cycles), file=f_out)
        print('#stack: ', sorted(stack), file=f_out)
        print('#stack2:', stack2, file=f_out)
    if 0 or DEBUG  or  'jmp' in gotoes:
        print('#gotoes:', gotoes, file=f_out)


def get_func(f_in):
    global file_offset, total_funcs
    func_name = get_str(f_in)
    file_offset += 12
    func_params = struct.unpack('<IIBBBB', f_in.read(12))
    fn = '[%s: %s]' % (total_funcs, str(func_numbers)[1:-1])
    print('\nFUNC', fn, func_params, ';; #upvalues, #parameters, 1=VARARG_HASARG|2=VARARG_ISVARARG|4=VARARG_NEEDSARG, #registers', file=f_out)
    if func_name:
        print('#func_name:', func_name.__repr__(), file=f_out)
    code_offset = file_offset + 4       # +4, т.к. ещё читается int - число операторов в коде

    list_code = get_code(f_in)
    list_consts = get_consts(f_in)
    code = [ disasm(x, list_consts)  for x in list_code ]
    calc_indents(code)
    for i,(c,x) in enumerate(zip(list_code, code)):
        if not CONCISE:
            if hasattr(x, 'comment'):  print(x.comment, file=f_out)
            if HEX_EDITOR_VALUES:
                print('%5x %8x ' % (code_offset + 4*i, c), end='', file=f_out)
            print('%3i.'%i, ' %-8s %3s   '%tuple(x.gotoes), end='', file=f_out)
            print('.   '*x.indent, '%-60s'%x.full, ' ; ', x.simple, sep='', file=f_out)
        else:
            print('   '*x.indent, '%s'%x.full, sep='', file=f_out)


    total_funcs += 1
    func_numbers.append(0)
    funcs_num = get_int(f_in)
    if SHOW_CONSTS:
        print('FUNCS_NUM:', funcs_num, file=f_out)
    list_funcs = [ get_func(f_in)  for i in range(funcs_num) ]
    func_numbers.pop()
    func_numbers.append(1 + func_numbers.pop())


    ### DEBUG INFO:
    source_line_positions_num = get_int(f_in)
    source_line_positions = [ get_int(f_in)  for i in range(source_line_positions_num) ]
    if source_line_positions:
        print('#source_line_positions:', source_line_positions, file=f_out)

    local_vars_num = get_int(f_in)
    local_vars = [ (get_str(f_in), get_int(f_in), get_int(f_in))  for i in range(local_vars_num) ]
    if local_vars:
        print('#local_vars:', local_vars, file=f_out)

    upvalues_num = get_int(f_in)
    upvalues = [ get_str(f_in)  for i in range(upvalues_num) ]
    if upvalues:
        print('#upvalues:', upvalues, file=f_out)


func_numbers = [0]
total_funcs = 0
get_func(f_in)
