import time
import socket
import random
import hashlib
import json
import uuid
import KRPC
#import logging
import TinyLogger
import os
import threading
from bencode import exceptions
BKT_SUCCEED = 0
BKT_FULL = -1
BKT_NOT_IN_RANGE = -2
BKT_EXIST = -3

logger = TinyLogger.tinyLogger(True, None, './info.log','./warning.log', './error.log', './exception.log')
class Node:
    def __init__(self, IP, port, nodeID):
        self.__IP = IP
        self.__port = port
        self.__nodeID = nodeID
        self.__timeStamp = time.time()

    def updateTimeStamp(self, time): self.__timeStamp = time
    def getNodeInfo(self): return {'name': self.__IP,
                                   'port': self.__port, 'nID': self.__nodeID}
    def getIPPort(self):return (self.__IP, self.__port)
    def getNodeID(self):return self.__nodeID
    def getIP(self):return self.__IP
    def getPort(self):return self.__port
    def isFresh(self): return (time.time()-self.__timeStamp) <= 15*60#15 minutes


class Bucket:
    def __init__(self, minRage, maxRage, kSize):
        self.__nodes = []
        self.__timeStamp = time.time()
        self.__minRage = minRage
        self.__maxRage = maxRage
        self.__kSize = kSize
    
    def updateTimeStamp(self, time): self.__timeStamp = time
    def getRange (self):return (self.__minRage, self.__maxRage)
    def getNodes(self): return self.__nodes
    def isFresh(self): return (time.time()-self.__timeStamp) <= 15*60  # 15 minutes
    def addNode(self, node):
        intID = int.from_bytes(node.getNodeInfo()['nID'], byteorder='big', signed= False)
        if intID>self.__maxRage or intID<self.__minRage:return BKT_NOT_IN_RANGE
        if len(self.__nodes)==self.__kSize: return BKT_FULL
        for x in self.__nodes:
            if x.getNodeInfo()['nID'].hex() == node.getNodeInfo()['nID'].hex():return BKT_EXIST
        self.__nodes.append(node)
        return BKT_SUCCEED
    def delNode(self, node):
        self.__nodes.remove(node)
    def getCompactNodeInfo(self):
        nodes = b''
        for x in self.__nodes:
            compactNode = x.getNodeID()
            tmp = socket.gethostbyname(x.getIP()).split('.')
            for y in tmp:
                compactNode+= b'%c'%(int(y))
            try:
                compactNode+= x.getPort().to_bytes(2,byteorder='big')
            except:
                logger.excpt(f'{"%x"%(x.getPort())}|{x.getNodeInfo()}')
            nodes+=compactNode
        return nodes



class Table:
    def __init__(self, kSize, nBits):
        self.__buckets = [Bucket(0, 2**nBits-1, kSize)]
        self.__kSize = kSize

    def getBuckets(self): return self.__buckets
    def __splitBucket(self, index):
        bkt = self.__buckets[index]
        tmpNodes = bkt.getNodes()
        #Calc New Ranges
        min,max = bkt.getRange()
        half = int((max+1-min)/2)
        lMin = min
        lMax = lMin+half-1
        rMin = lMax + 1
        rMax = max
        #Create New Buckets
        lBKT = Bucket(lMin, lMax, self.__kSize)
        rBKT = Bucket(rMin, rMax, self.__kSize)
        self.__buckets.insert(index, lBKT)
        self.__buckets.insert(index+1, rBKT)
        for x in tmpNodes:
            self.addNode(x)
        del self.__buckets[index+2]

        
    def addNode(self, node):
        state = 1
        index = -1
        for i in range(0,len(self.__buckets)):
            bkt = self.__buckets[i]
            state = bkt.addNode(node)
            if state == BKT_EXIST: 
                break
            if state == BKT_NOT_IN_RANGE: continue
            else: 
                index = i
                break
        if state == BKT_FULL:
            self.__splitBucket(index)
            self.addNode(node)
    #Not implemented correctly
    def findNear(self, hashVal):
        for x in self.__buckets:
            val = int.from_bytes(hashVal, byteorder='big', signed= False)
            min, max = x.getRange()
            if min<=val<=max:
                return x.getCompactNodeInfo()
    def countNodes(self):
        c = 0
        for x in self.__buckets:
            c+=len(x.getNodes())
        return c

class Router:
    def __init__(self, nodes, hashCallBack):
        #logging.basicConfig(filename= './router.log', filemode='w', format='%(asctime)s - [%(levelname)s] : %(message)s', level=logging.DEBUG)
        self.__table = Table(12, 160)
        self.__nodeID = hashlib.sha1(uuid.uuid4().bytes).digest()
        logger.info(f'Initialize Self-Node ID: {self.__nodeID.hex()}, length: {len(self.__nodeID)} bytes')
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        port = random.randint(49152, 65535)
        self.__socket.bind(('0.0.0.0', port))
        logger.info(f'Initialize Router Port: {port}')
        self.__socket.setblocking(False)
        self.__initNodes = nodes
        self.__pFunc = {
            'r':self.__processResponse,
            'e':self.__processError,
            'q':self.__processQuery
        }
        self.__tokenList = []
        self.__hashCB = hashCallBack
    def __logTable(self):
        bkts = self.__table.getBuckets()
        logger.info(f'Table now has {len(bkts)} bucket(s) with {self.__table.countNodes()} node(s)')
        for i in range(0, len(bkts)):
            logger.info(f' bucket {i} has {len(bkts[i].getNodes())} node(s):')
            for x in bkts[i].getNodes():
                logger.info(f'     nID:{x.getNodeID().hex()}->{x.getIPPort()}')

    def __saveTMPNodes(self):
        logger.info(f'{self.__table.countNodes()} node(s)')
        if os.path.exists('./tmp.json'):
            os.remove('./tmp.json')
        
        f = open('./tmp.json','w')
        lst = []
        for x in self.__table.getBuckets():
            for y in x.getNodes():
                n = {'name': y.getIP(), 'port':y.getPort(), 'nID':y.getNodeID().hex()}
                lst.append(n)
        j = json.dumps(lst)
        f.write(j)
        f.close()

        
    def __send(self, to, msg): 
        try:
            if to[1]==0:return#filter port zero
            self.__socket.sendto(KRPC.krpcEncode(msg), to)
        except:
            logger.excpt(f'Exception at __send:{to}|{msg}')
    def __recv(self): return self.__socket.recvfrom(65535)
    def __genTID(self):
        return b'%c%c' % (random.randint(0, 255), random.randint(0, 255))
    def __genToken(self):
        return b'%c%c%c%c' % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    def __parseNode(self,node):
        return (node[0:20], '%d.%d.%d.%d' % (node[20], node[21], node[22], node[23]), int('%d' % (int.from_bytes(node[24:26], 'big'))))

    def __parseNodes(self, nodes):
        l = list(nodes[i:i+26] for i in range(0, len(nodes), 26))
        n = []
        for x in l:
            n.append(self.__parseNode(x))
        return n#format: [(nID,IP,port),...]
    def __sendPing(self, addr):
        tID = self.__genTID()
        msg = KRPC.ping(tID, self.__nodeID)
        self.__send(addr, msg)
    def __sendFindSelf(self, addr):
        tID = self.__genTID()
        msg = KRPC.find(tID, self.__nodeID, self.__nodeID)
        self.__send(addr, msg)

    def __parseHash(self, hashVal):
        if type(hashVal)==str:
            try:
                return bytes.fromhex(hashVal)
            except ValueError:
                return hashVal.encode('utf-8')
        return hashVal

    def __workerThread(self, func, flag, interval,*args):
        while flag[0]:
            time.sleep(interval)
            if args[0]==None:func()
            else:func(*args)
    def __initDHTNetwork(self):
        #logging.info(f'nodes.json: {[["%s:%s with nID: %s"%(x["name"], x["port"], x["nID"])] for x in self.__initNodes]}')
        if self.__initNodes==[] or self.__initNodes==None:
            raise Exception('No init Nodes found')
        for x in self.__initNodes:
            self.__sendPing((x['name'], x['port']))
            #logging.info(f'Init Ping: {x["nID"]}')
        y = [True]
        thd = threading.Thread(target=self.__workerThread, args=(self.__saveTMPNodes, y, 60*15, None))
        thd.start()
    def __sendError(self, addr, code,msg):
        tID = self.__genTID()
        data = KRPC.error(tID,code, msg)
        self.__send(addr, data)
    def __processError(self, data, address):
        pass
        #logging.warning(f'Server {address} returns an error: {data["e"]}')
    def __processQuery(self, data, address):
        try:
            tID = data['t']
            func = data['q']
            params = data['a']
            
            nID = self.__parseHash(params['id'])
            if nID.hex()== self.__nodeID.hex():return

            #logging.debug(f'Processing :{params["id"].hex()}')
            n = Node(address[0],address[1],nID)
            self.__table.addNode(n)

            if func==KRPC.KRPC_QUERY_FIND:
                msg = KRPC.rFind(tID, self.__nodeID, self.__table.findNear(self.__parseHash(params['target'])))
                #logging.debug(f'rFind_Nodes:{msg}')
                self.__send(address, msg)
            elif func==KRPC.KRPC_QUERY_PING:
                msg = KRPC.rPing(tID, self.__nodeID)
                #logging.debug(f'rPing:{msg}')
                self.__send(address, msg)
            elif func==KRPC.KRPC_QUERY_GET:#No PEERS implemented!
                token = self.__genToken()
                self.__tokenList.append(token)
                msg = KRPC.rGet(tID, self.__nodeID, token, nodes=self.__table.findNear(self.__parseHash(params['info_hash'])))
                #logging.debug(f'rGet_Peers:{msg}')
                #logger.warn(f'Info Hash: {self.__parseHash(params["info_hash"]).hex()}')
                self.__hashCB(self.__parseHash(params["info_hash"]).hex())
                self.__send(address, msg)
            elif func==KRPC.KRPC_QUERY_ANNOUNCE:#Not yet implemented
                #logger.warn(f'Info Hash: {self.__parseHash(params["info_hash"]).hex()}')
                self.__hashCB(self.__parseHash(params["info_hash"]).hex())
                msg = KRPC.rAnnounce(tID, self.__nodeID)
                #logging.debug(f'rAnnounce:{msg}')
                self.__send(address, msg)
            elif func=='vote':#ignore vote
                self.__sendError(address, KRPC.KRPC_ERROR_METHOD, 'Not Implemented')
            elif func=='sample_infohashes':
                #not implemented
                self.__sendError(address, KRPC.KRPC_ERROR_METHOD, 'Not Implemented')
            else:
                logger.error(f'Unhandled Method! From:{address}|{data}')
                self.__sendError(address, KRPC.KRPC_ERROR_METHOD, 'Unknown Method')
        except:
            logger.excpt(f'Fatal Error in __processQuery: {address}{data}')
            

    def __processResponse(self, data, address):
        response = data['r']
        keys = response.keys()
        try:
            nID = self.__parseHash(response['id'])
            if nID.hex()==self.__nodeID.hex():return
            n = Node(address[0], address[1],nID)
            self.__table.addNode(n)
        except:
            logger.excpt(f'From {address}|{data}')

        if 'nodes' in keys and 'token' not in keys:
            nodes = response['nodes']
            nodes = self.__parseHash(nodes)
            parsedNodes = self.__parseNodes(nodes)
            for x in parsedNodes:
                if x[0].hex()==self.__nodeID.hex():continue
                self.__sendPing((x[1],x[2]))
                #logging.info(f'response nodes Ping:{x[0].hex()}')
        if 'token' in keys:
            if 'nodes' in keys:
                pass
            if 'values' in keys:
                pass

    def __makeFriendsAndUpdate(self):
        for x in self.__table.getBuckets():
            for y in x.getNodes():
                if y==None:break
                if not y.isFresh():
                    self.__sendFindSelf(y.getIPPort())
                    #logging.info(f'find_node and del: {y.getNodeID().hex()}')
                    x.delNode(y)
    def __findSubBytesStrIndex(self,mainStr, subStr):
        a = list(mainStr)
        b = list(subStr)
        for x in range(len(b)):
            for y in range(len(a)):
                if a[y]==b[x]:
                    flag = False
                    for z in range(len(b)):
                        if a[y+z]!=b[z]:
                            flag=True
                            break
                    if not flag:return y+z-len(b)
        return 0
    def __looseResponse(self, data, address):
        try:
            i = self.__findSubBytesStrIndex(data, b'info_hash')
            if i!=0:
                infoHash = data[i+13:i+33]
                self.__hashCB(self.__parseHash(infoHash).hex())
        except:
            pass
        finally:
            self.__sendError(address, KRPC.KRPC_ERROR_PROTOCOL, 'Not A Valid Bencoded String')
    def run(self):
        try:
            self.__initDHTNetwork()
            while True:
                try:
                    time.sleep(0.01)
                    data, address = self.__recv()
                    try:
                        data = KRPC.krpcDecode(data)
                        self.__pFunc[data['y']](data,address)
                    except exceptions.BencodeDecodeError:
                        self.__looseResponse(data, address)
                    except TypeError:
                        logger.excpt(f'Data: {data}, address: {address}')
                    except IndexError:
                        logger.excpt(f'Data: {data}, address: {address}')
                    except KeyError:
                        self.__sendError(address, KRPC.KRPC_ERROR_PROTOCOL, 'Not A Valid Bencoded String')
                except BlockingIOError:
                    self.__makeFriendsAndUpdate()
        except:
            logger.excpt('Unhandled exception occured in router.run()')