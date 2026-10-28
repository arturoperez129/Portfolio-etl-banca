import pandas as pd
from etl_mora.transform import (
    FECHA_CORTE,
    cuota_estimada,
    dias_atraso,
    limpiar_tasa,
    tramo_mora,
    transformar,
)
from etl_mora.validate import validar


def test_limpiar_tasa():
    r = limpiar_tasa(pd.Series(["18,5%", "22.0", "30", "x"]))
    assert r.tolist()[:3] == [18.5, 22.0, 30.0] and pd.isna(r.iloc[3])


def test_dias_atraso_y_tramos():
    f = pd.Series(pd.to_datetime([None, "2025-06-29", "2025-05-31", "2025-04-01", "2025-01-01", "2024-01-01"]))
    d = dias_atraso(f, FECHA_CORTE)
    assert d.tolist() == [0, 1, 30, 90, 180, 546]
    assert tramo_mora(d).tolist() == ["0_AL_DIA", "1_30", "1_30", "61_90", "91_180", "MAS_180"]


def test_cuota_sistema_frances():
    c = cuota_estimada(pd.Series([12_000_000]), pd.Series([12.0]), pd.Series([12]))
    assert abs(c.iloc[0] - 1_066_185) < 5  # cuota nivelada de referencia


def _cartera():
    cols = ["id_credito", "id_cliente", "producto", "monto_desembolsado", "saldo_capital", "tasa_anual",
            "plazo_meses", "fecha_desembolso", "fecha_primer_vencimiento_impago", "ingreso_mensual",
            "edad", "antiguedad_laboral_meses"]
    filas = [
        ["A", "C1", " consumo ", "10000000", "8000000", "20,0%", "24", "2024-01-01", None, "5000000", "35", "60"],
        ["A", "C1", " consumo ", "10000000", "8000000", "20,0%", "24", "2024-01-01", None, "5000000", "35", "60"],
        ["B", "C2", "PYME", "50000000", "40000000", "15.0", "36", "2023-06-01", "2025-01-01", None, "999", "12"],
        ["C", "C3", "PYME", "50000000", "-5", "15.0", "36", "2023-06-01", None, "7000000", "40", "12"],
        ["D", "C4", "PYME", "50000000", "1000000", "15.0", "36", "2023-06-01", "2023-01-01", "7000000", "40", "12"],
        ["E", "C5", "PYME", "50000000", "30000000", "15.0", "36", "2023-06-01", None, "6000000", "45", "12"],
    ]
    return pd.DataFrame(filas, columns=cols)


def test_transformar_reglas():
    limpio, rechazado, m = transformar(_cartera())
    assert sorted(limpio["id_credito"]) == ["A", "B", "E"]
    assert set(rechazado["motivo_rechazo"]) == {"duplicado", "saldo_invalido", "impago_anterior_a_desembolso"}
    b = limpio[limpio.id_credito == "B"].iloc[0]
    assert b["dias_atraso"] == 180 and b["tramo_mora"] == "91_180" and b["en_mora_90"]
    assert b["ingreso_imputado"] and b["edad_imputada"] and b["ingreso_mensual"] == 6_000_000
    assert limpio.loc[limpio.id_credito == "A", "producto"].iloc[0] == "CONSUMO"
    assert validar(limpio) == []
    assert 0 < m["indice_morosidad_pct"] < 100
