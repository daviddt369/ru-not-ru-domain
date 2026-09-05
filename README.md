# ru-not-ru-domain

RU routing data for HE -> RU split routing.

Схема:

- российские домены и российские IP/CIDR -> outbound `RU`
- принудительные override-домены из `extra-direct-ru.txt` -> outbound `RU`
- всё остальное -> остаётся на `HE`

## Основной rule-set для sing-box

Подключай один файл:

```text
https://raw.githubusercontent.com/daviddt369/ru-not-ru-domain/main/rule-set/ru-all.json
```

Формат - sing-box source rule-set.

Пример на HE-ноде:

```json
{
  "route": {
    "rules": [
      {
        "rule_set": "ru-all",
        "action": "route",
        "outbound": "RU"
      }
    ],
    "rule_set": [
      {
        "type": "remote",
        "tag": "ru-all",
        "format": "source",
        "url": "https://raw.githubusercontent.com/daviddt369/ru-not-ru-domain/main/rule-set/ru-all.json",
        "update_interval": "24h"
      }
    ],
    "final": "HE"
  }
}
```

`RU` и `HE` - это теги outbound в конкретном конфиге. Если у тебя они называются иначе, меняются только эти значения.

RU-правило должно находиться выше общего HE/default правила.

## Что входит

Данные автоматически собираются из:

```text
https://redirect.alpaca-community.com/geo/geosite.dat
https://redirect.alpaca-community.com/geo/geoip.dat
```

Из `geosite.dat` берутся все теги `*-RU`, включая `CATEGORY-RU`, `TLD-RU`, банки, государственные ресурсы, СМИ, e-commerce и другие российские категории.

Из `geoip.dat` берётся страна `RU` целиком - IPv4 и IPv6 CIDR.

Дополнительно `extra-direct-ru.txt` содержит домены, которые нужно принудительно отправлять через RU, даже если их инфраструктура/IP находится за пределами РФ.

Сейчас туда входят MAX/VK/Mail/OK и IP-check endpoints, включая:

```text
max.ru
oneme.ru
okcdn.ru
mycdn.me
vkuser.net
vk-cdn.net
cdn-max.ru
apptracer.ru
vk-analytics.ru
tracker.my.com
ok.ru
odnoklassniki.ru
mail.ru
tamtam.chat
trace-flow.ru
api.ipify.org
ifconfig.me
checkip.amazonaws.com
ipv4-internet.yandex.net
ipv6-internet.yandex.net
```

## Отдельные файлы

```text
rule-set/ru-all.json
rule-set/ru-geosite.json
rule-set/ru-geoip.json
rules/ru-domain-suffix.txt
rules/ru-domain-exact.txt
rules/ru-domain-keyword.txt
rules/ru-domain-regex.txt
rules/ru-ipv4.txt
rules/ru-ipv6.txt
rules/ru-tags.txt
```

`ru-all.json` - основной вариант. В нём одновременно доменные правила и RU CIDR.

## Автообновление

GitHub Actions ежедневно скачивает свежие Alpaca `geosite.dat` и `geoip.dat`, пересобирает rule-set и коммитит изменения только если данные реально изменились.

Скрипт сборки:

```text
scripts/build_ru_routes.py
```

Старые `domains.txt` и `roscomvpn-*` оставлены как legacy и в основной HE -> RU схеме не нужны.
