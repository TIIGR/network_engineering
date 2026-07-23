import sys
sys.path.append('.')
from getpass import getpass
import paramiko
import ipaddress
import json
import os

SSH_HOST = '192.168.1.1'
SSH_PORT = 222
SSH_USER = 'root'
SSH_PASSWORD = str(getpass("Введите пароль: "))
REMOTE_PATH = '/opt/etc/HydraRoute/ip.list'
OUTPUT_JSON = r'TorrentCIDRData\amneziawg.json'

OUTPUT_DAT = r'TorrentCIDRData\ipfilter4torrents.dat'

def process_remote_ip_list():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"Подключение к {SSH_HOST}...")
        ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, 
                    look_for_keys=False, allow_agent=False)

        print("Читаем файл с роутера...")
        stdin, stdout, stderr = ssh.exec_command(f'cat {REMOTE_PATH}')
        
        lines = stdout.readlines()
        
        error = stderr.read().decode()
        if error:
            print(f"Ошибка при чтении файла на роутере: {error}")
            return

        output_dir = os.path.dirname(OUTPUT_DAT)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(OUTPUT_DAT, 'w') as outfile:
            for line in lines:
                line = line.strip()
                if not line or line.startswith(('#', '/')):
                    continue
                
                try:
                    network = ipaddress.ip_network(line, strict=False)
                    outfile.write(f"{network.network_address} - {network.broadcast_address} , 000 ,\n")
                except ValueError:
                    continue
        
        print(f"Готово! Файл успешно обновлен: {OUTPUT_DAT}")
        ssh.close()

    except Exception as e:
        print(f"Произошла ошибка: {e}")


def fetch_and_convert():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Подключение к {SSH_HOST}...")
        ssh.connect(
            hostname=SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASSWORD,
        )

        print(f"Чтение файла {REMOTE_PATH}...")
        stdin, stdout, stderr = ssh.exec_command(f"cat {REMOTE_PATH}")

        lines = stdout.read().decode("utf-8").splitlines()

        cidr_list = []

        for line in lines:
            cleaned_line = line.strip()

            if (
                not cleaned_line
                or cleaned_line == "##CIDR"
                or cleaned_line == "/FirstVDS"
            ):
                continue

            cidr_list.append(cleaned_line)

        json_structure = [{"hostname": cidr, "ip": ""} for cidr in cidr_list]

        raw_json_str = json.dumps(json_structure, indent=4)
        escaped_json_str = raw_json_str.replace("/", "\\/")

        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            f.write(escaped_json_str)

        print(
            f"Успешно! Файл {OUTPUT_JSON} создан. Обработано подсетей: {len(cidr_list)}"
        )

    except Exception as e:
        print(f"Произошла ошибка: {e}")

    finally:
        ssh.close()

if __name__ == "__main__":
    process_remote_ip_list()
    fetch_and_convert()