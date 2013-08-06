#!/usr/bin/python
from math import *
import readline
import locale
import units

class ParseError(Exception):
	def __init__(self,reason):
		self.reason=reason

	def __str__(self):
		return "Parse Error: %s" % self.reason

class NoSuchSymbol(Exception):
	def __init__(self,symbol):
		self.symbol = symbol

	def __str__(self):
		return "Undefined symbol: %s" % self.symbol

class AST:
	def getValue(self,symtab):
		return self.eval(symtab).getValue(symtab)

class Value:
	def __init__(self,value,unit=None):
		self.value=value
		self.unit=unit

	def eval(self,symtab):
		return self

	def getValue(self,symtab):
		return self.value

	def getUnit(self,symtab):
		return self.unit

	def __str__(self):
		if self.value-int(self.value)==0:
			v= str(int(self.value))
		elif type(self.value) in [ type(0.0), type(0)]:
			v= locale.format("%f",self.value,True)
		else:
			v=str(self.value)
		if self.unit:
			return v+" "+self.unit
		else:
			return v

	def __repr__(self):
		if self.unit:
			return "Value(%s,%s)" % (str(self.value),self.unit)
		else:
			return "Value(%s)" % str(self.value)

class Variable(AST):
	def __init__(self,name):
		self.name=name

	def __str__(self):
		return self.name

	def __repr__(self):
		return "Variable(%s)" % self.name

	def eval(self,symtab):
		if symtab.has_key(self.name):
			return symtab[self.name].eval(symtab)
		else:
			raise NoSuchSymbol(self.name)

	def getUnit(self,symtab):
		if symtab.has_key(self.name):
			return symtab[self.name].getUnit(symtab)
		else:
			raise NoSuchSymbol(self.name)

class BinOp(AST):
	def __init__(self,lhs,rhs,op="?"):
		self.lhs=lhs
		self.rhs=rhs
		self.op=op

	def __str__(self):
		return str(self.lhs)+self.op+str(self.rhs)

	def eval(self,symtab):
		lhs = self.lhs.eval(symtab)
		rhs = self.rhs.eval(symtab)
		a=Value(eval("(lhs.getValue(symtab) "+self.op+" rhs.getValue(symtab))"),self.getUnit(symtab))
		return a


class MulOp(BinOp):
	def __init__(self,lhs,rhs):
		BinOp.__init__(self,lhs,rhs,"*")

	def getUnit(self,symtab):
		lhs=self.lhs.getUnit(symtab)
		rhs=self.rhs.getUnit(symtab)
		if lhs==None:
			lhs=""
		if rhs==None:
			rhs=""
		return lhs+" "+rhs

class DivOp(BinOp):
	def __init__(self,lhs,rhs):
		BinOp.__init__(self,lhs,rhs,"/")

	def getUnit(self,symtab):
		lhs=self.lhs.getUnit(symtab)
		rhs=self.rhs.getUnit(symtab)
		if lhs==None or lhs=="":
			if rhs==None or rhs=="":
				return None
			else:
				return "1/("+rhs+")"
		else:
			if rhs==None or rhs=="":
				return lhs
			else:
				return "("+lhs+")/("+rhs+")"
		return "("+lhs+")/("+rhs+")"

# For addition and subtraction
class TermOp(BinOp):
	def getValue(self,symtab):
		# Ok, we have to convert everything to be in the same units.
		lhs = self.lhs.eval(symtab)
		rhs = self.rhs.eval(symtab)

		if rhs.getUnit(symtab)==None:
			# If the rhs has no unit, we pretend it's in the
			# same unit.  People are lazy, and the alternative
			# is to raise an error, which just infuriates users
			pass
		else:
			# Ok, the rhs has a unit, we need to convert it to
			# be the same as the left
			rhs=units.convert(rhs,rhs.getUnit(symtab),lhs.getUnit(symtab))
		a=Value(eval("(lhs.getValue(symtab) "+self.op+" rhs.getValue(symtab))"),lhs.getUnit(symtab))
		return a

	def getUnit(self,symtab):
		return self.lhs.getUnit(symtab)

class AddOp(TermOp):
	def __init__(self,lhs,rhs): TermOp.__init__(self,lhs,rhs,"+")
class SubOp(TermOp):
	def __init__(self,lhs,rhs): TermOp.__init__(self,lhs,rhs,"+")

class DefinedNativeFunction(AST):
	def __init__(self,name,func):
		self.name=name
		self.func=func

	def __str__(self):
		return self.name+"("+",".join(
			[ "a%i" % x 
			for x in range(self.func.func_code.co_argcount)
			]
			)+")"

	def eval(self,symtab):
		pass

	def evalFunction(self,symtab,args):
		return Value(apply(self.func,map(lambda x:x.getValue(symtab),args)))

	def __repr__(self):
		return "NativeFunction(%s,%s)" % (self.name,self.func)

class DefinedFunction(AST):
	def __init__(self,func,argsnames,expansion):
		self.func=func
		self.argnames=argsnames
		self.expansion=expansion

	def __str__(self):
		return self.func+"("+",".join(map(str,self.argnames))+")="+str(self.expansion)

	def eval(self,symtab):
		raise "Evaluating a defined function"

	def evalFunction(self,symtab,args):
		newsymtab=symtab.copy()
		for i in range(len(args)):
			newsymtab[self.argnames[i]]=args[i]
		return self.expansion.eval(newsymtab)

	def getFunctionUnit(self,symtab,args):
		newsymtab=symtab.copy()
		for i in range(len(args)):
			newsymtab[self.argnames[i]]=args[i]
		return self.expansion.getUnit(newsymtab)

	def __repr__(self):
		return "DefinedFunction(%s)" % str(self)

class EvalFunction(AST):
	def __init__(self,func,args):
		self.func=func
		self.args=args

	def __str__(self):
		return self.func+"("+",".join(map(str,self.args))+")"

	def eval(self,symtab):
		return symtab[self.func].evalFunction(
			symtab,
			map(lambda x:x.eval(symtab),
			self.args))

	def getUnit(self,symtab):
		return symtab[self.func].getFunctionUnit(
			symtab,
			map(lambda x:x.eval(symtab),
			self.args))

symtab = {
	"inc" : DefinedFunction("inc",["x"],BinOp(Variable("x"),Value(1),"+")),
	"sin" : DefinedNativeFunction("sin",sin),
	"x" : Value(3),
	}

def skip_white(x):
	while x!="" and x[0] in " \t\n\r":
		x=x[1:]
	return x


def parse_value(x):
	x=skip_white(x)
	if x=="":
		raise ParseError("Unexpected end of expression")
	if x[0] == "(":
		x,a = parse(x[1:])
		if x=="":
			raise ParseError("expected ')'")
		if x[0]!=")":
			raise ParseError("expected ')' got '%s' instead" % `x`)
		return x[1:],a
	if x[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_": 
		tok=""
		while x!="" and x[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_0123456789": 
			tok=tok+x[0]
			x=x[1:]
		# TODO, if a ( follows it's a function call
		x=skip_white(x)
		if x!="" and x[0]=="(":
			args=[]
			x=x[1:]
			while 1:
				x,arg=parse(x)
				args.append(arg)
				x=skip_white(x)
				if x[0]==")":
					return x[1:],EvalFunction(tok,args)
				if x[0]==",":
					x=x[1:]
					continue
				raise ParseError("expected ',' or ')' got %s" % `x`)
		return x,Variable(tok)
	if x!="" and x[0] in "0123456789.":
		tok=""
		while x!="" and x[0] in "0123456789":
			tok=tok+x[0]
			x=x[1:]
		if x=="" or x[0]!=".":
			return x,Value(int(tok))
		x=x[1:]
		tok=tok+"."
		while x!="" and x[0] in "0123456789":
			tok=tok+x[0]
			x=x[1:]
		return x,Value(float(tok))
	raise ParseError("Unexpected %s" % `x`)

def parse_exponent(x):
	x,term = parse_value(x)
	x = skip_white(x)
	while x!="":
		if x[0]=="^":
			x,term2 = parse_value(x[1:])
			term = BinOp(term,term2,"**")
		else:
			break
	return x,term

def parse_factor(x):
	x,term = parse_exponent(x)
	x = skip_white(x)
	while x!="":
		if x[0]=="*":
			x,term2 = parse_exponent(x[1:])
			term = MulOp(term,term2)
		elif x[0]=="/":
			x,term2 = parse_exponent(x[1:])
			term = DivOp(term,term2)
		else:
			break
	return x,term

def parse_term(x):
	x,term = parse_factor(x)
	x=skip_white(x)
	while x!="":
		if x[0]=="+":
			x,term2 = parse_factor(x[1:]) # Skip the +
			term = AddOp(term,term2)
		elif x[0]=="-":
			x,term2 = parse_factor(x[1:]) # Skip the -
			term = SubOp(term,term2)
		else:
			break
	return x,term
			

parse=parse_term

id=0
def evaluate(x):
	global id
	x,exp=parse(x)
	x=skip_white(x)
	if x!="" and x[0]=="=":
		func=exp
		x=x[1:]
		x,exp = parse(x)
		x=skip_white(x)
		if x!="":
			raise ParseError("%s left over" % `x`)
		if func.__class__==Variable:
			symtab[func.name]=exp
			return Variable(func.name)
		elif func.__class__==EvalFunction:
			symtab[func.func]=DefinedFunction(func.func,
							map(lambda x:x.name,func.args),
							exp)
		else:
			raise ParseError("can't assign to '%s'" % func)
		return symtab[func.func]
	else:
		if x!="":
			raise ParseError("Parse Error %s left over" % `x`)
		r=exp.eval(symtab)
		symtab["_"]=r
		symtab["_%i" % id]=r
		return exp

def evaluate_str(x):
	assert(type(x)==type(""))
	try:
		a=evaluate(x)
	except ParseError, e:
		return str(e)
	except NoSuchSymbol, e:
		return str(e)
	if a.__class__==DefinedFunction:
		return str(a)
	else:
		a2=a.eval(symtab)
		v,u=units.simplify(a2.getValue(symtab),a2.getUnit(symtab))
		a2=Value(v,u)
		return "%s = %s" % ( str(a),str(a2))

def expression_str(x):
	try:
		if x.__class__==Variable:
			return str(x)+"="+str(symtab[x.name])
	except e:
		raise
	return str(x)

def init():
	units.load()
	for k,v in units.units.items():
		symtab[k]=Value(1,k)

if __name__=="__main__":
	init()
	while 1:
		id=id+1
		print evaluate_str(raw_input("%i> " % id))

