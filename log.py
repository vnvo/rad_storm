from collections import defaultdict
import json
import time

from flatdict import FlatDict
import redis


class Stats:
    def __init__(self):
        self.log_db = redis.StrictRedis(host='localhost', port=6379, db=0)
        self.stat_db = redis.StrictRedis(host='localhost', port=6379, db=1)
        self.logs = self.log_db.keys('LOG_*')

        self.stats = defaultdict(int)
        self.stats['reject'] = defaultdict(int)
        self.stats['auth'] = defaultdict(int)
        self.stats['auth']['delay_max'] = 0.0
        self.stats['auth']['delay_min'] = 999.0
        self.stats['auth']['delay_period'] = defaultdict(int)
        self.stats['accounting'] = defaultdict(int)
        self.stats['accounting']['delay_max'] = 0.0
        self.stats['accounting']['delay_min'] = 999.0
        self.stats['accounting']['delay_period'] = defaultdict(int)

        self.parse_logs()

    def parse_logs(self):
        for log_hash in self.logs:
            log = self.log_db.hgetall(log_hash)
            if log['event_type'] == 'Received Data' and log['data_type'] in ['auth', 'accounting']:
                self.process_received_data(log)

            elif log['event_type'] == 'Access Rejected':
                self.stats['reject']['count'] += 1
                self.stats['reject'][log['reject_code']] += 1

            elif log['event_type'] == 'Time Out, Resending Data':
                self.process_timeout(log)

            elif log['event_type'] == 'Sending Data':
                self.stats['request_count'] += 1

        self.stats['start_time'] = float(self.log_db.get('start_time'))
        self.sync_db()
        if self.logs:
            self.log_db.delete(*self.logs)

    def process_received_data(self, log):
        data_type = log['data_type']
        delay = float(log['delay'])

        self.stats[data_type]['delay_count'] += 1
        self.stats[data_type]['delay_sum'] += delay
        self.stats[data_type]['delay_max'] = max(self.stats[data_type]['delay_max'], delay)
        self.stats[data_type]['delay_min'] = min(self.stats[data_type]['delay_min'], delay)

        if delay < 0.1:
            self.stats[data_type]['delay_period']['<100'] += 1
        elif delay < 0.5:
            self.stats[data_type]['delay_period']['100-500'] += 1
        elif delay < 2:
            self.stats[data_type]['delay_period']['500-2000'] += 1
        elif delay > 2:
            self.stats[data_type]['delay_period']['>2000'] += 1

    def process_timeout(self, log):
        if log['last_state'] == 'auth':
            data_type = 'auth'
        elif log['last_state'] == 'accounting_start':
            data_type = 'accounting'

        self.stats[data_type]['timeout_count'] += 1

    def sync_db(self):
        flat = FlatDict(self.stats)
        self.stat_db.hmset(time.time(), flat)
