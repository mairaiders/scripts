#!/usr/bin/env python
import vk, time, json, pickle, os.path, sys, signal
import urllib.request as urlreq
from threading import Thread
from termcolor import colored as C
from random import randint as rand

ACCESS_KEYS_FILE='access_keys.txt'
ACTIONS_FILE='actions.txt'
PEER_IDS_FILE = 'peer_ids.dat'
MAX_CYCLES = 100 # 100 or 500
API_VERSION='5.103'
DELAY=1
LONGPOLLWAIT=10
COMMENT = "#"

import base64
def print_random(n):
	return base64.b64encode(os.urandom(int(n)))

def print_line(line):
	return line
	
def random_pics(filename):
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
	return 0

def parse_access_keys(file):    
	access_keys = []
	with open(file, "r") as f:
		for i in f:
			line = i.strip()
			if line.startswith(COMMENT) or not line:
				continue
			splitted = line.split()
			access_keys.append({'name': splitted[0], 'group_id': int(splitted[1]), 'access_key': splitted[2]})
	return access_keys

def get_vk_bots_from_access_keys(access_keys):
	bots = []
	for i in access_keys:		
	    bots.append({'name': i['name'], 'group_id': i['group_id'], 'api': vk.API(vk.Session(access_token=i['access_key']), v=API_VERSION)})
	return bots
	

def parse_actions(file):
	actions = []
	with open(file, "r") as f:
		for i in f:
			line = i.strip()
			if line.startswith(COMMENT) or not line:
				continue
			splitted = line.split("\t")
			actions.append({ \
				'name': splitted[0], \
				'msg_type': splitted[1], \
				'function': globals()[splitted[2]], \
				'args': splitted[3:] if len(splitted) > 3 else [], \
				})
	return actions

# Global variable needed for stop threads
done = False
def wait_for_invite(bot):	
	print('  {} wait for invite'.format(bot['name']))
	lps = bot['api'].groups.getLongPollServer(group_id=bot['group_id'])
	while not done:	
		request = "{}?act=a_check&key={}&ts={}&wait={}".format(lps['server'], lps['key'], lps['ts'], LONGPOLLWAIT)
		
		resp = json.loads(urlreq.urlopen(request).read())
		if done: return			
		
		lps['ts'], updates = resp['ts'], resp['updates']

		for i in updates:
			if i['type'] == 'message_new' and \
			'action' in i['object']['message'] and \
			i['object']['message']['action']['type'] == 'chat_invite_user' and \
			i['object']['message']['action']['member_id'] == -bot['group_id']:
				bot['peer_id'] = i['object']['message']['peer_id']
				return 
				
def wait_for_invites(bots):
	def status():
		for i in bots:
			if not 'peer_id' in i:
				print(C('  {} did not joined the convesation'.format(i['name']), 'red', attrs=['bold']))
			else:
				print(C('  {} joined the convesation'.format(i['name']), 'green', attrs=['bold']))

	threads = []
	global done 
	done = False
	
	print(C('Waiting for invites...', 'yellow', attrs=['bold']))	
	for i in bots:
		thread = Thread(target=wait_for_invite, args=(i,), name=i['name'])
		thread.start()
		threads.append(thread)
	
	# So that the threads have time to print
	time.sleep(0.1)
	
	cmd = ''
	while cmd != 'done':
		cmd = input(C('done', 'cyan', attrs=['bold']) + \
			C('/', 'white', attrs=['bold']) + \
			C('status', 'cyan', attrs=['bold']) + \
			C('> ', 'white', attrs=['bold']))
		if cmd == 'status':
			status()			
			
	done = True
	
	print(C('Closing waiting threads...', 'yellow', attrs=['bold']))
	for i in threads:
		i.join()
		print('  {} waiting cancelled'.format(i.getName()))
	status()
	
	input(	C('All threads has been closed, press enter to continue', 'cyan', attrs=['bold']) + \
			C('> ', 'white', attrs=['bold']))
					
	print(C('Bots are ready to spam', 'yellow', attrs=['bold']))
	
	return [i for i in bots if 'peer_id' in i]

		
def intersection(acts, keys, item):
	acts_names = set((i[item] for i in acts))
	keys_names = set((i[item] for i in keys))
	inter = acts_names & keys_names
	
	for i in acts:
		if not i[item] in inter:
			acts.remove(i)
			print (C('{} has no access key, it will be removed'.format(i[item]), 'red', attrs=['bold']))
			
	for i in keys:
		if not i[item] in inter:
			keys.remove(i)
			print (C('{} has no action, it will be removed'.format(i[item]), 'red', attrs=['bold']))

def save_peer_ids(bots, filename):
	peer_ids = [{'name': i['name'], 'peer_id': i['peer_id']} for i in bots]
	with open(filename, 'wb') as f:
		pickle.dump(peer_ids, f)
		
def load_peer_ids(filename):
	with open(filename, 'rb') as f:
		return pickle.load(f)

def connect_peer_ids_with_bots(bots, peer_ids, option='remove'):
	for i in bots:
		peer_id = next((j['peer_id'] for j in peer_ids if j['name'] == i['name']), None)
		if not peer_id is None:
			i['peer_id'] = peer_id
			
	if option == 'remove':
		return [i for i in bots if 'peer_id' in i]
	elif option == 'partial':
		return bots
	
def spam(bots, acts):
	# len(bots) == len(acts) is true
	rnd = 0
	cycles = 0
	msgs_sent = 0
	done = False
	while not done:
		for i, j in zip(bots, acts):
			msg = j['function'](*j['args'])
			req = i['api'].messages.send
			if j['msg_type'] == 'text':
				req(peer_id=i['peer_id'], random_id=rnd+1, message=msg)			
			elif j['msg_type'] == 'attachment':
				req(peer_id=i['peer_id'], random_id=rnd+2, attachment=msg)		
			msgs_sent += 1
			print(C('{} prints: '.format(i['name']), 'yellow', attrs=['bold']) + '{}'.format(msg))
			rnd ^= 1
		print(C('{} cycles left, {} messages sent'.format(MAX_CYCLES-cycles-1, msgs_sent), 'yellow', attrs=['bold']))
		time.sleep(DELAY)
		cycles += 1
		if cycles == MAX_CYCLES:
			ans = input('Again? (Y/n) ')
			if ans in 'Yy':
				cycles = 0
			else:
				done = True
	
def main():
	print(C('Loading access keys...', 'yellow', attrs=['bold']))
	keys = parse_access_keys(ACCESS_KEYS_FILE)
	
	print(C('Loading actions...', 'yellow', attrs=['bold']))
	acts = parse_actions(ACTIONS_FILE)
	
	# If one have only either action or access key	
	intersection(acts, keys, 'name')
	
	bots = get_vk_bots_from_access_keys(keys)
	wait = True
	
	if os.path.isfile(PEER_IDS_FILE):
		ans = input('{} exists, load peer_ids from file? (Y/p/n) '.format(PEER_IDS_FILE))	
		if ans in 'Yy':
			bots = connect_peer_ids_with_bots(bots, load_peer_ids(PEER_IDS_FILE))	
			wait = False
		elif ans in 'Pp':
			bots = connect_peer_ids_with_bots(bots, load_peer_ids(PEER_IDS_FILE), 'partial')
						
	if wait:
		bots = wait_for_invites(bots)		
		save_peer_ids(bots, PEER_IDS_FILE)
			
	intersection(bots, acts, 'name')	
	spam(bots, acts)	
	
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print(C('Interrupted', 'red', attrs=['bold']))
		sys.exit(0)