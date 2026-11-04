import sys; sys.path.append('.'); import KeenRoute.ndms as Keenetic
from KeenRoute.uploader import update
from getpass import getpass


if __name__ == "__main__":

    pswd = str(getpass("Введите пароль от SSH: "))

    update(Keenetic.SSHClient("192.168.11.1", 22, "root", pswd, "Entware"))
    update(Keenetic.SSHClient("192.168.12.1", 22, "admin", pswd, "NDMS"))
    update(Keenetic.SSHClient("192.168.13.1", 22, "root", pswd, "Entware"))
