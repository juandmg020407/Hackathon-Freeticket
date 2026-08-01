"""El split es la pieza que, si falla, invalida todas las metricas en silencio."""

import pandas as pd
import pytest

from ft.splits import folds_por_evento, split_temporal, verificar_sin_fuga


def _falso(n_eventos=10, por_evento=20, semana_de=lambda i: 27 + i // 3):
    filas = []
    for i in range(n_eventos):
        for j in range(por_evento):
            filas.append({
                "event_id": f"ev{i}", "ticket_id": f"t{i}_{j}",
                "semana_iso": semana_de(i), "etiquetado": True,
                "y": j % 2 == 0, "es_cortesia": j % 3 == 0,
            })
    return pd.DataFrame(filas)


def test_ningun_evento_en_dos_conjuntos():
    partes = split_temporal(_falso())
    ids = [set(p["event_id"]) for p in partes.values()]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            assert not (ids[i] & ids[j])


def test_detecta_fuga_deliberada():
    df = _falso()
    partes = {"train": df[df.event_id.isin(["ev0", "ev1"])],
              "test": df[df.event_id.isin(["ev1", "ev2"])]}  # ev1 repetido
    with pytest.raises(AssertionError, match="fuga"):
        verificar_sin_fuga(partes)


def test_no_pierde_entradas():
    df = _falso()
    partes = split_temporal(df)
    total = sum(len(p) for p in partes.values())
    assert total == len(df[df.etiquetado])


def test_solo_usa_julio_etiquetado():
    df = _falso()
    df.loc[df.event_id == "ev0", "etiquetado"] = False   # simula agosto
    partes = split_temporal(df)
    for p in partes.values():
        assert "ev0" not in set(p["event_id"])


def test_folds_reparten_eventos_completos():
    df = _falso(n_eventos=15)
    for tr_idx, te_idx in folds_por_evento(df, n_splits=5):
        ev_tr = set(df.iloc[tr_idx]["event_id"])
        ev_te = set(df.iloc[te_idx]["event_id"])
        assert not (ev_tr & ev_te), "un evento quedo partido entre train y test"
        assert len(te_idx) > 0


def test_folds_cubren_todo_una_vez():
    df = _falso(n_eventos=15)
    vistos = []
    for _, te_idx in folds_por_evento(df, n_splits=5):
        vistos.extend(te_idx.tolist())
    assert sorted(vistos) == list(range(len(df)))
