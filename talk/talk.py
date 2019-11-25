#!/usr/bin/env python
import vk, json, os.path, sys, signal
import urllib.request as urlreq
from termcolor import colored as C

API_VERSION='5.103'
LONGPOLLWAIT=10
PEER_ID_FILE='peer_id.txt'
COMMENT='#'

# Global variable needed for stop threads
def wait_for_invite(bot):	
	while True:
		print(C('Waiting for invite...'))
		try:
			lps = bot['api'].groups.getLongPollServer(group_id=bot['group_id'])
			request = "{}?act=a_check&key={}&ts={}&wait={}".format(lps['server'], lps['key'], lps['ts'], LONGPOLLWAIT)		
			resp = json.loads(urlreq.urlopen(request).read())
		except Exception as e:
			print(C(e, 'red', attrs=['bold']))
			ans = input('Retry? (Y/n) ')
			if ans in 'Yy':
				continue
			else: 
				sys.exit(0)
		
		lps['ts'], updates = resp['ts'], resp['updates']

		for i in updates:
			if i['type'] == 'message_new' and \
			'action' in i['object']['message'] and \
			i['object']['message']['action']['type'] == 'chat_invite_user' and \
			i['object']['message']['action']['member_id'] == -bot['group_id']:
				bot['peer_id'] = i['object']['message']['peer_id']
				return 

def read_peer_id(filename):
	with open(filename) as f:
		return int(f.readline().strip())
		
def save_peer_id(bot, filename):
	with open(filename, "w") as f:
		print(bot['peer_id'], file=f)

def talk(bot):
	rnd = 0
	while True:
		try:
			msg = input(C('send', 'cyan') + \
				C('> ', 'white'))
		except EOFError as e:
			print()
			sys.exit(0)
			
		if len(msg.strip()) == 0:
			print(C('Invalid message: "{}"'.format(msg), 'red', attrs=['bold']))
			continue
		try:
			bot['api'].messages.send(peer_id=bot['peer_id'], random_id=rnd+1, message=msg)
		except vk.exceptions.VkAPIError as e:
			print(e.message, file=sys.stderr)
			continue
		print(	C('You sent: ', 'green') + \
			'"{}"'.format(msg))
		rnd ^= 1
			
def main():
	if len(sys.argv) < 3:
		print('Usage: ./talk.py [GROUP ID] [ACCESS KEY]', file=sys.stderr)
		sys.exit(1)
	
	print(C('Access key: ', 'green') + '{}'.format(sys.argv[2][:4] + '....' + sys.argv[2][-4:]))
	print(C('Group id: ', 'green') + '{}'.format(sys.argv[1]))
	bot = {	'api': vk.API(vk.Session(access_token=sys.argv[2]), v=API_VERSION), \
		'group_id': int(sys.argv[1])}
	
	wait = True
	if os.path.isfile(PEER_ID_FILE):
		ans = input('{} exists, load peer_id from file? (Y/n) '.format(PEER_ID_FILE))	
		if ans in 'Yy':			
			bot['peer_id'] = read_peer_id(PEER_ID_FILE)
			wait = False
	if wait:									
		wait_for_invite(bot)		
		save_peer_id(bot, PEER_ID_FILE)
			
	talk(bot)
	
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print(C('Interrupted', 'red', attrs=['bold']))
		sys.exit(0)