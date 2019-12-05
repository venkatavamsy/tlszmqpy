from threading import Thread
from tlszmq import TLSZmq
import zmq


class SSLWrapper(object):
    def __init__(self, zmqsocket, name, log, proto, cert, key):
        self.socket = zmqsocket
        self.tls = TLSZmq(name, log, proto, cert, key)
        self.LOG = log

    def send_recv(self, value):
        try:
            self.tls.send_string(value)
            while True:
                self.tls.update()

                if self.tls.needs_write():
                    enc_msg = self.tls.get_data()
                    print(enc_msg.encode(errors='surrogateescape'))
                    self.socket.send(enc_msg.encode(errors='surrogateescape'))

                    enc_req = self.socket.recv()
                    self.tls.put_data(enc_req)
                    self.tls.update()
            
                if self.tls.can_recv(): 
                    return self.tls.recv()
                    break
        except Exception as ex:
            self.LOG.exception(ex)

    def shutdown(self):
        self.tls.shutdown()


class ZMQTLSClient(Thread):

    def __init__(self, name, log, uri, proto, cert=None, key=None, ctx=None):
        super(ZMQTLSClient, self).__init__()

        self.name = name
        self.LOG = log
        self.proto = proto
        self.cert = cert
        self.key = key
        self.uri = uri
        self.ctx = ctx or zmq.Context(1)

    def run(self):
        subclients = 8

        for sub in range(subclients):
            ident = self.name + '____' + str(sub)
            self.socket = self.ctx.socket(zmq.REQ)
            self.socket.connect(self.uri)
            self.socket.setsockopt_string(zmq.IDENTITY, ident)

            sslw = SSLWrapper(self.socket, ident,
                              self.LOG, self.proto,
                              self.cert, self.key)

            rep = sslw.send_recv("first req: " + self.name)
            self.LOG.info("Received: %s" % rep)

            rep = sslw.send_recv("second req: " + self.name)
            self.LOG.info("Received: %s" % rep)

            self.socket.close()

            sslw.shutdown()

        self.LOG.info("Client exited")

