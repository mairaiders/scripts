from random import randint as rand 
import base64

def print_random(n):
	return base64.b64encode(os.urandom(int(n)))

def print_line(line):
	return line
	
def random_attach(filename):
	with open(filename) as f:
		linelen = len(f.readline())
		
	with open(filename) as f:
		lines = int((f.seek(0, 2))/linelen)
		randomline = rand(0, lines - 1)
		f.seek(0)
		for i, j in enumerate(f):
			if i == randomline:
				return j.strip()