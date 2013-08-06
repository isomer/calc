#!/usr/bin/python
import posix

def convert(value,from_unit,to_unit):
	a=posix.popen("/usr/bin/units -o %%.15g '%f %s' '%s'" % (value,from_unit,to_unit),"r")
	return float(a.readline().strip().split(" ",1)[1].strip())

def simplify(value,units):
	if units==None:
		return value,None # Easy!
	a=posix.popen("/usr/bin/units -o %%.15g '%f %s'" % (value,units),"r")
	(v,u)=a.readline().strip().split(" ",1)[1].strip().split(" ",1)
	v=float(v)
	return v,u
	

def load(db="/usr/share/misc/units.dat"):
	global prefixes,units
	prefixes={}
	units={}
	f=open(db,"r")
	while 1:
		i=f.readline()
		if i=="":
			break
		while 1:
			if "#" in i:
				i=i.split("#")[0]
			i=i.strip()
			if i=="":
				break
			if i[-1]=="\\":
				i=i+" "+f.readline()
				continue
			break
		if i=="":
			continue
		if i[0]=="!":
			continue
		print `i`
		l,r=map(lambda x:x.strip(),i.split(" ",1))
		if l[-1]=="-":
			prefixes[l[:-1]]=r
		else:
			units[l]=r
		
if __name__=="__main__":
	load()
	print convert(1,"feet","meters")
