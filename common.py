import os

VIDEO_H264 = 0
VIDEO_MJPEG = 1
VIDEO_RAW = 2

# Возвращает температуру процессора
def getCPUtemperature():
    res = os.popen('vcgencmd measure_temp').readline()
    return float(res.replace('temp=','').replace('\'C\n',''))

# проверка доступности камеры, возвращает True, если камера доступна в системе
def checkCamera():
    res = os.popen('vcgencmd get_camera').readline().replace('\n','') #читаем результат, удаляем \n
    dct = {}
    for param in res.split(' '): #разбираем параметры
        tmp = param.split('=')
        dct.update({tmp[0]: int(tmp[1])}) #помещаем в словарь
    return (dct['supported'] and dct['detected'])

def getIP():
    #cmd = 'hostname -I | cut -d\' \' -f1'
    #ip = subprocess.check_output(cmd, shell = True) #получаем IP
    res = os.popen('hostname -I | cut -d\' \' -f1').readline().replace('\n','') #получаем IP, удаляем \n
    return res
