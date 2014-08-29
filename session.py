from collections import OrderedDict
from json import dumps
import random
import time
import sys
from pprint import pprint

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor, defer, task
import redis

from pyrad.packet import AuthPacket, AcctPacket, PacketError, AccessAccept, AccessReject
from utils import gen_nas_port, gen_mac_address
from config import SESSION_TIME_LIST, UPDATE_INTERVAL, SERVER_IP
from config import SECRET, TIMEOUT, RETRY, DICT, USERS_DATA_FILE, USERS
from log import Stats


class Session(DatagramProtocol):

    def __init__(self, db, username, password, **spec):
        self.db = db
        self.username = username

        self.server_ip = SERVER_IP
        self.auth_port = 1812
        self.accounting_port = 1813
        self.timeout_defer = None
        self.radius_packet_args = {
            'secret': SECRET,
            'dict': DICT,
            'User_Name': username
        }

        # session spec
        self.password = password
        self.mac = spec.get('mac', None)
        self.client_ip = spec.get('client_ip', None)
        self.nas_ip = spec.get('nas_ip', '127.0.0.1')

        # accounting data
        self.framed_ip = spec.get('framed_ip', None)
        self.interim_update = spec.get('interim_update', 60)

        self.session_time_limit = random.choice(SESSION_TIME_LIST)
        self.last_interim_update = None
        self.last_state = None
        self.accounting_session_id = None

        self.accounting_input_octets = 0
        self.accounting_output_octets = 0
        self.accounting_input_pkts = 0
        self.accounting_output_pkts = 0

        self.request_count = 0
        self.last_request_time = 0
        self.total_auth_time = 0
        self.total_accounting_time = 0
        self.total_response_time = 0
        self.rejected_access_count = 0

        # self.log('Session Started')

    # def __setattr__(self, name, value):
    #     self.__dict__[name] = value
    #     whitelist = [
    #         'accounting_timeouts', 'rejected_access_count', 'auth_timeouts', 'request_count',
    #         'total_accounting_time', 'total_auth_time', 'total_response_time'
    #     ]
    #     if name in whitelist:
    #         self.db.hset('INFO_{}'.format(self.username), name, value)

    def startProtocol(self):
        d = defer.Deferred()
        delay = 1
        # self.log('Delay sat', delay=delay)
        reactor.callLater(delay, self.authenticate, d)

        return d

    def authenticate(self, d=None):
        self.auth_timeouts = 0
        self.accounting_timeouts = 0

        self.last_state = 'auth'
        auth_packet = AuthPacket(**self.radius_packet_args)
        self.gen_radius_packet(auth_packet)

        self.log('Sending Authentication Data')
        self.auth_pkt_data = auth_packet.RequestPacket()
        return self._send_data(self.auth_port, self.auth_pkt_data)

    def _send_data(self, port, data):
        self.last_request_time = time.time()
        self.request_count += 1
        self.log('Sending Data', port=port)

        self.transport.write(data, (self.server_ip, port))

        self.timeout_defer = defer.Deferred()
        self.timeout_defer.addErrback(self.handleFailure)
        reactor.callLater(TIMEOUT, self.retry_send)
        return self.timeout_defer

    def retry_send(self):
        if self.last_state == 'auth':
            self.log('Time Out, Resending Data', last_state=self.last_state, auth_timeouts=self.auth_timeouts)
            if self.auth_timeouts <= RETRY:
                self.auth_timeouts += 1
                return self._send_data(self.auth_port, self.auth_pkt_data)
            else:
                reactor.callLater(random.randint(20, 60), self.authenticate)
        elif self.last_state == 'accounting_start':
            self.log('Time Out, Resending Data', last_state=self.last_state, accounting_timeouts=self.accounting_timeouts)
            if self.accounting_timeouts <= RETRY:
                self.accounting_timeouts += 1
                return self._send_data(self.accounting_port, self.accounting_start_pkt_data)
            else:
                self.stop_accounting()
                reactor.callLater(random.randint(10, 40), self.authenticate)

    def datagramReceived(self, data, (host, port)):
        response_time = time.time() - self.last_request_time
        self.total_response_time += response_time

        if port == self.auth_port:
            _Type = AuthPacket
            self.total_auth_time += response_time
        else:
            _Type = AcctPacket
            self.total_accounting_time += response_time

        self.log(
            'Received Data', delay=response_time,
            data_type='auth' if port == self.auth_port else 'accounting'
        )

        try:
            pkt = _Type(packet=data, **self.radius_packet_args)
        except PacketError as err:
            self.log('Dropped Data', error=str(err))
            return

        if isinstance(pkt, AuthPacket):
            self.handle_auth_response(pkt)
        else:
            self.handle_accounting_response(pkt)

    def handle_auth_response(self, pkt):
        self.log('Auth Response')
        if pkt.code == AccessAccept:
            self.log('Access Accept')
            self.start_time = time.time()
            self.accounting_start()

        elif pkt.code == AccessReject:
            self.log(
                'Access Rejected',
                rejected_access_count=self.rejected_access_count,
                reject_code=pkt   #[18][0].partition('=')[-1]   # Weird, pkt exmaple: {18: ['E=908']}
            )

            self.rejected_access_count += 1
            d = defer.Deferred()
            reactor.callLater(random.choice([120, 190]), self.authenticate, d)
            return d

    def handle_accounting_response(self, pkt):
        self.log('Handling Response', last_state=self.last_state)

        if self.last_state == 'accounting_start':
            self.last_state = 'accounting_update'

        if self.last_state == 'accounting_update':
            d = defer.Deferred()
            self.last_interim_update = time.time()
            reactor.callLater(UPDATE_INTERVAL+1, self.update_accounting, d)
            return d

    def connectionRefused(self):
        self.log('Connection Refused')

    def handleFailure(self, f):
        self.log('Exception', trace=f.getTraceback())
        f.trap(RuntimeError)

    def accounting_start(self, d=None):
        self.last_state = 'accounting_start'
        accounting_packet = AcctPacket(**self.radius_packet_args)

        self.gen_radius_packet(accounting_packet, 'Start')

        self.log('Starting Accounting')

        self.accounting_start_time = time.time()
        self.accounting_start_pkt_data = accounting_packet.RequestPacket()
        return self._send_data(self.accounting_port, self.accounting_start_pkt_data)

    def update_accounting(self, d=None):
        self.log('Updating Account')
        self.last_state = 'accounting_update'
        if d is None:
            d = defer.Deferred()

        session_time = time.time() - self.accounting_start_time
        if session_time >= self.session_time_limit:
            reactor.callLater(1, self.stop_accounting, d)
            return d

        if self.last_interim_update and time.time() - self.last_interim_update > UPDATE_INTERVAL:
            self.log(
                'Sending Updates',
                last_interim_update=self.last_interim_update,
                update_interval=UPDATE_INTERVAL
            )

            accounting_packet = AcctPacket(**self.radius_packet_args)

            self.gen_radius_packet(accounting_packet, 'Alive')

            self.accounting_update_pkt_data = accounting_packet.RequestPacket()
            return self._send_data(self.accounting_port, self.accounting_update_pkt_data)

        else:
            self.log('Too Soon For Update')
            self.last_interim_update = time.time()
            reactor.callLater(UPDATE_INTERVAL+1, self.update_accounting, d)

        return d

    def stop_accounting(self, d=None):
        self.last_state = 'accounting_stop'
        accounting_packet = AcctPacket(**self.radius_packet_args)

        self.gen_radius_packet(accounting_packet, 'Stop')
        accounting_packet['Acct-Terminate-Cause'] = 'User-Request'

        self.transport.write(accounting_packet.RequestPacket(),
                             (self.server_ip, self.accounting_port))
        d = defer.Deferred()
        reactor.callLater(random.randint(1, 60), self.authenticate, d)
        return d

    def gen_radius_packet(self, packet, accounting_status=None):
        if isinstance(packet, AuthPacket):
            self.nas_port = gen_nas_port()
            self.accounting_session_id = str(random.random())[2:]
            packet['User-Password'] = packet.PwCrypt(self.password)

        if isinstance(packet, AcctPacket):
            if accounting_status in ['Alive', 'Stop']:
                self.gen_accounting()
                packet['Acct-Session-Time'] = long(time.time() - self.accounting_start_time)

            packet['Acct-Status-Type'] = accounting_status
            packet['Framed-IP-Address'] = self.client_ip
            packet['Acct-Input-Octets'] = self.accounting_input_octets
            packet['Acct-Output-Octets'] = self.accounting_output_octets
            packet['Acct-Input-Packets'] = self.accounting_input_pkts
            packet['Acct-Output-Packets'] = self.accounting_output_pkts

        packet['NAS-Identifier'] = 'Dummy-NAS'
        packet['NAS-Port-Type'] = 'Ethernet'
        packet['NAS-IP-Address'] = self.nas_ip
        packet['Calling-Station-Id'] = self.mac
        packet['NAS-Port'] = self.nas_port
        packet['Acct-Session-Id'] = self.accounting_session_id

        return packet

    def gen_accounting(self):
        self.accounting_input_octets += random.randrange(2**3, 2**8)
        self.accounting_output_octets += random.randrange(2**8, 2**10)
        self.accounting_input_pkts += random.randrange(104, 1024)
        self.accounting_output_pkts += random.randrange(1083, 9984)

    def log(self, event_type, **args):
        args.update(event_type=event_type)
        self.db.hmset('LOG_{}_{}'.format(self.username, time.time()), args)
        if self.username == 'atest_00001':
            pprint(args)
        # if event_type == 'Access Rejected':
        #     pprint(args)


def main(users):
    log_db = redis.StrictRedis(host='localhost', port=6379, db=0)
    log_db.flushdb()

    stat_db = redis.StrictRedis(host='localhost', port=6379, db=1)
    stat_db.flushdb()

    with open(USERS_DATA_FILE) as users_data:
        for i in range(int(users)):
            username, password, ip = users_data.readline().strip().split(',')
            mac = gen_mac_address()
            session = Session(log_db, username, password, mac=mac, client_ip=ip)

            reactor.listenUDP(0, session)

    log_db.set('start_time', time.time())

    # reactor.callLater(TOTAL_RUNTIME, reactor.stop)
    st = task.LoopingCall(Stats)
    st.start(1)

    reactor.run()

if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except IndexError:
        main(USERS)
