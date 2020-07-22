from bencode import bencode, bdecode

KRPC_QUERY = 0#q
KRPC_QUERY_PING = 'ping'
KRPC_QUERY_FIND = 'find_node'
KRPC_QUERY_GET = 'get_peers'
KRPC_QUERY_ANNOUNCE = 'announce_peer'

KRPC_ERROR = 1#e
KRPC_ERROR_GENERIC = 201
KRPC_ERROR_SERVER = 202
KRPC_ERROR_PROTOCOL = 203
KRPC_ERROR_METHOD = 204

KRPC_RESPONSE = 2#r
KRPC_RESPONSE_PING = 0
KRPC_RESPONSE_FIND = 1
KRPC_RESPONSE_GET = 2
KRPC_RESPONSE_ANNOUNCE = 3

def dhtKRPC(type, tID, reType = -1,errCode = -1,errMSG='', queFunc = '', ID = '', target='', infoHash = '', port=-1, token ='', nodes=None, values = None, implied_port = -1):
    dic = {}
    dic['t'] = tID
    dic['v'] = b'DC\x00\x01'
    if type == KRPC_ERROR:
        dic['y'] = 'e'
        dic['e'] = [errCode, errMSG]
    elif type == KRPC_QUERY:
        dic['y'] = 'q'
        dic['q'] = queFunc
        dic['a'] = {'id':ID}
        if queFunc == KRPC_QUERY_PING: pass
        if queFunc == KRPC_QUERY_FIND:
            dic['a']['target'] = target
        if queFunc == KRPC_QUERY_GET:
            dic['a']['info_hash'] = infoHash
        if queFunc == KRPC_QUERY_ANNOUNCE:
            dic['a']['implied_port'] = implied_port
            dic['a']['info_hash'] = infoHash
            dic['a']['port'] = port
            dic['a']['token'] = token
    elif type == KRPC_RESPONSE:
        dic['y'] = 'r'
        dic['r'] = {'id':ID}
        if reType == KRPC_RESPONSE_FIND:
            dic['r']['nodes'] = nodes
        if reType == KRPC_RESPONSE_GET:
            dic['r']['token'] = token
            if nodes!=None: dic['r']['nodes'] = nodes
            else: dic['r']['values'] = values
        if reType == KRPC_RESPONSE_ANNOUNCE: pass
        if reType == KRPC_RESPONSE_PING: pass
    return dic

def krpcDecode(msg): return bdecode(msg)
def krpcEncode(msg): return bencode(msg)


def ping(tID, ID):
    return dhtKRPC(KRPC_QUERY, tID = tID, queFunc=KRPC_QUERY_PING, ID = ID)

def find(tID, ID, target):
    return dhtKRPC(KRPC_QUERY, tID = tID, queFunc=KRPC_QUERY_FIND, ID = ID, target= target)

def announce(tID, ID, implied_port, infoHash, port, token):#Not Implemented yet
    return dhtKRPC(KRPC_QUERY, tID = tID, queFunc=KRPC_QUERY_ANNOUNCE, ID = ID, implied_port= implied_port, infoHash=infoHash, port=port, token=token)

def get(tID, ID, infoHash):
    return dhtKRPC(KRPC_QUERY, tID = tID, queFunc=KRPC_QUERY_GET, ID = ID, infoHash=infoHash)
     
def error(tID, errCode, errMSG):
    return dhtKRPC(KRPC_ERROR, tID=tID, errCode=errCode, errMSG=errMSG)
     
def rPing(tID, ID):
    return dhtKRPC(KRPC_RESPONSE, tID = tID, reType=KRPC_RESPONSE_PING, ID = ID)
     
def rAnnounce(tID, ID):
    return dhtKRPC(KRPC_RESPONSE, tID = tID, reType=KRPC_RESPONSE_ANNOUNCE, ID = ID)
     
def rFind(tID, ID, nodes):
    return dhtKRPC(KRPC_RESPONSE, tID = tID, reType=KRPC_RESPONSE_FIND, ID = ID, nodes = nodes)
     
def rGet(tID, ID, token, nodes = None, values = None):
    return dhtKRPC(KRPC_RESPONSE, tID = tID, reType=KRPC_RESPONSE_GET, ID = ID, nodes = nodes, values=values, token=token)