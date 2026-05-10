from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQUID_TEMPLATE = ROOT / "rootfs/opt/dify-aio/squid/squid.conf.template"


def test_squid_blocks_internal_destinations_before_localhost_allow() -> None:
    lines = SQUID_TEMPLATE.read_text().splitlines()
    required_acl_lines = {
        "acl deny_internal dst 0.0.0.0/8",
        "acl deny_internal dst 10.0.0.0/8",
        "acl deny_internal dst 100.64.0.0/10",
        "acl deny_internal dst 127.0.0.0/8",
        "acl deny_internal dst 169.254.0.0/16",
        "acl deny_internal dst 172.16.0.0/12",
        "acl deny_internal dst 192.168.0.0/16",
        "acl deny_internal dst 224.0.0.0/4",
        "acl deny_internal dst 240.0.0.0/4",
        "acl deny_internal dst ::1/128",
        "acl deny_internal dst fc00::/7",
        "acl deny_internal dst fe80::/10",
    }

    assert required_acl_lines.issubset(set(lines))  # nosec B101
    deny_index = lines.index("http_access deny deny_internal")
    localhost_index = lines.index("http_access allow localhost")
    marketplace_index = lines.index("http_access allow allowed_domains")

    assert deny_index < localhost_index  # nosec B101
    assert deny_index < marketplace_index  # nosec B101
