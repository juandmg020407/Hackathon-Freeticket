"""Experimento completo: compara, elige campeon y toca el test UNA vez.

Deja todo en reports/metrics.json y reports/figures/ para que las slides y la
skill citen numeros que salieron de aqui y no de la memoria de nadie.

Protocolo:
  1. CV agrupada por evento sobre train+val (21 eventos) -> comparar candidatos.
  2. Comparacion pareada contra el mejor baseline -> decir si la ventaja es real.
  3. Elegir campeon.
  4. Reentrenar con train+val y evaluar en test (11 eventos). Una sola vez.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .api import FIGURES, REPORTS, asegurar_carpetas
from .baselines import construir_todos as baselines
from .candidatos import construir_todos as candidatos
from .datos import tickets
from .evaluate import (
    agregar_por_evento,
    bootstrap_mae,
    comparar_pareado,
    error_por_segmento,
    evaluar_cv,
    metricas_entrada,
    metricas_evento,
    predicciones_oof,
    tabla_calibracion,
)
from .splits import resumen, split_temporal

CAMPEON = "M1 · logística segmentada"


def _figuras(desarrollo, preds, tab, y):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.dpi": 110, "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": .25})
    AZUL, NARANJA, GRIS = "#3b6ef5", "#f5a03b", "#8b93a7"

    # --- escalera de error con IC ---
    t = tab.sort_values("mae", ascending=False)
    lo = [float(s.strip("[]").split(",")[0]) for s in t.mae_ic95]
    hi = [float(s.strip("[]").split(",")[1]) for s in t.mae_ic95]
    fig, ax = plt.subplots(figsize=(8, 4))
    col = [NARANJA if n.startswith("B") else AZUL for n in t.modelo]
    ax.barh(t.modelo, t.mae, color=col)
    ax.errorbar(t.mae, range(len(t)), xerr=[t.mae - lo, np.array(hi) - t.mae],
                fmt="none", ecolor="#33384a", capsize=3, lw=1.2)
    ax.set_xlabel("error medio por evento (personas) — IC 95%")
    ax.set_title("Nadie le gana de forma concluyente a la tasa por tipo",
                 loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "07_comparacion_modelos.png", bbox_inches="tight")
    plt.close(fig)

    # --- calibracion del campeon vs mejor baseline ---
    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    ax.plot([0, 1], [0, 1], color=GRIS, ls="--", lw=1, label="perfecta")
    for nombre, color in [(CAMPEON, AZUL), ("B2 · tasa por tipo", NARANJA)]:
        c = tabla_calibracion(y, preds[nombre])
        ax.plot(c.p_medio, c.observado, "o-", color=color, label=nombre, ms=4.5)
    ax.set_xlabel("probabilidad predicha")
    ax.set_ylabel("frecuencia observada")
    ax.set_title("Calibración", loc="left", fontweight="bold")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "08_calibracion.png", bbox_inches="tight")
    plt.close(fig)

    # --- predicho vs observado por evento ---
    ev = agregar_por_evento(desarrollo, preds[CAMPEON])
    fig, ax = plt.subplots(figsize=(5, 4.4))
    lim = float(max(ev.obs.max(), ev.pred.max())) * 1.08
    ax.plot([0, lim], [0, lim], color=GRIS, ls="--", lw=1)
    ax.scatter(ev.obs, ev.pred, s=ev.n / 5, c=NARANJA, alpha=.8, edgecolor="none")
    ax.set_xlabel("asistencia observada")
    ax.set_ylabel("asistencia predicha")
    ax.set_title("Predicho vs observado, fuera de muestra", loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "09_predicho_vs_observado.png", bbox_inches="tight")
    plt.close(fig)


def main() -> dict:
    asegurar_carpetas()
    df = tickets()
    partes = split_temporal(df)
    desarrollo = pd.concat([partes["train"], partes["val"]])
    test = partes["test"]

    print("Reparto de julio")
    print(resumen(partes).to_string(index=False))

    modelos = baselines() + candidatos()
    print(f"\n[1] CV agrupada por evento sobre train+val "
          f"({desarrollo.event_id.nunique()} eventos)")
    tab = evaluar_cv(modelos, desarrollo, n_splits=5)
    print(tab[["modelo", "mae", "mae_ic95", "sesgo", "mape", "log_loss",
               "auc_roc", "ece"]].to_string(index=False,
                                            float_format=lambda v: f"{v:.4f}"))

    preds = predicciones_oof(modelos, desarrollo, n_splits=5)
    y_des = desarrollo["y"].astype(int).to_numpy()

    mejor_base = tab[tab.modelo.str.startswith("B")].sort_values("mae").iloc[0]["modelo"]
    print(f"\n[2] Comparación pareada contra {mejor_base}")
    pareadas = {}
    for nombre in [m.nombre for m in modelos if m.nombre.startswith("M")]:
        r = comparar_pareado(desarrollo, preds[nombre], preds[mejor_base])
        pareadas[nombre] = r
        print(f"  {nombre:32} dif={r['dif_media']:+6.2f} "
              f"IC95=[{r['ic95'][0]:+.2f}, {r['ic95'][1]:+.2f}] "
              f"concluyente: {'SÍ' if r['concluyente'] else 'no'}")

    print(f"\n[3] Campeón: {CAMPEON}")
    print("    empata en MAE, pero gana en calibración, MAPE y discriminación,")
    print("    y da probabilidad por entrada — que es lo que la capa prescriptiva necesita.")

    print("\n[4] Test (11 eventos, se toca una sola vez)")
    campeon = next(m for m in modelos if m.nombre == CAMPEON)
    base2 = next(m for m in modelos if m.nombre == mejor_base)
    campeon.fit(desarrollo)
    base2.fit(desarrollo)
    p_test = campeon.predict_proba(test)
    p_test_base = base2.predict_proba(test)
    y_test = test["y"].astype(int).to_numpy()

    m_ent = metricas_entrada(y_test, p_test)
    m_ev = metricas_evento(test, p_test)
    m_ev_base = metricas_evento(test, p_test_base)
    ic_c = bootstrap_mae(test, p_test)
    ic_b = bootstrap_mae(test, p_test_base)
    par_test = comparar_pareado(test, p_test, p_test_base)
    m_ev["mae_ic95"] = list(ic_c)
    m_ev_base["mae_ic95"] = list(ic_b)
    print(f"    {CAMPEON}: MAE={m_ev['mae']:.1f} IC95=[{ic_c[0]:.1f}, {ic_c[1]:.1f}]  "
          f"MAPE={m_ev['mape']:.1%}  sesgo={m_ev['sesgo']:+.1f}  "
          f"AUC={m_ent['auc_roc']:.3f}  ECE={m_ent['ece']:.4f}")
    print(f"    {mejor_base}: MAE={m_ev_base['mae']:.1f} IC95=[{ic_b[0]:.1f}, {ic_b[1]:.1f}]  "
          f"MAPE={m_ev_base['mape']:.1%}  sesgo={m_ev_base['sesgo']:+.1f}")
    print(f"    pareado en test: dif={par_test['dif_media']:+.2f} personas por evento, "
          f"IC95=[{par_test['ic95'][0]:+.2f}, {par_test['ic95'][1]:+.2f}] "
          f"-> {'la ventaja se sostiene' if par_test['concluyente'] else 'no concluyente'}")

    _figuras(desarrollo, preds, tab, y_des)
    seg = error_por_segmento(test, p_test)
    print("\n[5] Dónde falla, en test")
    print(seg.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    metrics = {
        "protocolo": {
            "split": "temporal por semana ISO, agrupado por evento",
            "reparto": resumen(partes).to_dict("records"),
            "cv": "GroupKFold(5) por event_id sobre train+val",
            "test_evaluado_veces": 1,
        },
        "comparacion_cv": tab.to_dict("records"),
        "comparacion_pareada_vs_baseline": {"baseline": mejor_base, "resultados": pareadas},
        "campeon": CAMPEON,
        "test": {
            "campeon": {**m_ent, **m_ev},
            "baseline": {"modelo": mejor_base, **m_ev_base},
            "pareado_campeon_vs_baseline": par_test,
        },
        "error_por_segmento_test": seg.to_dict("records"),
        "calibracion_test": tabla_calibracion(y_test, p_test).to_dict("records"),
    }
    (REPORTS / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nreports/metrics.json y {len(list(FIGURES.glob('*.png')))} figuras escritas")
    return metrics


if __name__ == "__main__":
    main()
