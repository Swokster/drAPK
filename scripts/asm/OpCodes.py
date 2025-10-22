#!/usr/bin/env python3

FILE_HEADER = b'\x1bLuaQ\x00\x01\x04\x04\x04\x08\x00'

#import collections
#Code = collections.namedtuple('CodeLine', 'full simple gotoes indent')
class Code:
    def __init__(self, full, simple, gotoes=['',0]):
        self.full = full
        self.simple = simple
        self.gotoes = list(gotoes)
        self.indent = 0



class OpCode:
    def __init__(self, name):
        self.name = name

    def unpack_abc(self, code, consts):
        a = (code >> 6) & 0xFF
        c = (code >> 14) & 0x1FF
        b = (code >> 23) & 0x1FF
        bx = code >> 14
        sbx = (code >> 14) - 131071
        return a,b,c, bx,sbx

    def unpack(self, code, consts):
        a,b,c,bx,sbx = self.unpack_abc(code, consts)
#        simple = op_short[code & 0x3F].disasm(code, consts)
        simple = self.simple_disasm(code, consts)
        return a,b,c, bx,sbx, simple

# ----------------- ----------------- ----------------- -----------------

class ABC(OpCode):
    def simple_disasm(self, code, consts):
        a,b,c,bx,sbx = self.unpack_abc(code, consts)
        if 1:
            if b>=256:  b = '#%i' % (b-256)
            if c>=256:  c = '#%i' % (c-256)
        else:
            if b>=256:  b = consts[b-256].__repr__()
            if c>=256:  c = consts[c-256].__repr__()
        return '%s  %i %s %s' % (self.name, a, b, c)

    def asm(self, i, args):
        assert 3 == len(args),  args
        a,b,c = args
        return i + (a<<6) + (b<<23) + (c<<14)

class AB0C(OpCode):
    def simple_disasm(self, code, consts):
        a,b,c,bx,sbx = self.unpack_abc(code, consts)
        assert b==0, b
        if 1:
            if c>=256:  c = '#%i' % (c-256)
        else:
            if c>=256:  c = consts[c-256].__repr__()
        return '%s  %i %s' % (self.name, a, c)

    def asm(self, i, args):
        assert 2 == len(args),  args
        a,c = args
        return i + (a<<6) + (c<<14)

class ABC0(OpCode):
    def simple_disasm(self, code, consts):
        a,b,c,bx,sbx = self.unpack_abc(code, consts)
        assert c==0, c
        if 1:
            if b>=256:  b = '#%i' % (b-256)
        else:
            if b>=256:  b = consts[b-256].__repr__()
        return '%s  %i %s' % (self.name, a, b)

    def asm(self, i, args):
        assert 2 == len(args),  args
        a,b = args
        return i + (a<<6) + (b<<23)

class AB0C0(OpCode):
    def simple_disasm(self, code, consts):
        a,b,c,bx,sbx = self.unpack_abc(code, consts)
        assert (b,c) == (0,0),  (b,c)
        return '%s  %i' % (self.name, a)

    def asm(self, i, args):
        assert 1 == len(args),  args
        a = args[0]
        return i + (a<<6)

class ABx(OpCode):
    def simple_disasm(self, code, consts):
        a,b,c,bx,sbx = self.unpack_abc(code, consts)
        return '%s  %i %i' % (self.name, a, bx)

    def asm(self, i, args):
        assert 2 == len(args),  args
        a,bx = args
        return i + (a<<6) + (bx<<14)

class AsBx(OpCode):
    def simple_disasm(self, code, consts):
        a,b,c,bx,sbx = self.unpack_abc(code, consts)
        return '%s  %i %i' % (self.name, a, sbx)

    def asm(self, i, args):
        assert 2 == len(args),  args
        a,sbx = args
        sbx += 131071
        return i + (a<<6) + (sbx<<14)

class A0sBx(OpCode):
    def simple_disasm(self, code, consts):
        a,b,c,bx,sbx = self.unpack_abc(code, consts)
        assert a==0, a
        return '%s  %i' % (self.name, sbx)

    def asm(self, i, args):
        assert 1 == len(args),  args
        sbx = args[0] + 131071
        return i + (sbx<<14)

# ----------------- ----------------- ----------------- -----------------

class OpMove(ABC0):
    def disasm(self, code, consts):     # MOVE  A B   R(A) := R(B)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c==0,  c
        return Code('r%i = r%i' % (a, b), simple)

class OpLoadK(ABx):
    def disasm(self, code, consts):     # LOADK  A Bx   R(A) := Kst(Bx)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        bx_ = consts[bx].__repr__()
        return Code('r%i = %s' % (a, bx_), simple)

class OpLoadBool(ABC):
    def disasm(self, code, consts):     # LOADBOOL  A B C   R(A) := (Bool)B; if (C) PC++
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert b in {0,1},  b
        assert c in {0,1},  c
        b_ = bool(b)
        c_ = ', PC++'  if c else  ''
        return Code('r%i = %s %s' % (a, b_, c_), simple, ['LoadB1',1] if c else ['',0])

class OpLoadNIL(ABC0):
    def disasm(self, code, consts):     # LOADNIL  A B   R(A) := ... := R(B) := nil
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c==0,  c
        out = ' = '.join([ 'r'+str(i)  for i in range(a,b+1) ])
        return Code('%s = nil' % out, simple)

class OpGetGlobal(ABx):
    def disasm(self, code, consts):     # GETGLOBAL  A Bx   R(A) := Gbl[Kst(Bx)]
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        bx_ = consts[bx]
        assert type(bx_) == str,  bx
        return Code('r%i = <%s>' % (a, bx_), simple)

class OpSetGlobal(ABx):
    def disasm(self, code, consts):     # SETGLOBAL  A Bx   Gbl[Kst(Bx)] := R(A)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        bx_ = consts[bx]
        assert type(bx_) == str,  bx
        return Code('<%s> = r%i' % (bx_, a), simple)

class OpGetUPVal(ABC0):
    def disasm(self, code, consts):     # GETUPVAL  A B   R(A) := UpValue[B]
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c==0,  c
        return Code('r%i = UP[%i]' % (a, b), simple)

class OpSetUPVal(ABC0):
    def disasm(self, code, consts):     # SETUPVAL  A B   UpValue[B] := R(A)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c==0,  c
        return Code('UP[%i] = r%i' % (b, a), simple)

class OpGetTable(ABC):
    def disasm(self, code, consts):     # GETTABLE  A B C   R(A) := R(B)[RK(C)]
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        c_ = 'r'+str(c)  if c<256 else  consts[c-256] #.__repr__()
        c_ = '[%s]'%c_  if type(c_) != str or ' ' in c_ else  '.'+c_
        return Code('r%i = r%i%s' % (a, b, c_), simple)

class OpSetTable(ABC):
    def disasm(self, code, consts):     # SETTABLE  A B C   R(A)[RK(B)] := RK(C)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        b_ = 'r'+str(b)  if b<256 else  consts[b-256]
        if type(b_) == str  and  not b_.isprintable():
            b_ = b_.__repr__()
        b_ = '[%s]'%b_  if type(b_) != str or ' ' in b_ else  '.'+b_
        c_ = 'r'+str(c)  if c<256 else  consts[c-256].__repr__()
        return Code('r%i%s = %s' % (a, b_, c_), simple)

class OpAdd(ABC):
    opname = '+'
    def disasm(self, code, consts):     # ADD  A B C   R(A) := RK(B) + RK(C)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        b_ = 'r'+str(b)  if b<256 else  consts[b-256].__repr__()
        c_ = 'r'+str(c)  if c<256 else  consts[c-256].__repr__()
        return Code('r%i = %s %s %s' % (a, b_, self.opname, c_), simple)

class OpSub(OpAdd):
    opname = '-'
class OpMul(OpAdd):
    opname = '*'
class OpDiv(OpAdd):
    opname = '/'
class OpMod(OpAdd):
    opname = '%'
class OpPow(OpAdd):
    opname = '^'

class OpUnM(ABC0):
    opname = '-'
    def disasm(self, code, consts):     # UNM  A B   R(A) := -R(B)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c == 0,  c
        return Code('r%i = %sr%i' % (a, self.opname, b), simple)

class OpNot(OpUnM):
    opname = 'not '
class OpLen(OpUnM):
    opname = '#'

class OpConcat(ABC):
    def disasm(self, code, consts):     # CONCAT  A B C   R(A) := R(B).. ... ..R(C)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        out = ' .. '.join([ 'r'+str(i)  for i in range(b,c+1) ])
        return Code('r%i = %s' % (a, out), simple)

class OpJmp(A0sBx):
    def disasm(self, code, consts):     # JMP  sBx   PC += sBx
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert a == 0,  a
        return Code('PC += %i' % sbx, simple, ['jmp',sbx])

class OpCall(ABC):
    def disasm(self, code, consts):     # CALL  A B C   R(A), ... ,R(A+C-2) := R(A)(R(A+1), ... ,R(A+B-1))
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        out1 = ', '.join([ 'r'+str(i)  for i in range(a, a+c-1) ])
        if c == 0:  out1 = 'r%i...' % a
        if c == 1:  out1 = '_'
        out2 = ', '.join([ 'r'+str(i)  for i in range(a+1, a+b) ])
        if b == 0:  out2 = 'r%i...' % (a+1)
        return Code('%s = r%i(%s)' % (out1, a, out2), simple)

class OpReturn(ABC0):
    def disasm(self, code, consts):     # RETURN  A B   return R(A), ... ,R(A+B-2)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c == 0,  c
        out = ', '.join([ 'r'+str(i)  for i in range(a, a+b-1) ])
        if b == 0:  out = 'r%i...' % a
        return Code('return %s' % out, simple)

class OpTailCall(ABC0):
    def disasm(self, code, consts):     # TAILCALL  A B  return R(A)(R(A+1), ... ,R(A+B-1))
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c == 0,  c
        out = ', '.join([ 'r'+str(i)  for i in range(a+1, a+b) ])
        if b == 0: out = 'r%i...' % (a+1)       # есть в config.lu
        return Code('return r%i(%s)' % (a, out), simple)

class OpVARarg(ABC0):
    def disasm(self, code, consts):     # VARARG  A B   R(A), R(A+1), ..., R(A+B-1) = vararg
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c == 0,  c
        out = ', '.join([ 'r'+str(i)  for i in range(a, a+b) ])
        if b == 0: out = 'r%i...' % a       # есть в config.lu
        return Code('%s = ...' % out, simple)

class OpSelf(ABC):
    def disasm(self, code, consts):     # SELF  A B C   R(A+1) := R(B); R(A) := R(B)[RK(C)]
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        out1 = 'r%i, r%i' % (a, a+1)
        c_ = 'r'+str(c)  if c<256 else  consts[c-256] #.__repr__()
        assert ' ' not in c_,  c_
        out2 = 'r%i.%s, r%i' % (b, c_, b)
        return Code('%s = %s' % (out1, out2), simple)

class OpEQ(ABC):         # за ним могут следовать 1-2 jmp  (реализация then ... else ...)
    opname = ('==', '!=')
    def disasm(self, code, consts):     # EQ  A B C    if ((RK(B) == RK(C)) ~= A) then PC++
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert a in {0,1},  a
        b_ = 'r'+str(b)  if b<256 else  consts[b-256].__repr__()
        c_ = 'r'+str(c)  if c<256 else  consts[c-256].__repr__()
        return Code('IF %s %s %s:  PC++' % (b_, self.opname[a], c_), simple, ['if',1])

class OpLT(OpEQ):
    opname = ('< ', '>=')
class OpLE(OpEQ):
    opname = ('<=', '> ')

class OpTest(AB0C):
    opname = ('', ' not')
    def disasm(self, code, consts):     # TEST  A C   if not (R(A) <=> C) then PC++
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert b == 0,  b
        assert c in {0,1},  c
        return Code('IF%s r%i:  PC++' % (self.opname[c], a), simple, ['if',1])

class OpTestSet(ABC):
    opname = ('', ' not')
    def disasm(self, code, consts):     # TESTSET  A B C   if not (R(B) <=> C) then PC++  else  R(A) := R(B)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c in {0,1},  c
        return Code('IF%s r%i:  PC++  else  r%i = r%i' % (self.opname[c], b, a, b), simple, ['if',1])

class OpForPrep(AsBx):        # внутри могут быть if/jmp на следущий оператор после ForLoop -- реализация break
    def disasm(self, code, consts):     # FORPREP  A sBx   R(A) -= R(A+2); PC += sBx
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        return Code('FORstart r%i -= r%i,  PC += %i' % (a, a+2, sbx), simple, ['FORStart',sbx])

class OpForLoop(AsBx):
    def disasm(self, code, consts):     # FORLOOP  A sBx   R(A) += R(A+2) if R(A) <?= R(A+1) then { PC += sBx; R(A+3) = R(A) }
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        return Code('FORend r%i += r%i,  IF r%i <?= r%i: { PC += %i, r%i = r%i }' % (a,a+2, a,a+1, sbx, a+3,a), simple, ['FORend',sbx])

class OpTForLoop(AB0C):        # Цикл работает с генератором.  Перед и после цикла - jmp.  Отрицательный jmp есть ещё при while, repeat-until
    def disasm(self, code, consts):
        # TFORLOOP  A C   R(A+3), ... ,R(A+2+C) := R(A)(R(A+1), R(A+2)); if R(A+3) ~= nil then { R(A+2) = R(A+3); } else { PC++; }
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert b == 0,  b
        assert c >= 1,  c
        out = ', '.join([ 'r'+str(i)  for i in range(a+3, a+3+c) ])
        return Code('TFORloop %s = r%i(r%i, r%i),  IF r%i != nil:  r%i = r%i  else  PC++' % (out, a,a+1,a+2, a+3, a+2, a+3), simple, ['TFor',1])

class OpNewTable(ABC):
    def disasm(self, code, consts):     # NEWTABLE  A B C   R(A) := {}  (size = B,C)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        def fpbyte(a):      # “floating point byte”
            if a >> 3 == 0:  return a
            return (8 + (a & 0x7))  <<  ((a >> 3) - 1)
        out = ''  if b==c==0  else  '  (%i, %i)' % (fpbyte(b), fpbyte(c))
        return Code('r%i = {}%s' % (a, out), simple)

class OpSetList(ABC):
    def disasm(self, code, consts):     # SETLIST  A B C   R(A)[(C-1)*FPF+i] := R(A+i),  1 <= i <= B
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert c > 0,  [c, 'If C is 0, the next instruction is cast as an integer, and used as the C value']
        i = 50 * (c - 1)
        end = ('.', '.')  if b == 0 else  (i+b, a+b)
        return Code('r%i[%i..%s] = r%i..%s' % (a, i+1,end[0], a+1,end[1]), simple)

class OpClosure(ABx):
    def disasm(self, code, consts):     # CLOSURE  A Bx   R(A) := closure(KPROTO[Bx], R(A), ... ,R(A+n))
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        return Code('r%i = closure(KPROTO[%i], r%i, ...)' % (a, bx, a), simple)

class OpClose(AB0C0):
    def disasm(self, code, consts):     # CLOSE  A   close all variables in the stack up to (>=) R(A)
        a,b,c,bx,sbx,simple = self.unpack(code, consts)
        assert (b,c) == (0,0),  [b,c]
        return Code('CLOSE r%i+' % a, simple)



opcodes = (
    OpMove('Move'), OpLoadK('LoadK'), OpLoadBool('LoadBool'), OpLoadNIL('LoadNIL'), OpGetUPVal('GetUPVal'), OpGetGlobal('GetGlobal'),
    OpGetTable('GetTable'), OpSetGlobal('SetGlobal'), OpSetUPVal('SetUPVal'), OpSetTable('SetTable'), OpNewTable('NewTable'), OpSelf('Self'),
    OpAdd('Add'), OpSub('Sub'), OpMul('Mul'), OpDiv('Div'), OpMod('Mod'), OpPow('Pow'), OpUnM('UnM'), OpNot('NOT'), OpLen('Len'), OpConcat('Concat'),
    OpJmp('jmp'), OpEQ('EQ'), OpLT('LT'), OpLE('LE'), OpTest('Test'), OpTestSet('TestSet'), OpCall('Call'), OpTailCall('TailCall'), OpReturn('Return'),
    OpForLoop('ForLoop'), OpForPrep('ForPrep'), OpTForLoop('TForLoop'), OpSetList('SetList'), OpClose('Close'), OpClosure('Closure'), OpVARarg('VARarg'),
)


opcodes_rev = {}
for i,op in enumerate(opcodes):  opcodes_rev[ op.name ] = (i, op)

import re
def asm_to_code(s, debug=False):
    c = re.findall(r'(\w+) +([\d #-]+)$', s.strip())[0]
    code,args = c[0], re.split(r' +', c[1])
    args = [ int(x)  if x[0]!='#' else  int(x[1:])+256  for x in args ]
    i,op = opcodes_rev[code]
    out = op.asm(i, args)
    if debug:  print('debug:', code, args, '%x'%out)
    return out

if __name__ == '__main__':
    assert asm_to_code(' GetTable  0   0 #3   ', debug=True) == 0x40c006
    assert asm_to_code('   jmp -6  ', debug=True) == 0x7ffe4016
    print('Ok.')
