import sys
sys.path.insert(0, 'lib')

from askfm import *
client = AskFmClient()

client._load_cookie_jar()
client.logged_in = True

#client.login('penniesarerich', raw_input('Password for penniesarerich: '))
#client._save_cookie_jar()

questions = client.get_inbox_questions()

#client.ask_question('penniesarerich', 'Who are you', anon=False)
