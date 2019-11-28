#!/usr/bin/env python
import vk, time, json, pickle, os.path, sys, signal, random
import urllib.request as urlreq
import argparse
from threading import Thread
from termcolor import colored as C

# Importing user functions
import functions

ACCESS_KEYS_FILE='access_keys.txt'
ACTIONS_FILE='actions.txt'
PEER_IDS_FILE='peer_ids.dat'
MAX_CYCLES=1000 # 100 or 500
API_VERSION='5.103'
DELAY=0.7
LONGPOLLWAIT=10
COMMENT="#"

peer_ids = {}

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
				'function': functions.__dict__[splitted[2]], \
				'args': splitted[3:] if len(splitted) > 3 else [], \
				})
	return actions

# Global variable needed for stop threads
done = False
def wait_for_invite(bot, spam=False, act=None):	
	def sending_loop():
		while True:
			perform(bot, act)
			time.sleep(DELAY)
	if spam and not act:
		print(C('Act doesn\'t exist for {}'.format(bot['name']), 'red', attr=['bold']))			
		return
		
	if spam and act and 'peer_id' in bot:
		sending_loop()
		
	global peer_ids
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
				peer_ids[bot['name']] = bot['peer_id']			
				save_peer_ids(PEER_IDS_FILE)	
				if spam and act:
					sending_loop()
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
		
def intersection(l1, l2, item):
	l1_names = set((i[item] for i in l1))
	l2_names = set((i[item] for i in l2))
	inter = l1_names & l2_names
	
	l1[:] = [i for i in l1 if i[item] in inter]
	l2[:] = [i for i in l2 if i[item] in inter]

def save_peer_ids(filename):
	global peer_ids
	with open(filename, 'wb') as f:
		pickle.dump(peer_ids, f)
		
def load_peer_ids(filename):
	global peer_ids
	with open(filename, 'rb') as f:
		peer_ids = pickle.load(f)

def connect_peer_ids_with_bots(bots, option='remove'):
	global peer_ids
	for i in bots:
		peer_id = peer_ids.get(i['name'])
		if not peer_id is None:
			i['peer_id'] = peer_id
			
	if option == 'remove':
		bots[:] = [i for i in bots if 'peer_id' in i]
	elif option == 'partial':
		pass
			
def perform(bot, act):
	msg = act['function'](*act['args'])
	req = bot['api'].messages.send
	rand = random.getrandbits(64)
	try:
		if act['msg_type'] == 'text':
			req(peer_id=bot['peer_id'], random_id=rand, message=msg)			
		elif act['msg_type'] == 'attachment':
			req(peer_id=bot['peer_id'], random_id=rand, attachment=msg)		
	except vk.exceptions.VkAPIError as e:
		print(C(e, 'red', attrs=['bold']))
		return
	print(C('{} prints: '.format(bot['name']), 'yellow', attrs=['bold']) + '{}'.format(msg))
	
def spam(bots, acts):
	cycles = 0
	msgs_sent = 0
	while True:
		for j in acts:
			i = next((x for x in bots if x['name'] == j['name']), None)
			perform(i, j)
			msgs_sent += 1
		print(C('{} cycles left, {} messages sent'.format(MAX_CYCLES-cycles-1, msgs_sent), 'yellow', attrs=['bold']))
		time.sleep(DELAY)
		cycles += 1
		if cycles == MAX_CYCLES:
			ans = input('Again? (Y/n) ')
			if ans in 'Yy':
				cycles = 0
			else:
				return
	
def wait_for_invites_and_spam(bots, acts):
	print(C('Waiting for invites...', 'yellow', attrs=['bold']))	
	for i in bots:	
		act = next((x for x in acts if x['name'] == i['name']), None)
		thread = Thread(target=wait_for_invite, args=(i, True, act))
		thread.start()

def main():	
	global PEER_IDS_FILE
	
	parser = argparse.ArgumentParser(epilog='Written by mairaiders <raidconversations@gmail.com>')
	parser.add_argument('-a', '--asynh', action='store_true', help='send messages immediately after invitation')
	parser.add_argument('-V', '--version', action='version', version='rush.py 0.3')
	parser.add_argument('-f', '--file', default=PEER_IDS_FILE, dest='file', help='set file contains peer ids')
	
	args = parser.parse_args()
	
	PEER_IDS_FILE = args.file
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
		load_peer_ids(PEER_IDS_FILE)
		if ans in 'Yy':
			connect_peer_ids_with_bots(bots)	
			wait = False				
		elif ans in 'Pp':
			connect_peer_ids_with_bots(bots, 'partial')
	
	if wait and args.asynh:
		wait_for_invites_and_spam(bots, acts)
	elif wait:
		bots = wait_for_invites(bots)		

	if not args.asynh:
		intersection(bots, acts, 'name')	
		spam(bots, acts)
				
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print(C('Interrupted', 'red', attrs=['bold']))
		
		sys.exit(0)