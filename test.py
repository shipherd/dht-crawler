import json
import KRPC
import socket
import random
import hashlib
import uuid
import time

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', random.randint(49152, 65535)))
s.settimeout(2)
s.setblocking(False)
def genNID():
    return hashlib.sha1(uuid.uuid4().bytes).digest()
nid = genNID()
def g(): return b'%c%c' % (random.randint(0, 255), random.randint(0, 255))#33 ,126

def parseNode(node):
    return (node[0:20], '%d.%d.%d.%d' % (node[20], node[21], node[22], node[23]), '%d' % (int.from_bytes(node[24:26], 'big')))

def parseNodes(nodes): 
    l = list(nodes[i:i+26] for i in range(0, len(nodes), 26))
    n = []
    for x in l:
        n.append(parseNode(x))
    return n



print(f'self:{nid}')
rl = []
while True:
    print(':', end='')
    val = input()
    ary = val.split(' ')
    if ary[0] == 'r':
        for x in rl:
            msg = None
            if ary[1] == 'p':
                msg = KRPC.ping(g(),nid)
            if ary[1] == 'f':
                msg = KRPC.find(g(),nid,nid)
            print(f'Sending MSG:{msg} to {x}')
            s.sendto(KRPC.krpcEncode(msg), x)
        while True:
            d ,a = s.recvfrom(65535)
            print(f'Received from {a}, ->{dict(KRPC.krpcDecode(d))}')


    if ary[0] == 'p':
        msg = KRPC.ping(g(),nid)
        print(f'Sending MSG:{msg}')
        s.sendto(KRPC.krpcEncode(msg), (ary[1], int(ary[2])))
        time.sleep(2)
        try:
            d ,a = s.recvfrom(65535)
            print(f'RAW:{dict(KRPC.krpcDecode(d))}')
            print(f'{dict(KRPC.krpcDecode(d))} from {a} with nid: {dict(KRPC.krpcDecode(d))["r"]["id"].hex()}')
        except BlockingIOError:
            print('No data received')

    if ary[0] == 'f':
        msg = KRPC.find(g(),nid,nid)
        print(f'Sending MSG:{msg}')
        s.sendto(KRPC.krpcEncode(msg), (ary[1], int(ary[2])))
        time.sleep(2)
        d ,a = s.recvfrom(65535)
        dic = KRPC.krpcDecode(d)
        print(f'RAW:{dic}')
        n = dic['r']['nodes']
        print(f'From {a} with nid: {dic["r"]["id"].hex()}, returned nodes:')
        for x in parseNodes(n):
            rl.append((x[1],int(x[2])))
            print(f'{x[0].hex()}|{x[1]}:{x[2]}')
    if ary[0]=='pf':
        s.setblocking(False)
        allNodes = json.loads(open('nodes.json','r').read())
        for x in allNodes:
            msg = KRPC.krpcEncode(KRPC.ping(g(),nid))
            s.sendto(msg,(x['name'],x['port']))
        while True:
            try:
                time.sleep(2)
                d,a = s.recvfrom(65535)
                print(f'from {a}:{KRPC.krpcDecode(d)}')
            except BlockingIOError:
                print('No data')