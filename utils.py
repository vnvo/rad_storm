import random
import sys

from config import USERS, USERS_DATA_FILE

def gen_mac_address():
    '''
        Generate a random MAC Address
    '''
    mac = [ 0x00, 0x16, 0x1e,
        random.randint(0x00, 0x7f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]

    return ':'.join(map(lambda x: '%02x' % x, mac))


def gen_nas_port():
    return long(random.random()*10000000)


def gen_users(users):
    with open(USERS_DATA_FILE) as data, \
        open('userpass.csv', 'w') as userpass:
        for i in range(users):
            line = data.readline().rpartition(',')[0]
            userpass.write(line + '\n')


if __name__ == '__main__':
    try:
        gen_users(int(sys.argv[1]))
    except IndexError:
        gen_users(USERS)
