import pandas as pd
from etl_kyc.dedupe import consolidar, encontrar_pares
from etl_kyc.transform import (
    calcular_dv_ruc,
    normalizar_cedula,
    normalizar_direccion,
    normalizar_nombre,
    normalizar_telefono,
    transformar,
    validar_email,
    validar_ruc,
)


def test_normalizar_nombre_formato_apellido_coma():
    assert normalizar_nombre("GONZÁLEZ BENÍTEZ, José María") == "JOSE MARIA GONZALEZ BENITEZ"
    assert normalizar_nombre("  juan   pérez ") == "JUAN PEREZ"
    assert normalizar_nombre("") is None


def test_normalizar_cedula():
    assert normalizar_cedula("1.234.567") == "1234567"
    assert normalizar_cedula(" 4567890 ") == "4567890"
    assert normalizar_cedula("0") is None
    assert normalizar_cedula("1111111") is None
    assert normalizar_cedula(None) is None


def test_ruc_digito_verificador():
    assert calcular_dv_ruc("80000001") == calcular_dv_ruc("80000001")  # determinista
    dv = calcular_dv_ruc("1234567")
    assert validar_ruc(f"1234567-{dv}")
    assert not validar_ruc(f"1234567-{(dv + 1) % 10}")
    assert not validar_ruc("abc")


def test_telefono_formatos():
    esperado = "+595 981 123456"
    for v in ["0981 123 456", "+595981123456", "(0981) 123456", "0981123456", "981123456"]:
        assert normalizar_telefono(v) == esperado
    assert normalizar_telefono("981123") is None


def test_email_y_direccion():
    assert validar_email("Juan.Perez@GMAIL.com") == "juan.perez@gmail.com"
    assert validar_email("juan.perezgmail.com") is None
    assert normalizar_direccion("Avda. España 1234") == "AVENIDA ESPANA 1234"
    assert normalizar_direccion("C/ Palma 100") == "CALLE PALMA 100"


def _clientes():
    return pd.DataFrame({
        "id_cliente": ["C1", "C2", "C3", "C4"],
        "nombre_completo": ["Juan Carlos Pérez Gómez", "PEREZ GOMEZ, JUAN CARLOS", "Juan Karlos Perez Gomez",
                            "Ana Torres"],
        "cedula": ["1.234.567", "1234567", None, "7654321"],
        "ruc": [None] * 4,
        "fecha_nacimiento": ["1990-05-01", "1990-05-01", "1990-05-01", "1985-01-01"],
        "telefono": ["0981123456"] * 4,
        "email": [None] * 4,
        "direccion": ["Calle Palma 1"] * 4,
        "ciudad": ["Luque"] * 4,
        "fecha_alta": ["2020-01-01", "2021-01-01", "2022-01-01", "2020-01-01"],
    })


def test_deteccion_y_consolidacion():
    limpio, _ = transformar(_clientes())
    pares = encontrar_pares(limpio, umbral=92)
    reglas = set(pares["regla"])
    assert "cedula_exacta" in reglas and "nombre_difuso+fecha_nacimiento" in reglas
    con_maestro, unicos = consolidar(limpio, pares)
    assert len(unicos) == 2  # {C1,C2,C3} y {C4}
    assert con_maestro.loc[con_maestro.id_cliente == "C3", "id_cliente_maestro"].iloc[0] == "C2"
    assert con_maestro.loc[con_maestro.id_cliente == "C4", "id_cliente_maestro"].iloc[0] == "C4"
