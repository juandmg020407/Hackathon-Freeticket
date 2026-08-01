#!/usr/bin/env python
"""Pipeline de punta a punta.

    python run.py                descarga (con cache), cruza, proyecta y prescribe
    python run.py --force        vuelve a bajar los datos del API
    python run.py --puerta       ademas genera los links efimeros de puerta
    python run.py --experimento  ademas corre la comparacion de modelos completa
"""

import sys
import time

from ft import dashboard, fetch, forecast, match, overbooking, prescribe


def main() -> int:
    t0 = time.time()
    force = "--force" in sys.argv

    print("[1/6] Datos")
    fetch.main(force=force)

    print("\n[2/6] Cruce Boom <-> FreeTicket")
    match.main()

    print("\n[3/6] Proyeccion de agosto")
    forecast.main()

    print("\n[4/6] Acciones recomendadas")
    prescribe.main()

    print("\n[5/6] Sobreventa segura")
    overbooking.main()

    # La skill responde SOLO desde este archivo. Va al final y no en un comando
    # aparte: si dependiera de que alguien se acuerde de correrlo, la copia que
    # viaja con la skill envejeceria en silencio.
    print("\n[6/6] Dashboard para la skill")
    dashboard.main()

    if "--experimento" in sys.argv:
        print("\n[extra] Comparacion de modelos")
        from ft import experimento
        experimento.main()

    if "--puerta" in sys.argv:
        print("\n[extra] Links de puerta")
        from ft import puerta
        puerta.generar()

    print(f"\nListo en {time.time() - t0:.1f}s — outputs/: matches.csv, "
          f"forecast.csv, acciones.csv, overbooking.csv, dashboard.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

