"""Cliente de linha de comando para MCP IPMA."""
from __future__ import annotations

import argparse
import re
import sys
from itertools import count

import requests

BASE = "http://localhost:5000"
_RPC = f"{BASE}/rpc"
_id_gen = count(1)


def _rpc_call(method: str, params: dict | None = None) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": next(_id_gen),
        "method": method,
        "params": params or {},
    }
    resp = requests.post(_RPC, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_forecast(city: str) -> str:
    res = _rpc_call(
        "tools/call",
        {"name": "get_forecast", "arguments": {"city": city}},
    )
    if "error" in res:
        raise RuntimeError(res["error"]["message"])
    return res["result"]["content"][0]["text"]


def parse_city(query: str) -> str | None:
    patterns = [
        r"em\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]+)$",
        r"no\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]+)$",
        r"para\s+hoje\s+em\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]+)$",
        r"(?:meteorologia|tempo)\s+(.+?)\s*(?:hoje)?$",
    ]
    for pat in patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch weather forecast from IPMA via MCP"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Ex.: 'Meteorologia Braga Hoje' ou "
        "'Tempo hoje no Porto'",
    )
    args = parser.parse_args()

    if not args.query:
        print("Erro: falta --query", file=sys.stderr)
        sys.exit(1)

    city = parse_city(args.query)
    if not city:
        print(
            "Erro: não consegui extrair a cidade. "
            "Tenta 'Tempo hoje em Braga'.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        print("\n" + get_forecast(city))
    except Exception as exc:
        msg = str(exc)
        if "não encontrada" in msg.lower():
            print("Erro: cidade inválida", file=sys.stderr)
        else:
            print(f"Erro: {msg}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
