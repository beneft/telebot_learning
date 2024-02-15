import telebot
import time
from mysql.connector import connect,Error

bot = telebot.TeleBot("5818529324:AAFRx09-sqm3g1XBEtM_BW65AAng3Abe_PQ", parse_mode="HTML")

try:	#подключение к бд
	connection = connect(
		host="localhost",
		user="admini",
		password="AdminiPA55",
		database="buglist")
except Error as e:
	print(e)

global header	#необязательно писать глобал, но просто чтобы видно было
global buffer
in_query = False #global

@bot.message_handler(commands=['add'])		#команда /add
def add_query(message):
	global in_query
	if not in_query:
		in_query=True
		bot.register_next_step_handler(bot.send_message(message.chat.id,"Добавление записи...\n/stop для прерывания\n\nВведите заголовок\n\n"), get_header)

def get_header(message):					#второй шаг команды /add
	global in_query
	if message.text != "/stop":
		global header
		header = message.text
		bot.register_next_step_handler(bot.send_message(message.chat.id,"\n\nВведите описание проблемы\n\n"), get_text)
	else:
		bot.send_message(message.chat.id,"Отмена операции...")
		in_query=False

def get_text(message):				#третий шаг команды /add
	global in_query
	if message.text != "/stop":
		global header
		text = message.text
		now = time.strftime('%Y-%m-%d %H:%M:%S')
		username = message.chat.first_name
		insert_query = 'INSERT INTO buglist(username,entry_date,header,entry_text) VALUES ("%s","%s","%s","%s")' % (username,now,header,text)
		with connection.cursor() as cursor:
			cursor.execute(insert_query)
			connection.commit()
		getid_query ='SELECT entry_num FROM buglist ORDER BY entry_num DESC LIMIT 1'
		with connection.cursor(buffered=True) as cursor:
			cursor.execute(getid_query)
			num = cursor.fetchone()[0]
			if num != None:
				bot.send_message(message.chat.id, "\nДобавление прошло успешно.\nНомер записи: " + str(num) + "\nВремя: " + now + "\n")
				in_query=False
			else:
				bot.send_message(message.chat.id, "Запись не найдена!")
				in_query=False
	else:
		bot.send_message(message.chat.id,"Отмена операции...")
		in_query=False

@bot.message_handler(commands=['find'])			#команда /find
def send_find_menu(message):
	mk = telebot.types.InlineKeyboardMarkup()
	butt = telebot.types.InlineKeyboardButton("Поиск по id",callback_data='ids')
	mk.add(butt)
	butt = telebot.types.InlineKeyboardButton("Поиск по ключевым словам",callback_data='key')
	mk.add(butt)
	butt = telebot.types.InlineKeyboardButton("Получить список нерассмотренных", callback_data='todo')
	mk.add(butt)
	butt = telebot.types.InlineKeyboardButton("Получить целый список",callback_data='drop')
	mk.add(butt)
	#butt = telebot.types.InlineKeyboardButton("Отмена",callback_data='cancel')
	#mk.add(butt)
	bot.send_message(message.chat.id, "\n - Поиск по id для просмотра/добавления решения\n\n - Поиск по ключевым словам для вывода\n\n - Вывод базы данных в файл\n\n*файл формируется при 15+ записях на вывод при поиске*",reply_markup=mk)
	#bot.register_next_step_handler(msg,reply_tofind)

@bot.callback_query_handler(func=lambda c: c.data)
#отвечает за inline кнопки на сообщениях бота
def reply_tofind(callback_query: telebot.types.CallbackQuery):
	global buffer
	global in_query
	barrier = ""
	if not in_query:
		for char in callback_query.message.text:
			if char.isnumeric():
				barrier+=char
			else:
				break
		# ответ на нажатие кнопки "Добавить решение"
		if callback_query.data == "addsol" and buffer==int(barrier):
			try:
				tmp = callback_query.message.text
				bot.delete_message(callback_query.message.chat.id,callback_query.message.message_id)
				bot.send_message(callback_query.from_user.id, tmp)
			except:
				bot.send_message(callback_query.from_user.id,"Извините, данный объект принадлежит закончившейся сессии.\nОн доступен, но возможны ошибки(")
			finally:
				presentsol_query = 'SELECT solutions FROM buglist WHERE entry_num = %s' % buffer
				with connection.cursor(buffered=True) as cursor:
					cursor.execute(presentsol_query)
					row = cursor.fetchone()[0]
					if row == None:
						mk = telebot.types.ReplyKeyboardMarkup()
					else:
						mk = telebot.types.ReplyKeyboardMarkup()
						butt = telebot.types.KeyboardButton("/stop")
						mk.add(butt)
				in_query=True
				bot.register_next_step_handler(bot.send_message(callback_query.from_user.id,"Введите решение",reply_markup=mk),add_sol)
		# ответ на нажатие кнопки "Поиск по id"
		if callback_query.data == "ids":
			bot.answer_callback_query(callback_query.id,"VVedite ID")
			in_query=True
			bot.register_next_step_handler(bot.send_message(callback_query.from_user.id,"Введите ID"),find_id)
		# ответ на нажатие кнопки "Поиск по ключевым словам"
		elif callback_query.data == "key":
			bot.answer_callback_query(callback_query.id,"POISK ACTEVIROVAN")
			in_query=True
			bot.register_next_step_handler(bot.send_message(callback_query.from_user.id, "Поиск по ключевому слову"),find_key)
		# ответ на нажатие кнопки "Вывести невыполненные дела"
		elif callback_query.data == "todo":
			bot.answer_callback_query(callback_query.id, "PABOTAT TREE DNJA KAMENOLOMNA")
			bot.send_message(callback_query.from_user.id, "Выгружаю невыполненные дела!")
			nullsol_query = 'SELECT entry_num,username,entry_date,header,entry_text FROM buglist WHERE solutions is null'
			with connection.cursor() as cursor:
				cursor.execute(nullsol_query)
				rows = cursor.fetchall()
				if len(rows)<=15:
					for row in rows:
							bot.send_message(callback_query.from_user.id, str(row[0]) + "\nАвтор: " + row[1] + "\n" + row[2].strftime('%Y-%m-%d %H:%M:%S') + "\nТема: " + row[3] + "\nОписание: " + row[4] + "\nРешения: Не решено!")
				else:
					file = open("todolist.txt", 'w',encoding="utf-8")
					for row in rows:
							file.write(str(row[0]) + "\nАвтор: " + row[1] + "\n" + row[2].strftime('%Y-%m-%d %H:%M:%S') + "\nТема: " + row[3] + "\nОписание: " + row[4] + "\nРешения: Не решено!\n\n")
					file.close()
					bot.send_document(callback_query.from_user.id, open("bugtracker.txt", 'r', encoding="utf-8"))
				if len(rows)==0:
					bot.send_message(callback_query.from_user.id,"Все дела выполнены!")
		# ответ на нажатие кнопки "Выгрузить в файл"
		elif callback_query.data == "drop":
			bot.answer_callback_query(callback_query.id,"PRIGOTOVTES K TOTALNOMU UNIJENIJU")
			bot.send_message(callback_query.from_user.id, "Ловите файл!")
			selectall_query = "SELECT * FROM buglist"
			with connection.cursor() as cursor:
				cursor.execute(selectall_query)
				rows = cursor.fetchall()
				file = open("bugtracker.txt", 'w',encoding="utf-8")
				for row in rows:
					if row[5] != None:
						file.write(str(row[0]) + "\nАвтор: " + row[1] + "\n" + row[2].strftime('%Y-%m-%d %H:%M:%S') + "\nТема: " + row[3] + "\nОписание: " + row[4] + "\nРешения: " + row[5] + "\n\n")
					else:
						file.write(str(row[0]) + "\nАвтор: " + row[1] + "\n" + row[2].strftime('%Y-%m-%d %H:%M:%S') + "\nТема: " + row[3] + "\nОписание: " + row[4] + "\nРешения: Не решено!\n\n")
				file.close()
				bot.send_document(callback_query.from_user.id, open("bugtracker.txt",'r',encoding="utf-8"))

def find_id(message):		#реализация поиска по id
	global buffer
	global in_query
	if message.text != "/stop" and message.text.isnumeric():
		mk = telebot.types.InlineKeyboardMarkup()
		butt = telebot.types.InlineKeyboardButton("Добавить решение",callback_data='addsol')
		mk.add(butt)
		getid_query = 'SELECT entry_num,username,entry_date,header,entry_text,solutions FROM buglist WHERE entry_num = %s' % message.text
		with connection.cursor(buffered=True) as cursor:
			cursor.execute(getid_query)
			row = cursor.fetchone()
			if row!=None:
				if row[5]!=None:
					bot.send_message(message.chat.id,str(row[0])+"\nАвтор: "+row[1]+"\n"+row[2].strftime('%Y-%m-%d %H:%M:%S')+"\nТема: "+row[3]+"\nОписание: "+row[4]+"\nРешения: "+row[5],reply_markup=mk)
					buffer = row[0]
				else:
					bot.send_message(message.chat.id,str(row[0])+"\nАвтор: "+row[1]+"\n"+row[2].strftime('%Y-%m-%d %H:%M:%S')+"\nТема: "+row[3]+"\nОписание: "+row[4]+"\nРешения: Не решено!",reply_markup=mk)
					buffer = row[0]
			else:
				bot.send_message(message.chat.id, "Запись не найдена!")
	else:
		bot.send_message(message.chat.id, "Отмена операции...")
	in_query=False

def add_sol(message):		#реализвация добавления решения
	global buffer
	global in_query
	mk = telebot.types.ReplyKeyboardRemove()
	if message.text != "/stop":
		addsol_query = 'UPDATE buglist SET solutions = "%s" WHERE entry_num=%s' % (message.text,buffer)
		with connection.cursor() as cursor:
			cursor.execute(addsol_query)
			connection.commit()
			bot.send_message(message.chat.id,"Решение успешно изменено!",reply_markup=mk)
	else:
		bot.send_message(message.chat.id,"Отмена операции...",reply_markup=mk)
	in_query=False

def find_key(message):			#реализация поиска по ключевым словам
	global in_query
	if message.text != "/stop":
		findkey_query = "SELECT entry_num,username,entry_date,header,entry_text,solutions FROM buglist WHERE entry_text LIKE '%{0}%' or username LIKE '%{0}%' or header LIKE '%{0}%'".format(message.text)
		with connection.cursor() as cursor:
			cursor.execute(findkey_query)
			rows = cursor.fetchall()
			if len(rows)<=15:
				for row in rows:
					if row[5] != None:
						bot.send_message(message.chat.id, str(row[0]) + "\nАвтор: " + row[1] + "\n" + row[2].strftime(
							'%Y-%m-%d %H:%M:%S') + "\nТема: " + row[3] + "\nОписание: " + row[4] + "\nРешения: " + row[
											 5])
					else:
						bot.send_message(message.chat.id, str(row[0]) + "\nАвтор: " + row[1] + "\n" + row[2].strftime(
							'%Y-%m-%d %H:%M:%S') + "\nТема: " + row[3] + "\nОписание: " + row[
											 4] + "\nРешения: Не решено!")
			else:
				file = open("keysearch.txt", 'w',encoding="utf-8")
				for row in rows:
					if row[5] != None:
						file.write(str(row[0]) + "\nАвтор: " + row[1] + "\n" + row[2].strftime(
							'%Y-%m-%d %H:%M:%S') + "\nТема: " + row[3] + "\nОписание: " + row[4] + "\nРешения: " + row[
											 5]+"\n\n")
					else:
						file.write(str(row[0]) + "\nАвтор: " + row[1] + "\n" + row[2].strftime(
							'%Y-%m-%d %H:%M:%S') + "\nТема: " + row[3] + "\nОписание: " + row[
											 4] + "\nРешения: Не решено!\n\n")
				file.close()
				bot.send_document(message.chat.id, open("bugtracker.txt", 'r', encoding="utf-8"))
			if len(rows) == 0:
				bot.send_message(message.chat.id,"Ничего не найдено...")
	else:
		bot.send_message(message.chat.id,"Отмена операции...")
	in_query=False

@bot.message_handler(commands=['start'])		#команда /start
def send_welcome(message):
	bot.send_message(message.chat.id, "Добро пожаловать, "+message.chat.first_name+"!\nЗдесь ты можешь добавлять свои описания багов, добавлять к ним решения и т.д. /help")

@bot.message_handler(commands=['help'])			#команда /help
def send_help(message):
	bot.send_message(message.chat.id,"Список команд:\n/help - вызов этого сообщения\n/add - добавить баг в бд\n/find - поиск записей, добавление решения к конкретной записи, вывод\n/stop - остановка некоторых операций\n/support - показать контакты\n")

@bot.message_handler(commands=['support'])		#команда /support
def send_media_menu(message):
	mk = telebot.types.InlineKeyboardMarkup()
	butt = telebot.types.InlineKeyboardButton("VK", url="https://vk.com/gravitysharp")
	mk.add(butt)
	butt = telebot.types.InlineKeyboardButton("SC", url="https://soundcloud.com/nope_pls")
	mk.add(butt)
	butt = telebot.types.InlineKeyboardButton("TG", url="https://t.me/beneft")
	mk.add(butt)
	bot.send_message(message.chat.id, "Писать сюда по вопросам:", reply_markup=mk)

@bot.message_handler(commands=['stop'])		#команда /stop
def out_of_query(message):
	global in_query
	in_query=False

@bot.message_handler(content_types=['text'])		#как дела?
def generic_reply(message):
	if message.text.lower() == "как дела" or message.text.lower() == "как дела?":
		gmt = time.localtime()
		if gmt.tm_hour>23 or gmt.tm_hour<6: bot.send_message(message.chat.id,'Спать хочется...')
		elif gmt.tm_hour>5 and gmt.tm_hour<12: bot.send_message(message.chat.id,'Я, конечно, не сплю, но с утра чувствую себя бодро!')
		elif gmt.tm_hour>11 and gmt.tm_hour<18: bot.send_message(message.chat.id,'Вполне неплохо. Спасибо, что спросил(а).')
		elif gmt.tm_hour>17 and gmt.tm_hour<=23: bot.send_message(message.chat.id,'Отдыхаю, релаксирую, отвечаю на твои запросы - расслабон...')

if __name__ == '__main__':
	bot.infinity_polling()