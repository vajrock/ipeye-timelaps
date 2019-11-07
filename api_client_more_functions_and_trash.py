import requests
import json
import os
import sys
from datetime import datetime, timedelta
import time
from requests.auth import HTTPBasicAuth
import cv2

#
# Python 3
# Скрипт для формирования таймлапса с камер ipeye
# Only Windows
#

api_server = "api.ipeye.ru"
api_port = 8111
api_login = ""
api_password = ""
api_timeout = 2

timelapsTimer = 30 # частота запуска скрипта планировщиком в минутах
timeZoneDelta = -4 # Разница в часовых поясах

cams_json = '{"cam1": {"name": "Camera1", "uuid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}, "cam2": {"name": "Camera2", "uuid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}}'
cams = json.loads(cams_json)

LogEnable = 1 # включить логирование
log_file_path = os.environ['TEMP'] + "\\" + "ipeye_log_file.txt" # лог файл всех дейсвий в C:\Users\<username>\AppData\Local\Temp\ipeye_log_file.txt

#подчистить перед публикацией
workdir = "EDITTHIS:\\EDITTHIS\\EDITTHIS\\" # каталог синхронизируемый с облаком (не забыть про экранирование \\)

api_url = "http://" + api_server + ":" + str(api_port)

#############################################################
# Конец определения параметров и начало определения функций #
#############################################################

# Функция записи текста в лог
def writeLog(logdata):
	if LogEnable == 1:
		log_time = datetime.now()
		log_time = log_time.isoformat(timespec='seconds')
		log_file = open(log_file_path, "a+")
		log_file.write(log_time + ": " + str(logdata) + "\n")
		log_file.close
	else:
		return True

# getApiResponse отвечает для выполнения корректного запроса к API IPEYE
# метод POST - пережиток этапа тестирования. В последней версии POST запросы не выполняются
def getApiResponse(method, api_uri):
	if method == "GET":
		try:
			r = requests.get(api_url + api_uri, timeout = api_timeout)
			r.raise_for_status() # включаем обработку HTTP ошибок в эксепшенах
		except requests.exceptions.Timeout:
			writeLog("Error. Timeout. Request Uri:" + api_uri)
		except requests.exceptions.TooManyRedirects:
			writeLog("Error. TooManyRedirects or bad URL. Request Uri:" + api_uri) 
		except requests.exceptions.RequestException as e:
			writeLog("Error. Fatal error: " + str(e) + " Request Uri:" + api_uri) 
			sys.exit(1)
		except requests.exceptions.HTTPError as e:
			writeLog("Error. HTTP error: " + str(e) + " Request Uri:" + api_uri)
	if method == "POST":
		try:
			r = requests.post(api_url + api_uri, timeout = api_timeout)
			r.raise_for_status() # включаем обработку HTTP ошибок в эксепшенах
		except requests.exceptions.Timeout:
			writeLog("Error. Timeout. Request Uri:" + api_uri)
		except requests.exceptions.TooManyRedirects:
			writeLog("Error. TooManyRedirects or bad URL. Request Uri:" + api_uri) 
		except requests.exceptions.RequestException as e:
			writeLog("Error. Fatal error: " + str(e) + " Request Uri:" + api_uri) 
			sys.exit(1)
		except requests.exceptions.HTTPError as e:
			writeLog("Error. HTTP error: " + str(e) + " Request Uri:" + api_uri)

	return r

# Функция-пережиток. В последней версии не используется, т.к. для работы через авторизацию требуется заключение договора сервисом IPEYE
def getApiResponseAuth(method, api_uri):
	if method == "GET":
		try:
			r = requests.get(api_url + api_uri, timeout = api_timeout, auth = HTTPBasicAuth(api_login, api_password))
			r.raise_for_status()
		except requests.exceptions.Timeout:
			writeLog("Error. Timeout. Request Uri:" + api_uri)
		except requests.exceptions.TooManyRedirects:
			writeLog("Error. TooManyRedirects or bad URL. Request Uri:" + api_uri) 
		except requests.exceptions.RequestException as e:
			writeLog("Error. Fatal error: " + str(e) + " Request Uri:" + api_uri) 
			sys.exit(1)
		except requests.exceptions.HTTPError as e:
			writeLog("Error. HTTP error: " + str(e) + " Request Uri:" + api_uri)
	if method == "POST":
		try:
			r = requests.post(api_url + api_uri, timeout = api_timeout, auth = HTTPBasicAuth(api_login, api_password))
			r.raise_for_status()
		except requests.exceptions.Timeout:
			writeLog("Error. Timeout. Request Uri:" + api_uri)
		except requests.exceptions.TooManyRedirects:
			writeLog("Error. TooManyRedirects or bad URL. Request Uri:" + api_uri) 
		except requests.exceptions.RequestException as e:
			writeLog("Error. Fatal error: " + str(e) + " Request Uri:" + api_uri) 
			sys.exit(1)
		except requests.exceptions.HTTPError as e:
			writeLog("Error. HTTP error: " + str(e) + " Request Uri:" + api_uri)

	return r

# Запрос статуса работы сервера через API. Возвращает 1, если сервер готов отвечать на запросы
def getServerStatus():
	api_uri = "/info"
	# response = getApiResponse("GET", api_uri)
	response = json.loads(getApiResponse("GET", api_uri).text)
	writeLog("Server status:" + str(response["status"]) + " Version:" + response["message"])
	return response["status"]

# выкинуть нахер - не работает. Нужен договор
def getDevicesId():
	api_uri = "/devices/all"
	response = getApiResponseAuth("GET", api_uri)
	# response = json.loads(getApiResponse("GET", api_uri).text)
	print(response.text)
	# writeLog("Server status:" + str(response["status"]) + " Version:" + response["message"])	

	
# saveJpegFromCache сохраняет скриншот камеры из кеша потока IPEYE. Судя по поведению мобильного приложения и веб-сайта, кеш можно вытащить, даже, если поток лежит.
# подводный камень данной схемы - API сервер отдает 608*342 изображение, хоть камера пишется в FullHD
def saveJpegFromCache(uuid, name):
	api_uri = "/device/thumb/cache/" + uuid + "/1920/" + name
	writeLog("Trying save Cache screenshot for camera: " + name)
	response = getApiResponse("GET", api_uri)
	content_type = response.headers.get('content-type')
	if content_type is None:
		writeLog("Nothing to save")
		return False
	if 'text' in content_type.lower() or 'html' in content_type.lower():
		writeLog("Received text data: " + response.content.decode("utf-8")) 
		return False
	else:
		filename = dirToSave + "\\" + name + "-" + today.strftime("%Y-%m-%d-%H-%M-%S") + ".jpg"
		screenshot = open(filename, "wb")
		screenshot.write(response.content)
		screenshot.close()
		writeLog("File saved as: " + filename)
		return True

# saveJpegFromStream сохраняет скриншот камеры из потока IPEYE.
# подводный камень данной схемы - API сервер отдает 608*342 изображение, хоть камера пишется в FullHD		
def saveJpegFromStream(uuid, name):
	# api_uri = "/device/thumb/online/" + uuid + "/1920/" + name
	api_uri = "/device/jpeg/online/" + uuid + "/" + name
	writeLog("Trying save Stream screenshot for camera: " + name)
	response = getApiResponse("GET", api_uri)
	content_type = response.headers.get('content-type')
	if content_type is None:
		writeLog("Nothing to save")
		return False
	if 'text' in content_type.lower() or 'html' in content_type.lower():
		writeLog("Received text data: " + response.content.decode("utf-8")) 
		return False
	else:
		filename = dirToSave + "\\" + name + "-" + today.strftime("%Y-%m-%d-%H-%M-%S") + ".jpg"
		screenshot = open(filename, "wb")
		screenshot.write(response.content)
		screenshot.close()
		writeLog("File saved as: " + filename)
		return True

# Функция захвата RTSP потока и замутки скриншота из него.		
def saveJpegFromRTSP(name, rtspLink):
	writeLog("Trying save RTSP screenshot for camera: " + name)
	rtspClient = cv2.VideoCapture(rtspLink)
	
	if rtspClient.isOpened():
		_,frame = rtspClient.read()
		rtspClient.release() # закрываем поток сразу после получения карда
		if _ and frame is not None:
			filename = dirToSave + "\\" + name + "-" + today.strftime("%Y-%m-%d-%H-%M-%S") + ".jpg"
			cv2.imwrite(filename, frame)
			writeLog("File saved as: " + filename)
			return True
	else:
		writeLog("Can't read RTSP stream")
		return False

def checkStreamStatus(uuid, name):
	api_uri = "/device/status/" + uuid
	writeLog("Trying check stream status for " + name + " " + uuid)
	response = json.loads(getApiResponse("GET", api_uri).text)
	writeLog("Stream status " + uuid + ": " + str(response["status"]))
	return response["status"]

# Расширенное инфо о потоке. Не используется
def getStreamInfo(uuid, name):
	api_uri = "/device/info/" + uuid
	writeLog("Trying get stream info for " + name + " " + uuid)
	response = json.loads(getApiResponse("GET", api_uri).text)
	writeLog("Stream status uuid: " + str(response))
	return response["message"]

# Функция получения чистой ссылки на RTSP поток
def getStreamRTSP(uuid, name):
	api_uri = "/device/url/rtsp/" + uuid
	writeLog("Trying get stream RTSP link for " + name + " " + uuid)
	response = json.loads(getApiResponse("GET", api_uri).text)
	writeLog("Stream RTSP link for " + name + ": " + str(response["message"]))
	return str(response["message"])

# makeVideoFile() отвечает за формирование видеофайла из изображений
def makeVideoFile(name):

	height = 1080
	width = 1920
	
	# video = cv2.VideoWriter(dirToSave + "\\Video" + name + ".avi", cv2.VideoWriter_fourcc(*'DIVX'), 1,(width,height))
	video = cv2.VideoWriter(dirToSave + "\\Video" + name + ".mp4", cv2.VideoWriter_fourcc(*'mp4v'), 1,(width,height))
		
	# Получаем список изображений и фильтруем по паттерну "ИмяКамеры-"
	# В названии видео фалов "-" не используется, что бы не попасть под этот фильтр
	# на этапе тестирования использовались разные форматы изображений и фильтр по формату не использовался
	# Если хочется это поправить, то после первого фильтра можно добавить второй: screenshots = list(filter(lambda x: x.endswith(".jpg"), screenshots))
	files = os.listdir(dirToSave)
	screenshots = list(filter(lambda x: x.startswith(name + "-"), files))

	for screenshot in screenshots:
		origImage = cv2.imread(dirToSave + "\\" + screenshot)
		# Если изображение, пихуемое в видео поток, не соответсвует по габаритам потока - ничего не запихнется... Поэтому резайзим
		# Зачем ресайзить, если мы взяли до этого изображение из FullHD потока? Что бы была возможность добавить в видео изображение полученное через API
		heightOrig, widthOrig, channelsOrig = origImage.shape
		if height != heightOrig or width != widthOrig:
			img = cv2.resize(origImage, (width, height))
			video.write(img)
		else:
			video.write(origImage)
	cv2.destroyAllWindows()
	video.release()
	
	
####################################################
# Конец определения функций начало основной логики #
####################################################

writeLog("Script started")

today = datetime.today() + timedelta(hours = timeZoneDelta)
dirToSave = workdir + today.strftime("%Y.%m.%d")

# создаем папки
if not os.path.exists(workdir):
	os.mkdir(workdir)

if not os.path.exists(dirToSave):
	os.mkdir(dirToSave)

# проверяем статус сервера
if getServerStatus() == 0:
	writeLog("API Server unreachable. Exiting")
	sys.exit(1)

# мутим фоточки для всех указанных камер
for key, cam in cams.items():
	if checkStreamStatus(cam["uuid"], cam["name"]):
		saveJpegFromRTSP(cam["name"], getStreamRTSP(cam["uuid"], cam["name"]))
	else:
		saveJpegFromCache(cam["uuid"], cam["name"])


# Fake time for test
# today = datetime(2019, 11, 8, 3, 53, 59) + timedelta(hours = timeZoneDelta)

# определям заврашнюю дату и определяем последний ли это запуск скрипта в этих сутках
# если последний формируем видео по каждой камере

tomorrow = (today + timedelta(days = 1)).replace(hour = 0, minute = 0, second = 0)

today_ts = time.mktime(today.timetuple())
tomorrow_ts = time.mktime(tomorrow.timetuple())

if int(tomorrow_ts - today_ts) / 60 < timelapsTimer:
	writeLog("Making video files")
	for key, cam in cams.items():
		makeVideoFile(cam["name"])

writeLog("Script ended")