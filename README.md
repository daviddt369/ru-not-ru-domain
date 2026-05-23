# ru-not-ru-domain

Список российских сервисов, использующих домены **не в зоне .ru / .su / .рф**.

Нужен для маршрутизации — когда правила по TLD не покрывают CDN и инфраструктуру крупных российских сервисов.

## Использование

### xray / sing-box (suffix правила)

Каждый домен из `domains.txt` добавляется как `suffix:`:

```
suffix:yandex.net
suffix:vk.com
suffix:userapi.com
...
```

### Прямая ссылка для автозагрузки

```
https://raw.githubusercontent.com/daviddt369/ru-not-ru-domain/main/domains.txt
```

## Что включено

| Категория | Примеры |
|-----------|---------|
| Яндекс | yandex.net, yastatic.net, yandex.cloud |
| VK Group | vk.com, userapi.com, vkuservideo.net, boosty.to |
| Сбер | sberbank.com, cloud.ru, giga.chat |
| Ozon | ozonusercontent.com, ozon.tech |
| Wildberries | wbstatic.net |
| 2ГИС | 2gis.com |
| Банки | alfa-bank.com, moex.com, tochka.com |
| Стриминг | okko.tv, more.tv, premier.one, zvuk.com |
| Авиа | pobeda.aero, aviasales.com |
| IT/Хостинг | beget.com, timeweb.com, selcdn.net, habr.com |
| Антивирусы | kaspersky.com |

## Источники

- [hxehex/russia-mobile-internet-whitelist](https://github.com/hxehex/russia-mobile-internet-whitelist) — реальные перехваты мобильных сетей
- [Khfdd/geosite-russia-whitelist-minimal](https://github.com/Khfdd/geosite-russia-whitelist-minimal) — категоризированный список для xray/sing-box
- [chebur-net/russia-mobile-whitelist](https://github.com/chebur-net/russia-mobile-whitelist) — перехват реальных сетей Москва/СПб
