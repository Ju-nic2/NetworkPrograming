import random, time, zmq,argparse,struct
import matplotlib.pyplot as plt
B = 32  # number of bits of precision in each random integer
float_struct = struct.Struct('f') # for float data transmission
waitingtime = 15000 # milisecond  # all nodes wait for recv message in 15 seconds
""" except client ALL NODES are set time out 15secs"""

def client(zcontext,out_url,in_url):
    """plt. == Draw Graph code"""
    """out_url's purpose is to tell to bitsource Make Points"""
    """in_url's purpose is to recieve data from tally"""
    plt.figure()
    plt.savefig('map.png')
    plt.xlabel('iterations')
    plt.ylabel('pi')
    plt.title('Estimating Pi \n (Using Monte Carlo Method)', fontsize=15)
    plt.axhline(y=3.141592, color='#e337c2', linewidth=1)
    osock = zcontext.socket(zmq.PUSH) #output sock
    osock.bind(out_url)
    isock = zcontext.socket(zmq.PULL) #input sock
    isock.bind(in_url)
    n = input('give num As much as you want to make point :')
    isAppropriateInput(n)
    for i in range(int(n)): # repeat N times
        osock.send_string("1") # tell to bitsource  make points
    for i in range(int(n)): # receive N results
        block_data = isock.recv() # get packed data
        (data,) = float_struct.unpack(block_data)
        plt.scatter(i, data, color='r', edgecolors='none', s=3)
    plt.show()

class NagativeIntExeption(Exception): # N > 0 integer
    def __init__(self):
        pass
    def __str__(self):
        return "Number must be Positive Integer"

def isAppropriateInput(N): ## for Test input
    try:
        int(N)
        if int(N) < 0: # if N is negative num
            raise NagativeIntExeption()
    except ValueError: ## if N is str
        return False
    else:
        return True


def ones_and_zeros(digits):
    """Express `n` in at least `d` binary digits, with no special prefix."""
    return bin(random.getrandbits(digits)).lstrip('0b').zfill(digits)


def bitsource(zcontext, url, in_url):
    """Produce random points in the unit square."""
    """Bitsource make points when it get Message "1" """
    zsock = zcontext.socket(zmq.PUB)
    zsock.bind(url)
    isock = zcontext.socket(zmq.PULL) # get msg form client
    isock.connect(in_url)
    isock.RCVTIMEO = waitingtime #set time out
    while True:
        try:
            msg = isock.recv_string()
            if msg == "1":
                zsock.send_string(ones_and_zeros(B * 2))
                time.sleep(0.01)
        except zmq.Again as exc:
            raise TimeoutError("time out") from exc


def always_yes(zcontext, in_url, out_url):
    """Coordinates in the lower-left quadrant are inside the unit circle."""
    isock = zcontext.socket(zmq.SUB)
    isock.connect(in_url)
    isock.setsockopt(zmq.SUBSCRIBE, b'00')
    osock = zcontext.socket(zmq.PUSH)
    osock.connect(out_url)
    isock.RCVTIMEO = waitingtime #set time out
    while True:
        try:
            isock.recv_string()
            osock.send_string('Y')
        except zmq.Again as exc:
            raise TimeoutError("time out") from exc




def judge(zcontext, in_url, pythagoras_url, out_url):
    """Determine whether each input coordinate is inside the unit circle."""
    isock = zcontext.socket(zmq.SUB)
    isock.connect(in_url)
    for prefix in b'01', b'10', b'11':
        isock.setsockopt(zmq.SUBSCRIBE, prefix)
    psock = zcontext.socket(zmq.REQ)
    psock.connect(pythagoras_url)
    osock = zcontext.socket(zmq.PUSH)
    osock.connect(out_url)
    unit = 2 ** (B * 2)
    isock.RCVTIMEO = waitingtime #set time out
    while True:
        try:
            bits = isock.recv_string()
            n, m = int(bits[::2], 2), int(bits[1::2], 2)
            psock.send_json((n, m))
            sumsquares = psock.recv_json()
            osock.send_string('Y' if sumsquares < unit else 'N')
        except zmq.Again as exc:
            raise TimeoutError("time out") from exc


def pythagoras(zcontext, url):
    """Return the sum-of-squares of number sequences."""
    zsock = zcontext.socket(zmq.REP)
    zsock.bind(url)
    zsock.RCVTIMEO = waitingtime #set time out
    while True:
        try:
            numbers = zsock.recv_json()
            zsock.send_json(sum(n * n for n in numbers))
        except zmq.Again as exc:
            raise TimeoutError("time out") from exc



def tally(zcontext, url, out_url):
    """Tally how many points fall within the unit circle, and print pi."""
    zsock = zcontext.socket(zmq.PULL)
    zsock.bind(url)
    osock = zcontext.socket(zmq.PUSH)
    osock.connect(out_url)
    p = q = 0
    zsock.RCVTIMEO = waitingtime #set time out
    while True:
        try:
            decision = zsock.recv_string()
            q += 1
            if decision == 'Y':
                p += 4
            output = float_struct.pack(p/q) # pack float data
            osock.send(output)
        except zmq.Again as exc:
            raise TimeoutError("time out") from exc



if __name__ == '__main__':
    choices = {'client': client, 'bitsource': bitsource, 'always_yes': always_yes,
               'judge': judge, 'pythagoras': pythagoras, 'tally': tally}
    parser = argparse.ArgumentParser(description='message Queue Test')
    parser.add_argument('role', choices=choices)
    parser.add_argument('-co', help='Client output URL', default='tcp://127.0.0.1:1060')
    parser.add_argument('-ci', help='Client input URL', default='tcp://127.0.0.1:1061')
    parser.add_argument('-ps', help='Publisher or Subscriber URL', default='tcp://127.0.0.1:6700')
    parser.add_argument('-rr', help='Request or Reply URL', default='tcp://127.0.0.1:6701')
    parser.add_argument('-pp', help='Push or PULL URL', default='tcp://127.0.0.1:6702')
    args = parser.parse_args()
    function = choices[args.role]
    if id(function) == id(client):
        function(zmq.Context(), args.co, args.ci)
    elif id(function) == id(bitsource):
        function(zmq.Context(), args.ps, args.co)
    elif id(function) == id(always_yes):
        function(zmq.Context(), args.ps, args.pp)
    elif id(function) == id(judge):
        function(zmq.Context(), args.ps, args.rr, args.pp)
    elif id(function) == id(pythagoras):
        function(zmq.Context(), args.rr)
    elif id(function) == id(tally):
        function(zmq.Context(), args.pp, args.ci)

