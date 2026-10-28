"""Motor de conciliación por etapas, de la regla más estricta a la más flexible.

Cada etapa asigna pares 1 a 1 (un asiento del libro con un movimiento del banco) y solo
trabaja con lo que las etapas anteriores dejaron sin conciliar.
"""
import pandas as pd

ETAPAS = [
    # (nombre, claves de cruce, tolerancia en días, tolerancia de monto en PYG)
    ("1_referencia+monto+fecha_exactos", ["ref", "monto"], 0, 0),
    ("2_referencia+monto_con_desfase_fecha", ["ref", "monto"], 3, 0),
    ("3_monto+fecha_sin_referencia", ["monto"], 3, 0),
    ("4_referencia_con_diferencia_monto", ["ref"], 3, 50_000),
]


def _cruzar(libro: pd.DataFrame, banco: pd.DataFrame, claves: list[str], tol_dias: int, tol_monto: int):
    """Une por claves y se queda con el mejor par (menor desfase) respetando 1 a 1."""
    l = libro.rename(columns={"fecha": "fecha_l", "monto": "monto_l", "ref": "ref_l"})  # noqa: E741
    b = banco.rename(columns={"fecha": "fecha_b", "monto": "monto_b", "ref": "ref_b"})
    if "ref" in claves:  # una referencia vacía no identifica nada
        l, b = l[l["ref_l"] != ""], b[b["ref_b"] != ""]
    pares = l[["id_libro", "fecha_l", "monto_l", "ref_l"]].merge(
        b[["id_banco", "fecha_b", "monto_b", "ref_b"]],
        left_on=[f"{k}_l" for k in claves], right_on=[f"{k}_b" for k in claves],
    )
    pares["dias_dif"] = (pares["fecha_b"] - pares["fecha_l"]).dt.days.abs()
    pares["dif_monto"] = pares["monto_b"] - pares["monto_l"]
    pares = pares[(pares["dias_dif"] <= tol_dias) & (pares["dif_monto"].abs() <= tol_monto)]
    pares = pares.sort_values(["dias_dif", "id_libro", "id_banco"])
    pares = pares.drop_duplicates("id_libro").drop_duplicates("id_banco")
    return pares[["id_libro", "id_banco", "fecha_l", "fecha_b", "monto_l", "monto_b", "dias_dif", "dif_monto"]]


def conciliar(libro: pd.DataFrame, banco: pd.DataFrame):
    """Devuelve (conciliadas, pendientes_libro, pendientes_banco)."""
    pend_l, pend_b = libro.copy(), banco.copy()
    encontrados = []
    for nombre, claves, tol_dias, tol_monto in ETAPAS:
        pares = _cruzar(pend_l, pend_b, claves, tol_dias, tol_monto).assign(etapa=nombre)
        encontrados.append(pares)
        pend_l = pend_l[~pend_l["id_libro"].isin(pares["id_libro"])]
        pend_b = pend_b[~pend_b["id_banco"].isin(pares["id_banco"])]
    conciliadas = pd.concat(encontrados, ignore_index=True)
    return conciliadas, pend_l.reset_index(drop=True), pend_b.reset_index(drop=True)


def clasificar_pendientes(pend_libro: pd.DataFrame, pend_banco: pd.DataFrame):
    """Asigna una causa probable para que contabilidad sepa qué ajuste corresponde."""
    pl = pend_libro.copy()
    pl["causa_probable"] = pl["monto"].map(lambda m: "DEPOSITO_EN_TRANSITO" if m > 0 else "CHEQUE_O_PAGO_EN_TRANSITO")

    def causa_banco(desc: str) -> str:
        d = desc.upper()
        if "COMISION" in d:
            return "COMISION_BANCARIA_NO_REGISTRADA"
        if "INTERES" in d:
            return "INTERES_NO_REGISTRADO"
        if "DEBITO AUTOMATICO" in d:
            return "DEBITO_AUTOMATICO_NO_REGISTRADO"
        return "REVISAR_MANUALMENTE"

    pb = pend_banco.copy()
    pb["causa_probable"] = pb["descripcion"].map(causa_banco)
    return pl, pb


def resumen(libro, banco, conciliadas, pend_libro, pend_banco, saldo_inicial: int) -> dict:
    """Conciliación de saldos. Identidad: saldo_banco - saldo_libro =
    pendientes_banco - pendientes_libro + diferencias de monto en lo conciliado."""
    saldo_banco = saldo_inicial + int(banco["monto"].sum())
    saldo_libro = saldo_inicial + int(libro["monto"].sum())
    p_b, p_l = int(pend_banco["monto"].sum()), int(pend_libro["monto"].sum())
    dif_conc = int(conciliadas["dif_monto"].sum())
    explicado = p_b - p_l + dif_conc
    return {
        "movimientos_libro": len(libro),
        "movimientos_banco": len(banco),
        "conciliados": len(conciliadas),
        "pct_conciliado_libro": round(100 * len(conciliadas) / len(libro), 2),
        "pct_conciliado_banco": round(100 * len(conciliadas) / len(banco), 2),
        "pendientes_libro": len(pend_libro),
        "pendientes_banco": len(pend_banco),
        "conciliadas_por_etapa": conciliadas["etapa"].value_counts().sort_index().to_dict(),
        "saldo_segun_banco": saldo_banco,
        "saldo_segun_libro": saldo_libro,
        "diferencia_saldos": saldo_banco - saldo_libro,
        "componentes": {
            "partidas_solo_banco": p_b,
            "partidas_solo_libro": p_l,
            "diferencias_de_monto_en_conciliadas": dif_conc,
        },
        "diferencia_no_explicada": (saldo_banco - saldo_libro) - explicado,
    }
