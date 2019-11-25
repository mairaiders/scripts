from random import randint as rand 
import base64

def print_random(n):
	return base64.b64encode(os.urandom(int(n)))

def print_line(line):
	return line
	
def random_attach(filename):
	def file_len(file):
		for i, j in enumerate(file):
			pass
		file.seek(0)
		return i
	
	with open(filename, "r") as f:
		randomline = rand(0, file_len(f))
		for i, j in enumerate(f):
			if i == randomline:
				return j.strip()