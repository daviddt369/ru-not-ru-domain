#!/usr/bin/env python3
import ipaddress
import json
import sys
import urllib.request
from pathlib import Path

GEOSITE_URL = "https://redirect.alpaca-community.com/geo/geosite.dat"
GEOIP_URL = "https://redirect.alpaca-community.com/geo/geoip.dat"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "rule-set"
RULES = ROOT / "rules"
EXTRA_FILE = ROOT / "extra-direct-ru.txt"
CACHE = ROOT / ".cache"


def read_varint(data, pos):
    value = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError("truncated varint")
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, pos
        shift += 7
        if shift > 70:
            raise ValueError("invalid varint")


def fields(data):
    pos = 0
    while pos < len(data):
        tag, pos = read_varint(data, pos)
        num, wire = tag >> 3, tag & 7
        if wire == 0:
            val, pos = read_varint(data, pos)
        elif wire == 1:
            val = data[pos:pos + 8]
            pos += 8
        elif wire == 2:
            ln, pos = read_varint(data, pos)
            val = data[pos:pos + ln]
            pos += ln
        elif wire == 5:
            val = data[pos:pos + 4]
            pos += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
        yield num, wire, val


def parse_domain(msg):
    typ, value = 0, ""
    for num, wire, val in fields(msg):
        if num == 1 and wire == 0:
            typ = val
        elif num == 2 and wire == 2:
            value = val.decode("utf-8", errors="strict").lower().rstrip(".")
    return typ, value


def parse_geosite(path):
    result = {}
    for num, wire, entry in fields(path.read_bytes()):
        if num != 1 or wire != 2:
            continue
        tag = ""
        domains = []
        for n2, w2, v2 in fields(entry):
            if n2 == 1 and w2 == 2:
                tag = v2.decode("utf-8", errors="strict").upper()
            elif n2 == 2 and w2 == 2:
                domains.append(parse_domain(v2))
        if tag:
            result.setdefault(tag, []).extend(domains)
    return result


def parse_cidr(msg):
    ipb, prefix = b"", None
    for num, wire, val in fields(msg):
        if num == 1 and wire == 2:
            ipb = val
        elif num == 2 and wire == 0:
            prefix = val
    if not ipb or prefix is None:
        return None
    addr = ipaddress.ip_address(ipb)
    return str(ipaddress.ip_network((addr, prefix), strict=False))


def parse_geoip_ru(path):
    networks = []
    for num, wire, entry in fields(path.read_bytes()):
        if num != 1 or wire != 2:
            continue
        tag = ""
        cidrs = []
        for n2, w2, v2 in fields(entry):
            if n2 == 1 and w2 == 2:
                tag = v2.decode("utf-8", errors="strict").upper()
            elif n2 == 2 and w2 == 2:
                cidr = parse_cidr(v2)
                if cidr:
                    cidrs.append(cidr)
        if tag == "RU":
            networks.extend(cidrs)
    return sorted(
        set(networks),
        key=lambda s: (
            ipaddress.ip_network(s).version,
            int(ipaddress.ip_network(s).network_address),
            ipaddress.ip_network(s).prefixlen,
        ),
    )


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ru-not-ru-domain/2.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    path.write_bytes(data)
    print(f"downloaded {url}: {len(data):,} bytes", file=sys.stderr)


def load_extras():
    if not EXTRA_FILE.exists():
        return []
    out = []
    for line in EXTRA_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().lower().rstrip(".")
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return sorted(set(out))


def write_lines(path, values, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n" + "\n".join(values) + "\n", encoding="utf-8")


def main():
    CACHE.mkdir(exist_ok=True)
    gs_path = CACHE / "geosite.dat"
    gi_path = CACHE / "geoip.dat"
    download(GEOSITE_URL, gs_path)
    download(GEOIP_URL, gi_path)

    geosite = parse_geosite(gs_path)
    ru_tags = sorted(t for t in geosite if t == "RU" or t.endswith("-RU"))

    domain_exact, domain_suffix, domain_keyword, domain_regex = set(), set(), set(), set()
    for tag in ru_tags:
        for typ, value in geosite[tag]:
            if not value:
                continue
            if typ == 0:
                domain_keyword.add(value)
            elif typ == 1:
                domain_regex.add(value)
            elif typ == 2:
                domain_suffix.add(value)
            elif typ == 3:
                domain_exact.add(value)

    extras = load_extras()
    domain_suffix.update(extras)

    networks = parse_geoip_ru(gi_path)
    ipv4 = [n for n in networks if ":" not in n]
    ipv6 = [n for n in networks if ":" in n]

    domain_rule = {}
    if domain_exact:
        domain_rule["domain"] = sorted(domain_exact)
    if domain_suffix:
        domain_rule["domain_suffix"] = sorted(domain_suffix)
    if domain_keyword:
        domain_rule["domain_keyword"] = sorted(domain_keyword)
    if domain_regex:
        domain_rule["domain_regex"] = sorted(domain_regex)

    geosite_json = {"version": 1, "rules": [domain_rule]}
    geoip_json = {"version": 1, "rules": [{"ip_cidr": networks}]}
    geoip_v4_json = {"version": 1, "rules": [{"ip_cidr": ipv4}]}
    geoip_v6_json = {"version": 1, "rules": [{"ip_cidr": ipv6}]}
    all_json = {"version": 1, "rules": [domain_rule, {"ip_cidr": networks}]}

    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in [
        ("ru-geosite.json", geosite_json),
        ("ru-geoip.json", geoip_json),
        ("ru-geoip-v4.json", geoip_v4_json),
        ("ru-geoip-v6.json", geoip_v6_json),
        ("ru-all.json", all_json),
    ]:
        (OUT / name).write_text(
            json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    write_lines(
        RULES / "ru-domain-suffix.txt",
        sorted(domain_suffix),
        f"# RU domain suffixes; source Alpaca geosite + overrides; entries={len(domain_suffix)}",
    )
    write_lines(
        RULES / "ru-domain-exact.txt",
        sorted(domain_exact),
        f"# RU exact domains; source Alpaca geosite; entries={len(domain_exact)}",
    )
    write_lines(
        RULES / "ru-domain-keyword.txt",
        sorted(domain_keyword),
        f"# RU domain keywords; source Alpaca geosite; entries={len(domain_keyword)}",
    )
    write_lines(
        RULES / "ru-domain-regex.txt",
        sorted(domain_regex),
        f"# RU domain regex; source Alpaca geosite; entries={len(domain_regex)}",
    )
    write_lines(
        RULES / "ru-ipv4.txt",
        ipv4,
        f"# RU IPv4 CIDR; source Alpaca geoip RU; entries={len(ipv4)}",
    )
    write_lines(
        RULES / "ru-ipv6.txt",
        ipv6,
        f"# RU IPv6 CIDR; source Alpaca geoip RU; entries={len(ipv6)}",
    )
    write_lines(
        RULES / "ru-tags.txt",
        [f"{t}\t{len(geosite[t])}" for t in ru_tags],
        f"# Included geosite tags; tags={len(ru_tags)}",
    )

    print(f"RU tags: {len(ru_tags)}")
    print(
        f"domains: suffix={len(domain_suffix)} exact={len(domain_exact)} "
        f"keyword={len(domain_keyword)} regex={len(domain_regex)}"
    )
    print(f"IP: ipv4={len(ipv4)} ipv6={len(ipv6)} total={len(networks)}")
    print(f"extra overrides: {len(extras)}")


if __name__ == "__main__":
    main()
