# RPicam-Streamer
Библиотека для Python3, предназначенная для организации трансляции RTP видеопотока с камеры Raspberry Pi и параллельной обработки кадров потока средствами OpenCV.

## Описание
Библиотека содержит класс `RPiCamStreamer` для организации трансляции RTP видеопотока в форматах h264/mjpeg на удаленный хост и одновременно имеется возможность получать кадры потока в реальном времени для обработки средствами OpenCV.
Пример работы в файле `example.py`.
Для демонстрации работы примера `example.py` на удаленной машине необходимо иметь работающий RTP приемник видеопотока. В качестве приемника могут быть использованы bash скрипты `recv_h264.sh` или `recv_mjpeg.sh` в зависмости от типа используемого формата кодирования. В файлах `example.py`, `recv_h264.sh` и `recv_mjpeg.sh` необходимо правильно задать IP адреса.

## Установка необходимых пакетов и библиотек на Raspberry Pi
Gstreamer1.0  
```$ sudo apt install libgstreamer1.0-0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-doc gstreamer1.0-tools```

gstreamer1.0-omx  
```$ sudo apt install gstreamer1.0-omx```

libatlas-base-dev  
```$ sudo apt install libatlas-base-dev```

gi  
```$ sudo apt install python3-gi```

Установщик пакетов Python3 Pip3  
```$ sudo apt install python3-pip```

Библиотека OpenCV для Python3  
```$ sudo pip3 install opencv-python```

Библиотека для работы с камерой Raspberry Pi  
```$ sudo pip3 install picamera```

Библиотека для работы с ОС psutil  
```$ sudo pip3 install psutil```

## Подключение камеры

**Шлейф от камеры подсоединять к разъему только на выключенной Raspberry Pi.** Для работы с камерой Raspberry Pi необходимо её включить в ОС Raspbian запустив  
```$ sudo raspi-config```  
В меню выбрать `Interfacing Options -> Camera -> Yes`

## Подключение библиотеки в Python3
```import raspicam```
