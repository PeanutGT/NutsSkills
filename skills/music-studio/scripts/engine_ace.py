"""Compatibility shim: `engine_ace.py --request req.json` == `ace_worker.py --request req.json` (one-shot run)."""
import sys

import ace_worker

if __name__ == "__main__":
    sys.exit(ace_worker.main())
