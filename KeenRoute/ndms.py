class SSHClient(object):

    def __init__(self, host, port, user, passwd, env):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.env = env