import requests,lxml.html,re,json

class invalid_password(Exception):
    def __init__(self, value): self.value = value
    def __str__(self): return repr(self.value)
class not_valid_method(Exception):
    def __init__(self, value): self.value = value
    def __str__(self): return repr(self.value)
class response_error(Exception):
    def __init__(self, value): self.value = value
    def __str__(self): return repr(self.value)

class _messages(object):
    def __init__(this,login,password):
        this.login = login
        this.password = password
        this.hashes = {}
        this.auth()

    def auth(this):
        headers = { \
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language':'ru-ru,ru;q=0.8,en-us;q=0.5,en;q=0.3',
            'Accept-Encoding':'gzip, deflate',
            'Connection':'keep-alive',
            'DNT':'1'
            }
        this.session = requests.session()
        data = this.session.get('https://vk.com/', headers=headers)
        page = lxml.html.fromstring(data.content)
        form = page.forms[0]
        form.fields['email'] = this.login
        form.fields['pass'] = this.password
        response = this.session.post(form.action, data=form.form_values())
        if "onLoginDone" not in response.text: raise invalid_password("Неправильный пароль!")
        return

    def method(this,method,v=5.87,**params):
        if method not in this.hashes:
            this._get_hash(method)
        data = {'act': 'a_run_method','al': 1,
                'hash': this.hashes[method],
                'method': method,
                'param_v':v}
        for i in params:
            data["param_"+i] = params[i]
        answer = this.session.post('https://vk.com/dev',data=data)
        answer = json.loads(json.loads(answer.text[4:])['payload'][1][0]) 
        this._check(answer)
        return answer
        #return json.loads(re.findall("<!>(\{.+)",answer.text)[-1])
        
    def _get_hash(this,method):
        html = this.session.get('https://vk.com/dev/'+method)
        hash_0 = re.findall('onclick="Dev.methodRun\(\'(.+?)\', this\);',html.text)
        if len(hash_0)==0:
            raise not_valid_method("Method is not valid")
        this.hashes[method] = hash_0[0]
    
    def _check(self, response):
        if 'error' in response:
            raise response_error(response['error']['error_msg'])
    
class Account(_messages):
    API_VERSION = 5.87
    
    def __init__(this, login, password, user_id):
        super().__init__(login, password)
        this.user_id = user_id
    
            
    def spy_invite(this, user_id, chat_id):    
        this.method('messages.addChatUser', user_id=this.user_id, chat_id=chat_id, v=this.API_VERSION)
        this.method('messages.addChatUser', user_id=user_id, chat_id=chat_id, v=this.API_VERSION)
        this.method('messages.removeChatUser', user_id=this.user_id, chat_id=chat_id, v=this.API_VERSION)
        return True        
    
    def spy_send(this, chat_id, type, msg):
        this.method('messages.addChatUser', user_id=this.user_id, chat_id=chat_id, v=this.API_VERSION)
        this.send(chat_id, type, msg)
        this.method('messages.removeChatUser', user_id=this.user_id, chat_id=chat_id, v=this.API_VERSION)
        
    def send(this, chat_id, type, msg):
        if type == 'text':
            this.method('messages.send', chat_id=chat_id, message=msg, v=this.API_VERSION)
        elif type == 'attachment':
            this.method('messages.send', chat_id=chat_id, attachment=msg, v=this.API_VERSION)
        
    # Doesn't work
    def invite_bot(this, bot_id, chat_id):
        peer_id = chat_id + 2_000_000_000
        print(peer_id)
        data = {'act': 'a_add_bots_to_chat',
                'al': 1,
                'add_hash': this._get_chat_hash(bot_id),
                'bot_id': -bot_id,
                'peer_ids': peer_id,
                }
                
        answer = this.session.post('https://vk.com/al_im.php',data=data)
        return answer
    def _get_chat_hash(this, bot_id):
        data = {'act': 'a_search_chats_box',
                'al': 1,
                'group_id': -bot_id
                }                
        ans = this.session.post('https://vk.com/al_groups.php', data=data)
        
        start = ans.text.find('add_hash') + 11
        length = ans.text[start:].find('"')
        hash = ans.text[start:start + length]        
        print(hash)
        return hash
