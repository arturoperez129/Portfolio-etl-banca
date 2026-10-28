"""Detección de clientes duplicados: regla exacta (cédula) + coincidencia difusa (nombre)."""
from itertools import combinations

import pandas as pd
from rapidfuzz import fuzz


def _pares_exactos(df: pd.DataFrame) -> list[tuple]:
    pares = []
    for _, g in df[df["cedula"].notna()].groupby("cedula"):
        for a, b in combinations(g.index, 2):
            pares.append((a, b, 100.0, "cedula_exacta"))
    return pares


def _pares_difusos(df: pd.DataFrame, umbral: float) -> list[tuple]:
    """Blocking por fecha de nacimiento para evitar comparar todos contra todos (O(n^2))."""
    pares = []
    for _, g in df[df["fecha_nacimiento"].notna() & df["nombre_norm"].notna()].groupby("fecha_nacimiento"):
        if len(g) < 2:
            continue
        for (i, ni), (j, nj) in combinations(zip(g.index, g["nombre_norm"], strict=True), 2):
            score = fuzz.WRatio(ni, nj)
            if score >= umbral:
                pares.append((i, j, float(score), "nombre_difuso+fecha_nacimiento"))
    return pares


def encontrar_pares(df: pd.DataFrame, umbral: float = 92.0) -> pd.DataFrame:
    pares = _pares_exactos(df) + _pares_difusos(df, umbral)
    res = pd.DataFrame(pares, columns=["idx_a", "idx_b", "score", "regla"])
    if res.empty:
        return res.assign(id_cliente_a=[], id_cliente_b=[])
    # si un par cae en ambas reglas, se conserva la de mayor score
    res = res.sort_values("score", ascending=False).drop_duplicates(["idx_a", "idx_b"])
    res["id_cliente_a"] = df.loc[res["idx_a"], "id_cliente"].to_numpy()
    res["id_cliente_b"] = df.loc[res["idx_b"], "id_cliente"].to_numpy()
    return res.reset_index(drop=True)


def _clusters(indices, pares: pd.DataFrame) -> dict:
    """Union-Find: agrupa registros conectados por algún par duplicado."""
    padre = {i: i for i in indices}

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    for a, b in zip(pares["idx_a"], pares["idx_b"], strict=True):
        padre[raiz(a)] = raiz(b)
    return {i: raiz(i) for i in indices}


def consolidar(df: pd.DataFrame, pares: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (df con id_cliente_maestro, tabla de clientes únicos / 'golden record')."""
    df = df.copy()
    df["cluster"] = pd.Series(_clusters(df.index, pares))
    campos = ["nombre_norm", "cedula", "fecha_nacimiento", "telefono", "email", "direccion", "ciudad"]
    df["_completitud"] = df[campos].notna().sum(axis=1)
    orden = df.sort_values(["cluster", "_completitud", "fecha_alta"], ascending=[True, False, False])
    maestros = orden.drop_duplicates("cluster")
    mapa = maestros.set_index("cluster")["id_cliente"]
    df["id_cliente_maestro"] = df["cluster"].map(mapa)
    unicos = maestros.drop(columns=["_completitud"]).sort_values("id_cliente").reset_index(drop=True)
    return df.drop(columns=["_completitud"]), unicos


def evaluar(df: pd.DataFrame, pares: pd.DataFrame, ground_truth: pd.DataFrame) -> dict:
    """Precisión y recall a nivel de pares contra la verdad conocida (datos sintéticos)."""
    real = df[["id_cliente"]].merge(ground_truth, on="id_cliente")
    verdaderos = set()
    for _, g in real.groupby("id_real"):
        verdaderos |= {frozenset(p) for p in combinations(g["id_cliente"], 2)}
    detectados = {frozenset(p) for p in zip(pares["id_cliente_a"], pares["id_cliente_b"], strict=True)}
    tp = len(verdaderos & detectados)
    return {
        "pares_reales": len(verdaderos),
        "pares_detectados": len(detectados),
        "precision": round(tp / len(detectados), 3) if detectados else 0.0,
        "recall": round(tp / len(verdaderos), 3) if verdaderos else 0.0,
    }
