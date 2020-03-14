import config
import telebot
import logging
import time
from datetime import datetime
import traceback
import os
import flask
from siaskynet import Skynet

WEBHOOK_ENABLED = False

WEBHOOK_HOST = '1.1.1.1'
WEBHOOK_PORT = 443
WEBHOOK_LISTEN = '0.0.0.0'

WEBHOOK_SSL_CERT = './webhook_cert.pem'
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % config.bot_token

bot = telebot.TeleBot(config.bot_token)

@bot.message_handler(commands=['start', 'help'])
def handle_help(message):
    bot.send_message(message.chat.id, 'Hey. I\'ll upload your file to Skynet, just send me it!')


@bot.message_handler(content_types=['text', 'audio', 'document', 'photo', 'video', 'video_note', 'voice'])
def handle_message(message):
    try:
        ts = datetime.now().strftime("%H:%M:%S.%f")
        if (message.content_type == 'text'):
            file_name = 'text_message-' + ts + '.txt'
            with open(file_name, 'wt') as new_file:
                new_file.write(message.text)
        else:
            if (message.content_type == 'photo'):
                file_info = bot.get_file(message.photo[0].file_id)
            else:
                file_info = bot.get_file(getattr(message, message.content_type).file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            file_name = './' + message.content_type + ts
            with open(file_name, 'wb') as new_file:
                new_file.write(downloaded_file)
        skylink = Skynet.upload_file(file_name)
        bot.reply_to(message, 'Upload successful\n\n<b>Sia link:</b> <code>%s</code>\n\n<b>Web link:</b> %s' %
                 (skylink, skylink.replace('sia://', 'https://siasky.net/')),
                 parse_mode='HTML', disable_web_page_preview=True)
        new_file.close()
        os.remove(file_name)
    except Exception as ex:
        traceback.print_exc()
        logging.error('Exception of type {%s}: {%s}' % (type(ex).__name__, str(ex)))


app = flask.Flask(__name__)


@app.route('/', methods=['GET', 'HEAD'])
def index():
    return ''


@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)

if __name__ == '__main__':
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s', level=logging.INFO,
                         filename=config.log_name, datefmt='%d.%m.%Y %H:%M:%S')
    if WEBHOOK_ENABLED:
        bot.remove_webhook()
        logging.info('Webhook removed')
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH, certificate=open(WEBHOOK_SSL_CERT, 'r'))
        logging.info('Webhook set')
        app.run(host=WEBHOOK_LISTEN,
                port=WEBHOOK_PORT,
                ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV),
                debug=False)
        logging.info('Flask started')
    else:
        bot.polling(none_stop=True)
