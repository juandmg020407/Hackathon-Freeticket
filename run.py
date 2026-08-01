#!/usr/bin/env python
"""Pipeline de punta a punta.

    python run.py              descarga (con cache), cruza y proyecta
    python run.py --force      vuelve a bajar los datos del API
    python run.py --puerta     ademas genera los links efimeros de puerta
"""

import sys
import time

from ft import fetch, forecast, match


def main() -> int:
    t0 = time.time()
    force = "--force" in sys.argv

    print("[1/3] Datos")
    fetch.main(force=force)

    print("\n[2/3] Cruce Boom <-> FreeTicket")
    match.main()

    print("\n[3/3] Proyeccion de agosto")
    forecast.main()

    if "--puerta" in sys.argv:
        print("\n[extra] Links de puerta")
        from ft import puerta
        puerta.generar()

    print(f"\nListo en {time.time() - t0:.1f}s — matches.csv, forecast.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
