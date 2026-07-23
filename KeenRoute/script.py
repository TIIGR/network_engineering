import sys
sys.path.append('.')
from getpass import getpass
from KeenClient import SSHClient
import urllib.request
import ipaddress
import paramiko
import time

PRIMARY_SOURCE_URLS = [
    "https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/refs/heads/main/all/all_plain_ipv4.txt",
    "https://core.telegram.org/resources/cidr.txt",
    "https://iplist.opencck.org/?format=text&data=cidr4"
]
SECONDARY_SOURCE_URLS = [
    "https://iplist.opencck.org/?format=text&data=cidr4",
    "https://core.telegram.org/resources/cidr.txt"
]

ENTWARE_REMOTE_FILE_PATH = "/opt/etc/HydraRoute/ip.list"
BASE_GROUP_NAME = "HydraCIDR"
KEENETIC_OS_LIMIT = 300

STRICT_MODE = False 


def fetch_and_aggregate(urls):
    networks = []
    for url in urls:
        print(f"[*] Загрузка списков из: {url}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    net = ipaddress.ip_network(line, strict=STRICT_MODE)
                    if net.version == 4:
                        networks.append(net)
                except ValueError:
                    print(f" [!] Пропущен некорректный CIDR: {line}")
        except Exception as e:
            exit(f" [!] Ошибка при загрузке {url}: {e}")

    print(f"\n[*] Всего загружено подсетей до агрегации: {len(networks)}")
    print("[*] Выполняется агрегация без добавления лишних узлов...")
    
    aggregated = list(ipaddress.collapse_addresses(networks))
    print(f"[*] После агрегации осталось подсетей: {len(aggregated)}")
    return aggregated


def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def upload_to_entware(host, port, user, password, remote_path, networks):
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"\n[*] Подключение к роутеру {host}:{port} по SSH...")
    try:
        ssh.connect(
            host, 
            port=port, 
            username=user, 
            password=password, 
            timeout=15,
            look_for_keys=False, 
            allow_agent=False
        )
        
        print(f"[*] Запись данных в файл {remote_path} (режим stdin)...")
        stdin, stdout, stderr = ssh.exec_command(f"cat > {remote_path}")
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
        command = "export PATH=/opt/bin:/opt/sbin:$PATH; /opt/etc/init.d/S99hrneo restart"
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status() 
        output = stdout.read().decode().strip()
        errors = stderr.read().decode().strip()
        if exit_status == 0:
            print("[+] Служба успешно перезапущена!")
            if output:
                print(f"Вывод роутера:\n{output}")
        else:
            print(f"[!] Ошибка при перезапуске (код {exit_status}):\n{errors}")
            
    except Exception as e:
        print(f" [!] Ошибка при работе с SSH: {e}")
    finally:
        ssh.close()
        print("[*] SSH соединение закрыто.")


def upload_to_keenos(host, port, user, password, networks, base_group_name):
    print(f"\n[*] Подключение к KeeneticOS (SSH) {host}:{port}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, port=port, username=user, password=password, timeout=15,
                    look_for_keys=False, allow_agent=False)
        
        channel = ssh.invoke_shell()
        time.sleep(1)
        
        if channel.recv_ready():
            channel.recv(9999)
            
        # channel.send("system cli no-page\n")
        # time.sleep(0.2)
        
        chunks = list(chunk_list(networks, KEENETIC_OS_LIMIT))
        print(f"[*] Список разделен на {len(chunks)} групп(ы) для KeeneticOS.")

        print("[*] Очистка старых групп...")
        for i in range(1, len(chunks) + 5):
            channel.send(f"dns-proxy no route object-group {base_group_name}_{i} Wireguard0\n")
            time.sleep(0.1)
            channel.send(f"dns-proxy no route object-group {base_group_name}_{i} Wireguard2\n")
            time.sleep(0.1)
            channel.send(f"no object-group fqdn {base_group_name}_{i}\n")
            time.sleep(0.1)

        for idx, chunk in enumerate(chunks, start=1):
            group_name = f"{base_group_name}_{idx}"
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


if __name__ == "__main__":

    pswd = str(getpass("Введите пароль от SSH: "))
    pswd1 = str(getpass("Введите пароль от Andrey SSH: "))
    Ent1 = SSHClient("192.168.1.1", 222, "root", pswd)
    Ent2 = SSHClient("192.168.10.1", 222, "root", pswd1)
    Ndmc1 = SSHClient("192.168.2.1", 32, "admin", pswd)
    aggregated_list1 = fetch_and_aggregate(PRIMARY_SOURCE_URLS)
    if aggregated_list1 and Ent1:
        upload_to_entware(
            host=Ent1.host,
            port=Ent1.port,
            user=Ent1.user,
            password=Ent1.passwd,
            remote_path=ENTWARE_REMOTE_FILE_PATH,
            networks=aggregated_list1
        )
        upload_to_entware(
            host=Ent2.host,
            port=Ent2.port,
            user=Ent2.user,
            password=Ent2.passwd,
            remote_path=ENTWARE_REMOTE_FILE_PATH,
            networks=aggregated_list1
        )
    else:
        print(" [!] Список подсетей пуст. Загрузка на роутер отменена.")

    aggregated_list2 = fetch_and_aggregate(SECONDARY_SOURCE_URLS)
    if aggregated_list2 and Ndmc1:
        upload_to_keenos(
            host=Ndmc1.host,
            port=Ndmc1.port,
            user=Ndmc1.user,
            password=Ndmc1.passwd,
            networks=aggregated_list2,
            base_group_name=BASE_GROUP_NAME
        )
    else:
        print(" [!] Список подсетей пуст. Загрузка на роутер отменена.")