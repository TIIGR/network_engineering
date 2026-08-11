from aggregator import fetch_and_aggregate, chunk_list
import configparser
import time, os
import paramiko

def load_source_file(filepath):
    items = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    items.append(line)
    else:
        print(f" [!] Ресурсный файл {filepath} не найден. Убедитесь, что он создан.")
    return items

config = configparser.ConfigParser()
config.read('settings.conf', encoding='utf-8')
KEENETIC_OS_LIMIT = config.getint('SETTINGS', 'KEENETIC_OS_LIMIT', fallback=300)
ENTWARE_REMOTE_FILE_PATH = config.get('SETTINGS', 'ENTWARE_REMOTE_FILE_PATH', fallback='/opt/etc/HydraRoute/ip.list')

ENTWARE_SOURCE_URLS = load_source_file('KeenRoute/sources/entware_urls.source')
NDMS_SOURCE_URLS = load_source_file('KeenRoute/sources/ndms_urls.source')
ADDITIONAL_CIDR_LIST = load_source_file('KeenRoute/sources/custom_cidrs.lst')

def update(cli):
    if cli.env == "Entware":
        cidr_list = fetch_and_aggregate(ENTWARE_SOURCE_URLS, custom_cidrs=ADDITIONAL_CIDR_LIST)
        if cidr_list:
            upload2entware(cli, cidr_list)
        else:
            print(" [!] Список подсетей пуст. Загрузка на роутер отменена.")
    elif cli.env == "NDMS":
        cidr_list = fetch_and_aggregate(NDMS_SOURCE_URLS, custom_cidrs=ADDITIONAL_CIDR_LIST)
        if cidr_list:
            upload2keenos(cli, cidr_list)
        else:
            print(" [!] Список подсетей пуст. Загрузка на роутер отменена.")
    else:
        print(f" [!] Задан некорректный тип окружения для хоста {cli.host}")


def upload2entware(cli, networks):
    host = cli.host
    port = cli.port
    user = cli.user
    passwd = cli.passwd
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"\n[*] Подключение к Entware {host}:{port} по SSH...")
    try:
        ssh.connect(host, port=port, username=user, password=passwd, timeout=15,
                    look_for_keys=False, allow_agent=False)
        
        print(f"[*] Запись данных в файл {ENTWARE_REMOTE_FILE_PATH} (режим stdin)...")
        stdin, stdout, stderr = ssh.exec_command(f"sudo cat > {ENTWARE_REMOTE_FILE_PATH}")
        stdin.write("##CIDR\n")
        stdin.write("/FirstVDS\n")
        for net in networks:
            stdin.write(f"{net}\n")
        stdin.close()
        
        error_msg = stderr.read().decode().strip()
        if error_msg:
            print(f" [!] Ошибка на стороне роутера: {error_msg}")
        else:
            print(f"[+] Файл успешно обновлен на роутере!")

        print("[*] Перезапуск службы Hydra Route Neo...")
        command = "sudo export PATH=/opt/bin:/opt/sbin:$PATH; sudo /opt/etc/init.d/S99hrneo restart"
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status() 
        output = stdout.read().decode().strip()
        errors = stderr.read().decode().strip()
        if exit_status == 0:
            if output:
                print(f"{output}")
        else:
            print(f"[!] Ошибка при перезапуске (код {exit_status}):\n{errors}")
            
    except Exception as e:
        print(f" [!] Ошибка при работе с SSH: {e}")
    finally:
        ssh.close()
        print("[*] SSH соединение закрыто.")


def upload2keenos(cli, networks):
    BASE_GROUP_NAME = "HydraCIDR"

    host = cli.host
    port = cli.port
    user = cli.user
    passwd = cli.passwd
        
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"\n[*] Подключение к KeeneticOS {host}:{port} по SSH...")

    try:
        ssh.connect(host, port=port, username=user, password=passwd, timeout=15,
                    look_for_keys=False, allow_agent=False)
        
        channel = ssh.invoke_shell()
        time.sleep(1)
        
        if channel.recv_ready():
            channel.recv(9999)
            
        chunks = list(chunk_list(networks, KEENETIC_OS_LIMIT))
        print(f"[*] Список разделен на {len(chunks)} групп(ы) для KeeneticOS.")

        print("[*] Очистка старых групп...")
        for i in range(1, len(chunks) + 5):
            channel.send(f"dns-proxy no route object-group {BASE_GROUP_NAME}_{i} Wireguard0\n")
            time.sleep(0.1)
            channel.send(f"dns-proxy no route object-group {BASE_GROUP_NAME}_{i} Wireguard2\n")
            time.sleep(0.1)
            channel.send(f"no object-group fqdn {BASE_GROUP_NAME}_{i}\n")
            time.sleep(0.1)

        for idx, chunk in enumerate(chunks, start=1):
            group_name = f"{BASE_GROUP_NAME}_{idx}"
            print(f"[*] Заполнение fqdn-группы {group_name} и его последующая запись в flash память ({len(chunk)} строк) ...")
            
            channel.send(f"object-group fqdn {group_name}\n")
            time.sleep(0.1)
            channel.send(f"description {group_name}\n")
            time.sleep(0.1)
            
            for net in chunk:
                channel.send(f"include {net}\n")
                time.sleep(0.01)
                
            channel.send("exit\n")
            time.sleep(0.1)
            channel.send(f"dns-proxy route object-group {group_name} Wireguard0 auto\n")
            time.sleep(0.1)
            channel.send(f"dns-proxy route object-group {group_name} Wireguard2 auto\n")
            time.sleep(0.1)

        print("[*] Сохранение конфигурации в память роутера...")
        channel.send("system configuration save\n")
        time.sleep(0.5)
        
        channel.send("exit\n")
        print("[+] Все группы fqdn успешно обновлены через SSH!")

    except Exception as e:
        print(f" [!] Ошибка при работе с Keenetic по SSH: {e}")
    finally:
        ssh.close()