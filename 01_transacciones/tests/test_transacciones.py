import pandas as pd
from etl_transacciones.transform import (
    limpiar_monto,
    normalizar_categoria,
    parsear_fechas,
    transformar,
)
from etl_transacciones.validate import validar


def test_limpiar_monto_miles_y_decimales():
    s = pd.Series(["1.250.000", "1250000", "12.50", " 300 ", "abc", None])
    r = limpiar_monto(s).tolist()
    assert r[:4] == [1250000.0, 1250000.0, 12.5, 300.0]
    assert pd.isna(r[4]) and pd.isna(r[5])


def test_parsear_fechas_formatos_mixtos_e_invalidos():
    s = pd.Series(["2025-03-14 10:22:11", "14/03/2025", "31/02/2025", "N/A", ""])
    r = parsear_fechas(s)
    assert r.iloc[0] == pd.Timestamp("2025-03-14 10:22:11")
    assert r.iloc[1] == pd.Timestamp("2025-03-14")
    assert r.iloc[2:].isna().all()


def test_normalizar_categoria():
    s = pd.Series([" supermercado ", "Retiro Atm", "SUPER", "Combustibles", None, "xyz"])
    assert normalizar_categoria(s).tolist() == [
        "SUPERMERCADO", "RETIRO_ATM", "SUPERMERCADO", "COMBUSTIBLE",
        "SIN_CATEGORIA", "SIN_CATEGORIA",
    ]


def _df(filas):
    cols = ["id_transaccion", "id_cuenta", "fecha", "monto", "moneda", "tipo", "categoria", "comercio", "canal"]
    return pd.DataFrame(filas, columns=cols)


def test_transformar_separa_rechazos_y_corrige_signo():
    df = _df([
        ["T1", "A", "2025-01-01 10:00:00", "1.000.000", "PYG", "DEBITO", "salud", "x", "app"],
        ["T1", "A", "2025-01-01 10:00:00", "1.000.000", "PYG", "DEBITO", "salud", "x", "app"],  # dup
        ["T2", "A", "31/02/2025", "500", "PYG", "CREDITO", "salario", "x", "web"],              # fecha
        ["T3", "A", "02/01/2025", "-2000000", "PYG", "CREDITO", "salario", "x", "web"],          # signo
        ["T4", "A", "02/01/2025", "0", "PYG", "DEBITO", "salud", "x", "web"],                   # monto 0
        ["T5", "A", "02/01/2025", "10", "XXX", "DEBITO", "salud", "x", "web"],                  # moneda
        ["T6", "A", "03/01/2025", "10.00", "USD", "DEBITO", "salud", "x", "pos"],
    ])
    limpio, rechazado, m = transformar(df)
    assert sorted(limpio["id_transaccion"]) == ["T1", "T3", "T6"]
    assert set(rechazado["motivo_rechazo"]) == {
        "duplicado", "fecha_invalida", "monto_invalido", "moneda_invalida"
    }
    assert limpio.loc[limpio.id_transaccion == "T3", "monto"].iloc[0] == 2_000_000
    assert limpio.loc[limpio.id_transaccion == "T6", "monto_pyg"].iloc[0] == 75_000
    assert m["montos_con_signo_corregido"] == 1
    assert validar(limpio) == []
