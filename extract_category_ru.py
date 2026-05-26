#!/usr/bin/env python3
"""
Extract domains from roscomvpn-geosite.dat (v2fly protobuf format)
and write them as plain text, filtering by TLD.

Categories used:
  whitelist      - Russian domestic services curated by roscomvpn (the main source)
  category-ru    - small supplemental list (banks, misc)

Output files:
  roscomvpn-whitelist-all.txt    - all domains from whitelist category
  roscomvpn-whitelist-nontld.txt - only non-.ru/.su/.рф (for use alongside tld-ru rule)
"""
import struct
import sys
import urllib.request
import os

DAT_URL = "https://cdn.jsdelivr.net/gh/hydraponique/roscomvpn-geosite/release/geosite.dat"
DAT_PATH = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "roscomvpn-geosite.dat")


def varint_decode(data, pos):
    result = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, pos


def read_field(data, pos):
    tag_varint, pos = varint_decode(data, pos)
    field_number = tag_varint >> 3
    wire_type = tag_varint & 0x7
    if wire_type == 0:  # varint
        value, pos = varint_decode(data, pos)
        return field_number, wire_type, value, pos
    elif wire_type == 2:  # length-delimited
        length, pos = varint_decode(data, pos)
        value = data[pos:pos + length]
        pos += length
        return field_number, wire_type, value, pos
    else:
        raise ValueError(f"Unsupported wire type {wire_type} at pos {pos}")


def parse_domain_entry(data):
    """Parse a Domain message: {type: varint, value: string, attribute: ...}"""
    pos = 0
    domain_type = 0
    value = ""
    while pos < len(data):
        field_number, wire_type, field_value, pos = read_field(data, pos)
        if field_number == 1 and wire_type == 0:
            domain_type = field_value
        elif field_number == 2 and wire_type == 2:
            value = field_value.decode("utf-8", errors="replace")
    return domain_type, value


def parse_geosite_entry(data):
    """Parse a GeoSite message: {country_code: string, domain: repeated Domain}"""
    pos = 0
    country_code = ""
    domains = []
    while pos < len(data):
        field_number, wire_type, field_value, pos = read_field(data, pos)
        if field_number == 1 and wire_type == 2:
            country_code = field_value.decode("utf-8", errors="replace").lower()
        elif field_number == 2 and wire_type == 2:
            domain_type, value = parse_domain_entry(field_value)
            domains.append((domain_type, value))
    return country_code, domains


def parse_geosite_list(data):
    """Parse GeoSiteList: {entry: repeated GeoSite}"""
    pos = 0
    entries = {}
    while pos < len(data):
        field_number, wire_type, field_value, pos = read_field(data, pos)
        if field_number == 1 and wire_type == 2:
            country_code, domains = parse_geosite_entry(field_value)
            if country_code not in entries:
                entries[country_code] = []
            entries[country_code].extend(domains)
    return entries


def download(url, dest):
    print(f"Downloading {url} ...", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "ru-not-ru-domain/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)
    print(f"Saved {len(data):,} bytes to {dest}", file=sys.stderr)


RU_TLDS = (".ru", ".su", ".рф", ".xn--p1ai")


def is_ru_tld(domain):
    d = domain.lower()
    return any(d == tld.lstrip(".") or d.endswith(tld) for tld in RU_TLDS)


def format_domain(domain_type, value):
    # 0=Plain(substring), 1=Regex, 2=Domain(suffix), 3=Full(exact)
    if domain_type == 1:
        return f"regexp:{value}"
    if domain_type == 3:
        return f"full:{value}"
    # type 0 and 2 both treated as suffix for routing purposes
    return value


def main():
    if not os.path.exists(DAT_PATH):
        download(DAT_URL, DAT_PATH)

    with open(DAT_PATH, "rb") as f:
        data = f.read()

    print("Parsing geosite.dat ...", file=sys.stderr)
    entries = parse_geosite_list(data)

    # Merge whitelist + category-ru, deduplicate
    seen = set()
    merged_all = []
    merged_nontld = []

    for cat in ["whitelist", "category-ru"]:
        for domain_type, value in entries.get(cat, []):
            if not value:
                continue
            key = (domain_type, value)
            if key in seen:
                continue
            seen.add(key)
            line = format_domain(domain_type, value)
            merged_all.append(line)
            if not is_ru_tld(value):
                merged_nontld.append(line)

    merged_all.sort()
    merged_nontld.sort()

    print(f"whitelist:    {len(entries.get('whitelist', []))} entries", file=sys.stderr)
    print(f"category-ru:  {len(entries.get('category-ru', []))} entries", file=sys.stderr)
    print(f"merged total: {len(merged_all)}, non-tld: {len(merged_nontld)}", file=sys.stderr)

    header_all = (
        "# roscomvpn whitelist+category-ru — all domains\n"
        "# Source: https://github.com/hydraponique/roscomvpn-geosite\n"
        f"# Entries: {len(merged_all)}\n"
    )
    header_nontld = (
        "# roscomvpn whitelist — non-.ru/.su/.рф domains only\n"
        "# Add as Rule Source (direct_ru) in panel to route Russian CDN/service domains via RU node\n"
        "# Source: https://github.com/hydraponique/roscomvpn-geosite\n"
        f"# Entries: {len(merged_nontld)}\n"
    )

    with open("roscomvpn-whitelist-all.txt", "w", encoding="utf-8") as f:
        f.write(header_all + "\n".join(merged_all) + "\n")

    with open("roscomvpn-whitelist-nontld.txt", "w", encoding="utf-8") as f:
        f.write(header_nontld + "\n".join(merged_nontld) + "\n")

    print(f"roscomvpn-whitelist-all.txt:    {len(merged_all)} entries", file=sys.stderr)
    print(f"roscomvpn-whitelist-nontld.txt: {len(merged_nontld)} entries", file=sys.stderr)


if __name__ == "__main__":
    main()
