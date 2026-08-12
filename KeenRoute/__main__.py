import sys; sys.path.append('.'); import KeenRoute.ndms as Keenetic
from KeenRoute.uploader import update
from getpass import getpass


if __name__ == "__main__":

    pswd = str(getpass("Введите пароль от SSH: "))

    update(Keenetic.SSHClient("192.168.1.1", 222, "root", pswd, "Entware"))
    update(Keenetic.SSHClient("192.168.10.1", 222, "root", pswd, "Entware"))
    update(Keenetic.SSHClient("192.168.2.1", 22, "admin", pswd, "NDMS"))
