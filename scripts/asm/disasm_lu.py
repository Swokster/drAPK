#!/usr/bin/env python3
import re, struct, pprint, sys, collections
from OpCodes import opcodes, FILE_HEADER, asm_to_code

SHOW_CONSTS = False         # -c
DEBUG = 0                   # -d
HEX_EDITOR_VALUES = False   # -x
CONCISE = False             # -C
USE_BRACKET_FOR_AND = False # -b    Нужна ли скобка в выражениях типа   (A and B) or C
SEPARATE_IFS = 0            # -s
TEST = False                    # -t  (undocumented)

def f_init():
    global SHOW_CONSTS, DEBUG, HEX_EDITOR_VALUES, CONCISE, USE_BRACKET_FOR_AND, SEPARATE_IFS, TEST, f_in, f_out
    names = sys.argv[1:]
    if '-c' in names:  SHOW_CONSTS ^= True
    if '-d' in names:  DEBUG = 99
    if '-x' in names:  HEX_EDITOR_VALUES ^= True
    if '-C' in names:  CONCISE ^= True
    if '-b' in names:  USE_BRACKET_FOR_AND ^= True
    if '-s' in names:  SEPARATE_IFS ^= 2
    if '-t' in names:  TEST ^= True
    names = [ s  for s in names  if s not in ('-c', '-d', '-x', '-C', '-b', '-s', '-t') ]
    if not names:
        print('Usage:  %s  [-c] [-d] [-x] [-C] [-b] [-s]  filename.lu  [filename_out|-]\n\n'
                '-c -- to show constants (required for future assemble)\n'      '-d -- enable debugging\n'
                '-x -- include hex code\n'      '-C -- concise output\n'        '-b -- use brackets for AND operators\n'
                '-s -- separate IFs for AND/OR operators' % sys.argv[0])
        exit(0)

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


### Работа с Lu-файлом закончена, дальше анализ.


def calc_indents(codelines, separate_ifs=False, restrict='', else_pos=None):
    ''' Расчёт форматирования отступами. Участвует в разделения if. restrict ограничивает расчёт дерева логики указанным регистром и операторами Test. '''
    ''' В lua-5.1 нет CONTINUE. Только BREAK. '''
    c = codelines
    gotoes = collections.defaultdict(set)   # {'FORStart': {3}, 'FORend': {12}, 'TFor': {20}, 'if': {7}, 'jmp': {8, 9, 16, 21}}
    cycles = []     # список начальных и конечных (включительно) позиций циклов [[3, 14], [18, 23], [24, 29], [30, 34]]
    for i,line in enumerate(c):
        if line.gotoes[0]:              # варианты значений line.gotoes: ['',0],  ['jmp',-5],  ['if',1]
            line.gotoes[1] += i+1
            gotoes[ line.gotoes[0] ].add( i )
            c[ line.gotoes[1] ].is_label = True
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
    if separate_ifs:
        ifs = collections.defaultdict(list)     # таблица переходов IF:  {('Test  0 0', 3): [1], ('Test  0 0', 7): [4], ('Test  0 1', 6): [1, 4]}
    stack = []      # стек переходов if:  [(7, 12), (25, 30), (36, 42), (40, 45), (43, 48)]
    for i in set( gotoes['if'] ):  # i - номер строки с IF;  j - куда переходит i+1 jmp;  если есть ELSE, на j-1 месте должен быть jmp
        assert i+1 in gotoes['jmp']
        x,j = c[i+1].gotoes
        assert i < j,  [i,j]
        for _ in range(i+2, j):  c[_].indent += 1
        gotoes['if'] -= {i}
        gotoes['jmp'] -= {i+1}
        stack.append( (i,j) )

        if separate_ifs  and  not c[i].simple.startswith('TestSet  '):      # возможность разделения напрямую не применима для TestSet из-за  R(A) := R(B)
#           print(i, [c[i].simple, c[i+1].simple, c[i].gotoes, c[i+1].gotoes])
            if c[i].simple[:4] in ('EQ  ','LT  ','LE  '):       # 'LT  1 1 0'  ->  'LT  0 1 0'
                tmp = c[i].simple.split(' ')
                tmp[2] = {'0':'1', '1':'0'}[tmp[2]]
                reversed_if = ' '.join(tmp)
            else:                                               # 'Test  0 1' --> 'Test  0 0'
                assert c[i].simple.startswith('Test  ')
                assert c[i].simple[-2:] in (' 0',' 1'),  [c[i].simple, c[i].full]
                reversed_if = c[i].simple[:-1] + {'0':'1', '1':'0'}[ c[i].simple[-1] ]
            ifs[ c[i].simple, c[i].gotoes[1] ].append(i)
            if 0:                                               # TODO: Можно удалить. Осталось от предыдущих вариантов.
                ifs[ c[i].simple, i ].append(i)
                ifs[ reversed_if, i ].append(i)
            c[i+1].rev = ifs[ reversed_if, c[i+1].gotoes[1] ]
            c[i+1].rev.append(i)

    TTT = False
    if separate_ifs:
        if TTT:  print('ifs:', pprint.pformat(ifs))
        jmp_fix = {}        # {5: -2, 86: -6, 94: -6}
        if TTT:  print('SEPARATING:', pprint.pformat(else_pos, width=10**99, compact=True))  # {1: 4, 4: 13, 7: 13, 10: 13, 13: 15}
        for i,c_ in enumerate(c):
            if hasattr(c_, 'rev'):
                if TTT:  print('  c[%i].rev:' % i, c_.rev)
                assert c[i].gotoes[0] == 'jmp'  and  c[i-1].gotoes[0] == 'if'
                if i < max(c_.rev):
#                   jmp_fix[i] = max(c_.rev) - c_.gotoes[1]
                    new_array = [ x  for x in c_.rev  if x >= else_pos[i-1] ]
                    if TTT:  print('  NEW_ARRAY:', new_array)
                    if new_array:
                        jmp_fix[i] = min(new_array) - c_.gotoes[1]
                        if min(new_array) != else_pos[i-1]:  # ???  339/libs.enemies.lu  694/lib.interface.list.ui_cooking.lu  694/lib.location_master.lu
                            print('  ERROR? relocate jmp:', new_array, else_pos[i-1], file=sys.stderr)
                        if TTT:  print('    JMP_FIX:', i, else_pos[i-1], jmp_fix[i], c_.rev, c_.gotoes[1])
        if 0 or DEBUG:  print('#jmp_fix:', jmp_fix, file=f_out)
        return jmp_fix


    # оставшиеся jmp должны быть else (есть исключения)
    gotoes['fix_jmp'] = {}      # TODO: переименовать.
    for i in set( gotoes['jmp'] ):
        j = c[i].gotoes[1]
        assert i < j,  [i,j]
        if i+1 in [ j  for i,j in stack ]:
            c[i].indent -= 1
            c[i].full = 'ELSE: ' + c[i].full
            gotoes['jmp'] -= {i}
            gotoes['else'].add(i+1)
            for k,l in stack:       # Находим jmp, которые должны указывать на другие jmp(else). Может потребоваться повторный прогон.
                if i+1 == l:
                    for m in range(k,i):
                        if c[m].gotoes == c[i].gotoes:
                            gotoes['fix_jmp'][m] = i - j
        elif i+2 in [ j  for i,j in stack ]  and c[i+1].gotoes == ['LoadB1',i+3]:     # else на второй LoadB0 из пары
            c[i].indent -= 1
            c[i].full = 'ELSE2: ' + c[i].full
            gotoes['jmp'] -= {i}
            gotoes['else'].add(i+2)
        else:
            c[i].full = 'IF-TRUE-ELSE: ' + c[i].full    # в конструкции if true then ... оператор if опускается, остаётся только else (даже если пустой).
        for _ in range(i+1, j):  c[_].indent += 1

    # разбиваем на блоки и выводим в постфиксном формате:  [(1, 9), (4, 9), (12, 20), (15, 23), (18, 23)]  -->  [[9, '1 4 y9'], [23, '12 15 18 y23 x20']]
    stack2, stack2_tmp = [], []
    if TEST or DEBUG:  print('#stack:', sorted(stack), file=f_out)
    for j,i in sorted(stack):   # i - куда, j - откуда
        assert i >= j+2
        if restrict  and  c[j].simple.split()[:2] != ['Test',restrict]:  continue   # ограничиваемся только Test со вспомогательным регистром
        while stack2  and  stack2[-1][0] < j+2:     # временно переносим блоки, уже не способные на объединение
            stack2_tmp.append(stack2.pop())
        stack2.append([i, str(j)])
        while len(stack2) > 1:
            if stack2[-2][0] == j+2:
                if DEBUG:  print('#ОбъединяемX:', stack2, file=f_out)
#               stack2[-1][1] = '%s %s x%s' % (stack2[-2][1], stack2[-1][1], stack2[-1][0])
                stack2[-1][1] = '%s %s x%s' % (stack2[-2][1], stack2[-1][1], j+2)
                stack2.pop(-2)
                if DEBUG:  print('#   --->     ', stack2, file=f_out)
                continue
            if stack2[-2][0] == stack2[-1][0]:
                if DEBUG:  print('#ОбъединяемY:', stack2, file=f_out)
                stack2[-2][1] += ' %s y%s' % (stack2[-1][1], stack2[-1][0])
                stack2.pop(-1)
                if DEBUG:  print('#   --->     ', stack2, file=f_out)
                continue
            break
    stack2.extend(stack2_tmp);  del stack2_tmp

    # переводим из постфиксной в инфиксную:  '1 4 y18 7 y18 10 13 y21 16 y21 x18 19 x21'  -->  '1 and 4 and 7 and (~10 or ~13 or ~16) or 19'
    if 1:
        OPS = {True:' or ', False:' and '}
        def tree_to_str(tree, op, lvl=0, tilda=False):
            if not tree['op']:  return ('','~')[tilda] + tree['num']
            tildas = [op] * (len(tree['num']) - 1)  +  [tilda]
            s = [ tree_to_str(t, not op, lvl+1, tld)  for t,tld in zip(tree['num'], tildas) ]
            return ('(%s)'  if (USE_BRACKET_FOR_AND or op) and lvl else  '%s') % OPS[op].join(s)
#       stack2 = [[18, '1 4 y18 7 y18 10 13 y21 16 y21 x18 19 x21']]

        def else_positions(postfix):
            ''' '1 4 y18 7 y18 10 13 y21 16 y21 x18 19 x21' -->  {1: 4, 4: 7, 7: 16, 10: 13, 13: 16, 16: 19, 19: 21} '''
#           print('postfix:', postfix)
            stack = [];  out = {};  last_x = None
            for x in postfix.split():
                if x[0] in 'xy':
                    out[ stack.pop(-2) ] = last_x
                else:
                    last_x = int(x)
                    stack.append(last_x)
            assert stack == [ last_x ],  stack
            out[last_x] =  last_x + 2
#           print('postfix out:', pprint.pformat(out))
            return out

        if TEST or DEBUG:  print('#stack2:', stack2, file=f_out)
        else_pos = {}
        for n,(i,j) in enumerate(stack2):
#           print('i,j:', [i,j])
            else_pos.update( else_positions(j) )
            stack3 = []
            for v in j.split(' '):
                if v[0] not in 'xy':  stack3.append({'op':None, 'num':v});  continue
                val2 = stack3.pop()
                val1 = stack3.pop()
                if val1['op'] != v[1:]:  val1 = {'op':v[1:], 'num':[val1]}
                val1['num'].append(val2)
                stack3.append(val1)
            assert len(stack3) == 1,  stack3
#           pprint.pprint(stack3)
            top_is_or = j.split(' ')[-1][0] == 'x'
            stack2[n][1] = out = tree_to_str(stack3[0], top_is_or)
            if TEST or DEBUG:  print('# -- i,j,out:', [i, j, out], file=f_out)
#       print('else_pos:', pprint.pformat(else_pos))


    if DEBUG:
        for i,j in cycles:
            c[i].comment = c[j+1].comment = ''
    for i,j in stack2:
        if ' ' in j:
            c[i].comment = ''
#       if DEBUG:  print('#', [i, j], file=f_out)
    for i,j in stack2:  # отдельным циклом, чтобы наверняка не было перекрытия с предыдущими
        if ' ' in j:
            k = re.findall(r'\d+', j)
            c[ int(k[0]) ].comment = '\t# %s: %s' % (i,j)

    gotoes = { x:y  for x,y in gotoes.items()  if y }
    if 0 or DEBUG:
        print('#blocks:', sorted(cycles), file=f_out)
#       print('#stack: ', sorted(stack), file=f_out)
        print('#stack2:', stack2, file=f_out)
    if TEST or DEBUG  or  'jmp' in gotoes:
        if not CONCISE:  print('#gotoes:', gotoes, file=f_out)
    return stack2, gotoes.get('fix_jmp', {}), else_pos


def substitute_code(list_code, codelines, ifs):
    ''' ifs:  [(0, 'Move 99 1', 'Test 99 1'), (2, 'Move 99 2', 'Test 99 0')]  ДОЛЖЕН быть отсортирован по возрастанию.'''
    for i,line in enumerate(codelines):     # правим ссылки jmp, for*   ДО вставок;  у них надо изменить только правое значение
        c = line.simple.split()
        if c[0] in ('jmp', 'ForPrep', 'ForLoop'):
            c[-1] = int(c[-1])
            n = i+1 + c[-1]         # i - откуда переход,  n - куда
            for ops in ifs:
                if i < ops[0] < n:      c[-1] += len(ops[2:])
                elif n <= ops[0] < i:   c[-1] -= len(ops[2:])
            c[-1] = str(c[-1])
            list_code[i] = asm_to_code(' '.join(c))

    for ops in ifs[::-1]:
        list_code.pop(ops[0])        # удаляем исходный код, затем вставляем всё из ifs[][1:] в обратном порядке
        for op in ops[:0:-1]:
            list_code.insert(ops[0], asm_to_code(op))


def unify_ifs(list_code, codelines, free_r, logic_ops):
    ''' Подменяем все IF на Test. А также подчиняемся структуре отрицаний из logic_ops (можно полностью инвертировать). '''
    needs = {}                  # {0: '1', 2: '0', 8: '0'}
    for _,ops in logic_ops:                                 # [[11, '(~0 or 2) and 4 and 6 and 8']]
        for tilda,n in re.findall(r'(~?)(\d+)', ops):
            needs[int(n)] = {'~':'1', '':'0'}[tilda]    # так  выглядят лучше  if A and/or B ... then
#           needs[int(n)] = {'~':'0', '':'1'}[tilda]    # так  x = A and B or C  выглядит лучше
#   print('#logic_ops:', logic_ops)

    ifs = []        #  [(0, 'Move 99 1', 'Test 99 1'), (2, 'Move 99 2', 'Test 99 0')]
    for i,line in enumerate(codelines):
        c = line.simple.split()
        if i not in needs  and  codelines[i].gotoes[0] == 'if'  and  re.match(r'jmp  -\d+$', codelines[i+1].simple):    # repeat-until
            if TEST or DEBUG:  print('REPEAT-UNTIL. Miss in needs:', [i, codelines[i].full, codelines[i+1].full], file=sys.stderr)
            needs[i] = '0'
        if c[0] == 'Test':                  # 'Test  4 1'
            ifs.append((i, '%s %s %s' % ('Move' if needs[i] == c[2] else 'NOT',free_r,c[1]), 'Test %s %s' % (free_r,needs[i])))
        elif c[0] in ('EQ','LT','LE'):      # 'EQ  1 3 4'
            t0,t1 = {'0':(0,1), '1':(1,0)}[ needs[i] ]
            ifs.append((i, ' '.join(c), 'jmp 1', 'LoadBool %s %s 1'%(free_r,t1), 'LoadBool %s %s 0'%(free_r,t0), 'Test %s %s'%(free_r,t0)))
        elif c[0] == 'TestSet':             # 'TestSet  3 5 1'
            if 0:
                tmp = (i, 'Test %s %s' % (c[2],   {'0':'1', '1':'0'}[c[3]]), 'jmp 1', 'Move %s %s' % (c[1],c[2]))
                ifs.append(tmp + ('%s %s %s' % ('Move' if needs[i] == c[3] else 'NOT',free_r,c[2]), 'Test %s %s' % (free_r,needs[i])))
            else:
                tmp = (i, 'Test %s %s' % (c[2],   {'0':'1', '1':'0'}[c[3]]), 'jmp 2', 'Move %s %s' % (c[1],c[2]))
                ifs.append(tmp)

    if 0:  pprint.pprint(ifs)
    substitute_code(list_code, codelines, ifs)


def get_func(f_in):
    global file_offset, total_funcs
    func_name = get_str(f_in)
    file_offset += 12
    func_params = list( struct.unpack('<IIBBBB', f_in.read(12)) )
    if CONCISE:
        func_params = func_params[2:]   # чтобы при сравнении файлов не было различий из-за нумерации строк исходного кода
    if SEPARATE_IFS:
        func_params[-1] += 1            # нужен один свободный регистр для присваивания
    fn = '[%s: %s]' % (total_funcs, str(func_numbers)[1:-1])
    print('\nFUNC', fn, tuple(func_params), ';; #upvalues, #parameters, 1=VARARG_HASARG|2=VARARG_ISVARARG|4=VARARG_NEEDSARG, #registers', file=f_out)
    if func_name:
        print('#func_name:', func_name.__repr__(), file=f_out)
    code_offset = file_offset + 4       # +4, т.к. ещё читается int - число операторов в коде

    list_code = get_code(f_in)
    list_consts = get_consts(f_in)
    auxiliary_reg = ''                    # в режиме разделения if добавляем вспомогательный регистр
    if SEPARATE_IFS:
        def jmp_adjust(fix_adj):    # {80: -2, 83: -2, 75: -2, 86: -2, 78: -2}
            for i,adj in fix_adj.items():
                n = list_code[i]
                list_code[i] = opcodes[ n & 0x3F ].adjust(n, adj)
        while True:
            code = [ disasm(x, list_consts)  for x in list_code ]
            logic_ops,fix_jmp,_ = calc_indents(code, restrict='')
            if not fix_jmp:  break
            if 1 and TEST:  print('#fix_jmp:', fix_jmp, file=f_out)
            jmp_adjust(fix_jmp)
#       print('#logic_ops:', logic_ops)
        auxiliary_reg = str(func_params[-1] - 1)
        unify_ifs(list_code, code, auxiliary_reg, logic_ops)
        if SEPARATE_IFS > 1:
            code = [ disasm(x, list_consts)  for x in list_code ]
            logic_ops,fix_jmp,else_pos = calc_indents(code, restrict='')
#           while True:
            for _ in range(100):
                code = [ disasm(x, list_consts)  for x in list_code ]
                adj = calc_indents(code, separate_ifs=True, else_pos=else_pos)
                if not adj:  break
                if _ > 0:  print('ERROR?  #adj:', adj, file=sys.stderr)
                if 1 and TEST:  print('#adj:', adj, file=f_out)
                jmp_adjust(adj)
 #              break
    code = [ disasm(x, list_consts)  for x in list_code ]
    calc_indents(code, restrict=auxiliary_reg)
    for i,(x,c) in enumerate(zip(list_code, code)):
        if not CONCISE:
            if hasattr(c, 'comment'):  print(c.comment, file=f_out)
            if HEX_EDITOR_VALUES:
                print('%5x %8x ' % (code_offset + 4*i, x), end='', file=f_out)
            print('%-4s ' % ('%s:'%i  if SHOW_CONSTS or hasattr(c,'is_label') else  ''), end='', file=f_out)
            print('%-8s %3s   ' % tuple(c.gotoes), end='', file=f_out)
            print('.   '*c.indent, '%-60s'%c.full, ' ; ', c.simple, sep='', file=f_out)
        else:
            print('   '*c.indent, c.full, sep='', file=f_out)


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
