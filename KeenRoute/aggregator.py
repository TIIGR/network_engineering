import urllib.request
import ipaddress

STRICT_MODE = False 

def parse_custom_cidrs(cidr_list):
    networks = []
    for line in cidr_list:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        try:
            net = ipaddress.ip_network(line, strict=STRICT_MODE)
            if net.version == 4:
                networks.append(net)
        except ValueError:
            #print(f" [!] Пропущен некорректный пользовательский CIDR: {line}")
            continue
    return networks

def fetch_and_aggregate(urls, custom_cidrs=None):
    networks = []
    
    if custom_cidrs:
        parsed_custom = parse_custom_cidrs(custom_cidrs)
        networks.extend(parsed_custom)
        print(f"\n\n\n[*] Добавлено пользовательских подсетей: {len(parsed_custom)}")

    for url in urls:
        #print(f"[*] Загрузка списков из: {url}")
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
                    #print(f" [!] Пропущен некорректный CIDR: {line}")
                    continue
        except Exception as e:
            exit(f" [!] Ошибка при загрузке {url}: {e}")

    #print("[*] Выполняется агрегация без добавления лишних узлов...")
    aggregated = list(ipaddress.collapse_addresses(networks))
    print(f"[*] Всего загружено подсетей до агрегации: {len(networks)}, после: {len(aggregated)}")
    return aggregated


def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]