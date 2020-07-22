from router import Router
import json
import sqlite3
from xmlrpc import client


conn = None
cur = None
def initDB():
    global conn
    global cur
    conn = sqlite3.connect('./hashes.db')
    cur = conn.cursor()
    sql = '''
    CREATE TABLE IF NOT EXISTS BT(
        hash TEXT,
        UNIQUE(hash)
    )
    '''
    cur.execute(sql)
    conn.commit()

def cb(btHash):
    try:
        cur.execute(f'insert into BT(hash) values("{btHash}")')
        conn.commit()
        s = client.ServerProxy('http://127.0.0.1:6800/rpc')
        s.aria2.addUri('token:pbsoft', ['magnet:?xt=urn:btih:'+btHash])
        s.aria2.purgeDownloadResult('token:pbsoft')
    except sqlite3.IntegrityError:
        pass
    except:
        print(f'Error with {btHash}')
        
f = open('nodes.json','r')
j = json.loads(f.read())
initDB()
r = Router(j, cb)
r.run()
conn.close()
f.close()