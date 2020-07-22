import os
import datetime
import traceback
class tinyLogger:
    def __init__(self, delete, fmt,*files):
        #[0]->Information
        #[1]->Warning
        #[2]->Error
        #[3]->Exception
        self.__files = {}
        self.__format = fmt
        for x in files:
            if delete:
                try:
                    os.remove(x)
                except:
                    pass
            try:
                self.__files['INFO'] = files[0]
                self.__files['WARN'] = files[1]
                self.__files['ERROR'] = files[2]
                self.__files['EXCEPT'] = files[3]
            except:
                pass
    def __formatStr(self, msg, level):
        tmp = self.__format
        if tmp==None:
            tmp = '{$time} - [{$level}] - {$msg}'
        tmp = tmp.replace('{$time}', str(datetime.datetime.now()))
        tmp = tmp.replace('{$level}', level)
        tmp = tmp.replace('{$msg}', msg)
        return tmp
    def __writeFile(self, msg, level):
        try:
            f = open(self.__files[level], 'a+', encoding='utf-8')
            f.write(self.__formatStr(msg, level))
            f.close
        except:
            pass
    def info(self, msg):
        self.__writeFile(msg+"\n", 'INFO')
    def warn(self, msg):
        self.__writeFile(msg+"\n", 'WARN')
    def error(self, msg):
        self.__writeFile(msg+"\n", 'ERROR')
    def excpt(self, msg):
        self.__writeFile(msg+'\n'+traceback.format_exc(), 'EXCEPT')