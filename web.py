from pprint import pformat
import json

import redis
from jinja2 import Environment, PackageLoader
from twisted.web import static
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor

import config
from log import Stats


stat_db = redis.StrictRedis(host='localhost', port=6379, db=1)


class Index(Resource):
    isLeaf = True

    def __init__(self, env):
        self.env = env

    def render_GET(self, request):
        template = self.env.get_template('index.html')
        return bytes(template.render(config=config.__dict__))


class Json(Resource):
    isLeaf = True

    def render_GET(self, request):
        data = generate_json(float(request.args['time'][0]))
        return '<html><body><pre>%s</pre></body></html>' % (json.dumps(data),)

    def render_POST(self, request):
        # print request.__dict__
        data = generate_json(float(request.args['time'][0]))
        request.setHeader('content-type', 'application/json')
        return json.dumps(data)


def generate_json(last_time):
        defaults = {
            'auth:delay_count': 0,
            'auth:delay_sum': 0,
            'auth:delay_max': 0,
            'auth:delay_min': 999,
            'auth:timeout_count': 0,
            'auth:delay_period:<100': 0,
            'auth:delay_period:100-500': 0,
            'auth:delay_period:500-2000': 0,
            'auth:delay_period:>2000': 0,
            'accounting:delay_count': 0,
            'accounting:delay_sum': 0,
            'accounting:delay_max': 0,
            'accounting:delay_min': 999,
            'accounting:timeout_count': 0,
            'accounting:delay_period:<100': 0,
            'accounting:delay_period:100-500': 0,
            'accounting:delay_period:500-2000': 0,
            'accounting:delay_period:>2000': 0,
            'reject:count': 0,
            'reject:908': 0,
            'reject:909': 0,
            'request_count': 0,
            'start_time': 0
        }

        key_times = sorted(stat_db.keys())
        for key_time in key_times:
            if last_time < key_time:
                item = stat_db.hgetall(key_time)
                for key, value in defaults.items():
                    if 'max' in key:
                        defaults[key] = max(float(item[key]), defaults[key])
                    elif 'min' in key:
                        defaults[key] = min(float(item[key]), defaults[key])
                    elif key == 'start_time':
                        defaults[key] = float(item.get(key, 0))
                    else:
                        defaults[key] += float(item.get(key, 0))
                defaults['time'] = float(key_time)
        return defaults


def gen_site():
    env = Environment(loader=PackageLoader('web', 'html'))
    web = Resource()
    web.putChild('', Index(env))
    web.putChild('json', Json())
    web.putChild('static', static.File('./html'))
    return Site(web)


def main():
    stat_db = redis.StrictRedis(host='localhost', port=6379, db=1)
    # stat_db.flushdb()

    reactor.listenTCP(8888, gen_site())
    reactor.run()

if __name__ == '__main__':
    main()
