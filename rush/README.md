### Файлы
  - **rush.conf** - общие настройки, боты, аккаунты
  - **rush.log** - запись всех произведенных действий
  - **account.py** - код для взаимодействия через неофициальное API vk.com
  - **functions.py** - пользовательские функции возвращающие текст для сообщения, отправляемого ботом
  - **peer_ids.dat** - хранит полученные peer_ids бесед для каждого бота после их приглашения в беседу
  - **rush.py** - запускаемый скрипт

### Как использовать
Для начала убедитесь, что у вас установлен python3 и библиотеки к нему: urllib3, argparse, vk.
Затем создайте группу с возможностью приглашать бота, включите для него LongPoll с версией API VK 5.103.
В типах событий LongPoll установите "входящее сообщение" для того, чтобы скрипт мог понять, в какую беседу и когда был приглашен бот.

  - В rush.conf вносим аккаунты для использования скриптом, ботов и другие настройки в соответствие с примером
  
  - $ ./rush.py
  
  - Приглашаем ботов в беседу, проверяем их состояние с помощью команды **status**. Если бот был приглашен в беседу и это событие было перехвачено, то состояние бота будет установлено в "sending messages".
  
  - Чтобы начать непосредственно отправку сообщение, введите команду **unfreeze**. Если вы хотите остановить отправку сообщений можете выполнить обратную команду - **freeze**. По умолчанию все боты заморожены, сделано это по причине трудности отслеживания событий в беседе, в которую уже поступает много сообщений. Вы можете их разморозить заранее, тогда после перехвата событии о присоединении бота к беседе, он сразу начнет отправлять туда сообщение в соотвествие со своей командой. 
  
В rush.log будет записано каждое отправленное сообщение, изменение состояния бота и ошибки при отправке сообщений ботами.
При новом запуске скрипта rush.log не перезаписывается.

### Команды во время выполнения
  - **status** - показывает состояние каждого бота: кол-во отправленных сообщений, ошибки, заморожен ли бот;
  - **exit** - завершает работу скрипта, Ctrl+C делает тоже самое;
  - **help** - печатает список доступных команд;
  - **wait** ```<name>...``` - переводит бота(-ов) с именем ```<name>...``` в состоянии ожидания приглашения в беседу, полученный peer_id будет использован вместо текущего, если имя не указано, то выбираются все боты;
  - **invite** ```<chat_id>``` - каждый аккаунт с ролью Inviter выполняет три действия: вход в беседу, приглашения Main аккаунта, выход из беседы. Если какой-то Inviter успешно пригласил Main'а, то остальные ничего не делают;
  - **accounts** - выводит список существующих аккаунтов;
  - **spysend** ```<chat_id> <name> <msg_type> <msg>``` - отправление сообщения типа ```<msg_type>``` с содержимым ```<msg>``` в беседу ```<chat_id>``` от аккаунта с именем ```<name>``` в три действия: вход в беседу, отправка сообщения, выход из беседы;
  - **freeze** ```<name>...``` - бот(-ы) с именем ```<name>...``` прекращают отправлять сообщения, если имен не указано, применяется ко всем ботам;
  - **unfreeze** ```<name>...``` - бот(-ы) c именем ```<name>...``` продолжают отправлять сообщения, если имен не указано, применяется ко всем ботам;
