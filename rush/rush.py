#!/usr/bin/env python
import vk, time, json, pickle, sys, signal, random, logging, shlex, os, threading
import argparse, urllib.request as urlreq
import account

def color(msg, col):
	return colored(msg, col, attrs=['bold'])
try:
	from termcolor import colored
except ImportError:
	print('Python module "termcolor" not found, colored mode is disabled')
	color = lambda x, y: x

# Importing user functions
import functions

FORMATTER = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', '%Y/%m/%d %H:%M:%S')
CONFIG_FILE = 'rush.conf'
PEER_IDS_FILE_SECTION_DELIMITER = '--------------------------\n'
AVAILABLE_COMMANDS = 'status, exit, help, wait, invite, accounts, send, spysend, freeze, unfreeze'
HELP_FUNCITONS = { \
	'status': 'Show status of bots',
	'exit': 'Exit script',
	'help': 'help [COMMAND] ([COMMAND] - optional)\nShow available commands or brief information about COMMAND',
	'wait': 'wait [NAMES]... ([NAMES]... - optional)\nWait for new invite for each bots or only for specified',
	'invite': 'invite [CHAT_ID]\nEach inviter attempts to invite main into CHAT_ID',
	'accounts': 'Show available accounts',
	'send': 'send [CHAT_ID] [NAME] [MSG_TYPE] [MSG]\nSend [MSG] with type [MSG_TYPE] to [CHAT_ID] from account [NAME]',
	'spysend': 'spysend [CHAT_ID] [NAME] [MSG_TYPE] [MSG]\nWorks similar to "send", but adds two more actions: comes into the conversation, sends a message, exists the conversation', 
	'freeze': 'freeze [NAMES]..., ([NAMES]... - optional)\nStop sending messages by all bots',
	'unfreeze': 'unfreeze [NAMES]..., ([NAMES]... - optional)\nStart sending messages by all bots',
	}
	
class Config:
	entries = { \
		'Accounts': ['name', 'user_id', 'role', 'login', 'password'],
		'Bots': ['name', 'bot_id', 'msg_type', 'function', 'arg', 'access_key'],
		'Options': ['name', 'sign', 'value'],
		}

	def __init__(self, filename):
		self.sections = {'Bots': [], 'Accounts': [], 'Options': []}
		
		with open(filename) as f:
			current_section = None
			for i in f:
				i = i.strip()
				if i.startswith('#') or not i:
					continue
					
				if i.startswith('[') and i.endswith(']'):
					current_section = i[1:-1]
				elif current_section:
					i = shlex.split(i)
					self.sections[current_section].append(dict(zip(self.entries[current_section], i)))
				
	def get(self, section, name=None):
		if not name:
			return self.sections.get(section)
		
		for i in self.sections.get(section):
			if i['name'] == name:
				return i['value'] if section == 'Options' else i

class Bot(threading.Thread):		
	def __init__(self, name, bot_id, msg_type, func, arg, key, *, \
		peer_id=None, logfile=None, delay=1, api_version='5.103',  \
		long_poll_wait=25, to_save_peer_ids=None):
		super().__init__(daemon=True)
		self.handler = logging.FileHandler(logfile, mode='a') if logfile else logging.StreamHandler()
		self.handler.setFormatter(FORMATTER)
		self.log = logging.getLogger(name)		
		self.log.setLevel(logging.INFO)
		self.log.addHandler(self.handler)
	
		self.name = name	
		self.bot_id = int(bot_id)
		self.api = vk.API(vk.Session(access_token=key), v=api_version)
		self.peer_id = peer_id
	
		self.func = func
		self.arg = arg
		self.msg_type = msg_type
	
		self.sent = 0
		self.delay = float(delay)
		self.long_poll_wait = long_poll_wait
		self.to_save_peer_ids = to_save_peer_ids
		self.force_command = None
		
		# Handle by logger
		self._unfreeze = threading.Event()
		self._error = 'no errors'
		self._state = 'inactive'
		
	def act(self):
		if self.force_command:		
			self.error = 'no errors'
			self.force_command()
			return
			
		self._unfreeze.wait()
				
		msg = functions.__dict__[self.func](self.arg)
		req = self.api.messages.send
		rand = random.getrandbits(64)
		try:
			if self.msg_type == 'text':
				req(peer_id=self.peer_id, random_id=rand, message=msg)			
			elif self.msg_type == 'attachment':
				req(peer_id=self.peer_id, random_id=rand, attachment=msg)		
		except vk.exceptions.VkAPIError as error:
			self.error = error
			return
		self.sent += 1
		self.error = 'no errors'
		self.log.info('{} prints: {}'.format(self.name, msg))

	def sending(self):
		self.state = 'sending messages'
		while True:
			self.act()
			time.sleep(self.delay)
				
	def wait_for_invite(self, lps=None):
		if not lps:
			lps = self.api.groups.getLongPollServer(group_id=self.bot_id)
		
		self.state = 'wait for invite'
		request = "{}?act=a_check&key={}&ts={}&wait={}".format(lps['server'], lps['key'], lps['ts'], self.long_poll_wait)
		
		resp = json.loads(urlreq.urlopen(request).read())
		lps['ts'], updates = resp['ts'], resp['updates']

		for i in updates:
			if i['type'] == 'message_new' and 'action' in i['object']['message'] and \
			i['object']['message']['action']['type'] == 'chat_invite_user' and \
			i['object']['message']['action']['member_id'] == -self.bot_id:
				self.peer_id = i['object']['message']['peer_id']
				if self.to_save_peer_ids:
					with open(self.to_save_peer_ids, 'a') as f:
						f.write('{} {}\n'.format(self.name, self.peer_id))
				self.log.info('The wait for {} completed, peer_id set to {}'.format(self.name, self.peer_id))				
				return
		if self.peer_id == None:
			self.wait_for_invite(lps)
	
	def run(self):
		try:
			self.log.info('Thread for {} running'.format(self.name))
			if self.peer_id:
				self.sending()
			self.wait_for_invite()
			self.sending()
		except Exception as error:
			self.error = error	
	def status(self):
		return '{}: {}, messages sent: {}, error: {} {}'.format(self.name, color(self.state, 'white'), self.sent, color(self.error, 'red'), '(frozen)' if not self._unfreeze.is_set() else '')
	
	@property
	def state(self):
		return self._state
	
	@state.setter
	def state(self, value):
		if self._state == value:
			return
		self._state = value
		self.log.info('State of {} switched to "{}"'.format(self.name, self._state))
		
	@property
	def error(self):
		return self._error
		
	@error.setter
	def error(self, value):
		self._error = value
		if self._error != 'no errors':
			self.log.error('Error occured in {}: {}'.format(self.name, self._error))
	@property
	def freeze(self):
		return not self._unfreeze.is_set()
	
	@freeze.setter
	def freeze(self, value):
		if not value: 
			self._unfreeze.set()
			self.log.info('{} unfroze'.format(self.name))
		else: 
			self._unfreeze.clear()
			self.log.info('{} froze'.format(self.name))
		
def main():
	def peer_ids_load(peer_ids, peer_ids_file):
		with open(peer_ids_file, 'r+') as f:
			sections = [0]
			line = f.readline()			
			while line:
				if line == PEER_IDS_FILE_SECTION_DELIMITER:					
					sections.append(f.tell())
				line = f.readline()
					
			count = 1
			while peer_ids == {} and count <= len(sections):
				f.seek(sections[-count])
				i = f.readline()
				while i and i != PEER_IDS_FILE_SECTION_DELIMITER:
					i = i.split()
					peer_ids[i[0]] = int(i[1])
					i = f.readline()
				count += 1
	parser = argparse.ArgumentParser(epilog='Written by mairaiders <raidconversations@gmail.com>')
	parser.add_argument('-c', '--config', default=CONFIG_FILE, dest='config', help='set config file')
	parser.add_argument('-V', '--version', action='version', version='rush.py 0.5')
	args = parser.parse_args()
	
	conf = Config(CONFIG_FILE)	
	bots = []
	peer_ids = {}
	peer_ids_file = conf.get('Options', 'peer_ids_file')
	
	with open(peer_ids_file, 'a') as f:
		f.write(PEER_IDS_FILE_SECTION_DELIMITER)

	if os.path.isfile(peer_ids_file):
		ans = input('{} exists, read peer ids from it? [Y/n] '.format(peer_ids_file))
		if ans in 'Yy' and len(ans) == 1:
			peer_ids_load(peer_ids, peer_ids_file)
			for i, j in peer_ids.items():	
				print('Found peer_id {} for {}'.format(j, i))
			ans = input('Apply? [Y/n] ')
			if ans not in 'Yy' and len(ans) == 1:
				peer_ids = {}
	for i in conf.get('Bots'):
		bots.append(Bot(*i.values(), logfile=conf.get('Options', 'log_file'), \
			peer_id=peer_ids.get(i['name']), \
			delay=conf.get('Options', 'delay'), \
			api_version=conf.get('Options', 'api_version'), \
			long_poll_wait=conf.get('Options', 'long_poll_wait'), \
			to_save_peer_ids=conf.get('Options', 'peer_ids_file')))
		bots[-1].start()
	
	accounts = {'Inviter': [], 'Main': []}
	
	for i in conf.get('Accounts'):
		try:
			accounts[i['role']].append({'name': i['name'], \
				'account': account.Account(i['login'], i['password'], i['user_id'])})
		except account.invalid_password:
			print(i['name'] + ':', 'Authorization failed')			
	cmd = None
	while True:
		cmd = input(color('help', 'white') + \
			color('/', 'green') + \
			color('command', 'white') + \
			color('>', 'green') +  ' ')		
		cmd = shlex.split(cmd)
		if len(cmd) == 0: continue
		cmd, args = cmd[0], cmd[1:]
		try:	
			if cmd == 'status':
				for i in bots:
		 			print(i.status())		
			elif cmd =='help':
				if len(args) == 0:
					print(AVAILABLE_COMMANDS)	
				else:
					print(HELP_FUNCITONS[args[0]])
			elif cmd == 'wait':
				if len(args) == 0:
					for i in bots:
						i.force_command = i.wait_for_invite
				else:
					for i in bots:
						if i.name in args:
							i.force_command = i.wait_for_invite
			elif cmd == 'exit':
				sys.exit(0)
			elif cmd == 'invite':
				for i in accounts['Inviter']:
					if i.spy_invite(accounts['Main'][0]['account'].user_id, args[0]):
						break
			elif cmd == 'accounts':
				for role, accs in accounts.items():
					for i in accs:
						print('{} (https://vk.com/id{}): {}'.format(i['name'], i['account'].user_id, role))
			elif cmd == 'spysend' or cmd == 'send':
				for role, accs in accounts.items():
					for i in accs:
						if i['name'] == args[1]:
							method = i['account'].spy_send if cmd == 'spysend' else i['account'].send
							method(args[0], args[2], args[3])
			elif cmd == 'freeze' or cmd == 'unfreeze':
				val = cmd == 'freeze'
				if len(args) == 0:					
					for i in bots:
						i.freeze = val
				else:
					for i in bots:
						if i.name in args:
							i.freeze = val
			else:
				print(color('{}: command not found'.format(cmd), 'red'))
		except IndexError:
			print(color('Invalid arguments', 'red'), file=sys.stderr)
		except Exception as error:
			print(color('Error: ' + str(error), 'red'), file=sys.stderr)
		
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print(color('Interrupted', 'red'), file=sys.stderr)
	except Exception as error:
		print(color('Error: ' + str(error), 'red'), file=sys.stderr)