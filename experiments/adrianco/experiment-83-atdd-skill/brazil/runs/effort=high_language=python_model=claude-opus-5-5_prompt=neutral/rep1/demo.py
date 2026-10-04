"""Answer the sample questions by calling the MCP tools directly (no LLM needed).

    python demo.py            # all sample questions
    python demo.py derbies    # only questions whose text/tool contains "derbies"
"""

import sys
import time

from brsoccer.samples import CASES
from brsoccer.server import MCPServer


def main() -> None:
    needle = " ".join(sys.argv[1:]).lower()
    server = MCPServer()
    server.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    for i, (question, tool, args, _) in enumerate(CASES, 1):
        if needle and needle not in question.lower() and needle not in tool:
            continue
        start = time.perf_counter()
        resp = server.handle({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                              "params": {"name": tool, "arguments": args}})
        ms = (time.perf_counter() - start) * 1000
        print(f"Q{i}: {question}\n    → {tool}({args})  [{ms:.0f} ms]\n")
        print(resp["result"]["content"][0]["text"])
        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    main()
