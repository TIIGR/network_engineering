import urllib.request
import ipaddress

STRICT_MODE = False 

ADDITIONAL_BOGONS = [
    ipaddress.ip_network('100.64.0.0/10'),  # CGNAT (включает 100.82.0.0/16 и др.)
    ipaddress.ip_network('192.0.0.0/24'),   # IETF Protocol Assignments
    ipaddress.ip_network('198.18.0.0/15'),  # Benchmark Testing
    ipaddress.ip_network('192.88.99.0/24')  # 6to4 Relay Anycast
]

def filter_private_networks(networks):
    filtered = []
    excluded_count = 0
    
    for net in networks:
        if (net.is_private or net.is_loopback or 
            net.is_link_local or net.is_multicast or net.is_reserved):
            excluded_count += 1
            continue
            
        is_bogon = False
        for bogon in ADDITIONAL_BOGONS:
            if net.overlaps(bogon):
                is_bogon = True
                break
                
        if is_bogon:
            excluded_count += 1
        else:
            filtered.append(net)
            
    if excluded_count > 0:
        print(f"[*] Исключено {excluded_count} частных/зарезервированных подсетей перед агрегацией.")
    return filtered

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

    networks = filter_private_networks(networks)

    #print("[*] Выполняется агрегация без добавления лишних узлов...")
    aggregated = list(ipaddress.collapse_addresses(networks))
    print(f"[*] Всего загружено подсетей до агрегации: {len(networks)}, после: {len(aggregated)}")
    return aggregated


def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]