import pandas as pd
from etl_conciliacion.match import conciliar, resumen
from etl_conciliacion.transform import normalizar_referencia


def _fuente(filas, id_col):
    return pd.DataFrame(filas, columns=[id_col, "fecha", "ref", "monto", "descripcion"]).assign(
        fecha=lambda d: pd.to_datetime(d["fecha"])
    )


def test_normalizar_referencia():
    assert normalizar_referencia("TRX-000123") == normalizar_referencia("trx000123") == "TRX000123"
    assert normalizar_referencia(None) == "" and normalizar_referencia("") == ""


def test_conciliacion_por_etapas_y_identidad_de_saldos():
    libro = _fuente([
        ["L1", "2025-06-01", "TRX1", 1_000_000, "exacto"],
        ["L2", "2025-06-02", "TRX2", -500_000, "fecha distinta"],
        ["L3", "2025-06-03", "", 2_000_000, "sin referencia"],
        ["L4", "2025-06-04", "TRX4", -300_000, "monto distinto"],
        ["L5", "2025-06-05", "TRX5", -700_000, "solo libro"],
    ], "id_libro")
    banco = _fuente([
        ["B1", "2025-06-01", "TRX1", 1_000_000, "x"],
        ["B2", "2025-06-04", "TRX2", -500_000, "x"],
        ["B3", "2025-06-03", "", 2_000_000, "x"],
        ["B4", "2025-06-04", "TRX4", -310_000, "x"],
        ["B5", "2025-06-10", "BCO1", -35_000, "COMISION"],
    ], "id_banco")
    conc, pl, pb = conciliar(libro, banco)

    etapa = dict(zip(conc["id_libro"], conc["etapa"], strict=True))
    assert etapa["L1"].startswith("1_") and etapa["L2"].startswith("2_")
    assert etapa["L3"].startswith("3_") and etapa["L4"].startswith("4_")
    assert pl["id_libro"].tolist() == ["L5"] and pb["id_banco"].tolist() == ["B5"]

    r = resumen(libro, banco, conc, pl, pb, saldo_inicial=10_000_000)
    assert r["diferencia_no_explicada"] == 0
    assert r["conciliados"] == 4


def test_un_movimiento_no_se_concilia_dos_veces():
    libro = _fuente([["L1", "2025-06-01", "A", 100, "x"], ["L2", "2025-06-01", "B", 100, "x"]], "id_libro")
    banco = _fuente([["B1", "2025-06-01", "", 100, "x"]], "id_banco")
    conc, pl, pb = conciliar(libro, banco)
    assert len(conc) == 1 and len(pl) == 1 and pb.empty
