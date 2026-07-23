import sys
sys.path.append('.')
import ipaddress
import geoip2.database
import geoip2.errors
import time
from KeenRoute.script import fetch_and_aggregate

DB_PATH = "GeoRouting\GeoLite2-Country.mmdb"
OUTPUT_FILE = "GeoRouting\\routing_rules.txt"
PRIMARY_SOURCE_URLS = [
    "https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/refs/heads/main/all/all_plain_ipv4.txt",
    # "https://antifilter.network/download/ipsum.lst"
    "https://iplist.opencck.org/?format=text&data=cidr4"
]
SECONDARY_SOURCE_URLS = [
    "https://iplist.opencck.org/?format=text&data=cidr4"
]

INPUT_FILE = fetch_and_aggregate(PRIMARY_SOURCE_URLS)

ALMATY_ZONE_COUNTRIES = {'KZ', 'UZ', 'KG', 'TJ', 'TM', 'BY', 'AM', 'AZ', 'GE'}

def main():
    amsterdam_cidrs = []
    almaty_cidrs = []

    print(f"Запуск локальной гео-проверки для {len(INPUT_FILE)} сетей...")
    start_time = time.time()
    errors = 0

    try:
        with geoip2.database.Reader(DB_PATH) as reader:
            for cidr in INPUT_FILE:
                try:
                    network = ipaddress.ip_network(cidr, strict=False)
                    if network.is_private:
                        continue

                    base_ip = str(network.network_address)
                    
                    try:
                        response = reader.country(base_ip)
                        country = response.country.iso_code
                    except geoip2.errors.AddressNotFoundError:
                        country = None

                    if country in ALMATY_ZONE_COUNTRIES:
                        almaty_cidrs.append(str(network))
                    else:
                        amsterdam_cidrs.append(str(network))

                except ValueError:
                    errors += 1
                    
    except FileNotFoundError:
        print(f"Ошибка: База данных {DB_PATH} не найдена.")
        return

    with open(OUTPUT_FILE, "w") as f:
        f.write("##AMS\n")
        if amsterdam_cidrs:
            f.write("\n".join(amsterdam_cidrs) + "\n")
            
        f.write("##ALM\n")
        if almaty_cidrs:
            f.write("\n".join(almaty_cidrs) + "\n")

    elapsed = round(time.time() - start_time, 2)
    
    print("\nРаспределение завершено!")
    print(f"Время выполнения: {elapsed} сек.")
    print(f"Результат сохранен в файл: {OUTPUT_FILE}")
    print(f"  - Амстердам: {len(amsterdam_cidrs)} сетей")
    print(f"  - Алматы: {len(almaty_cidrs)} сетей")
    if errors > 0:
        print(f"  - Ошибок парсинга (неверный формат CIDR): {errors}")

if __name__ == "__main__":
    main()