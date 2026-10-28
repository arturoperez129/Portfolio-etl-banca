"""Chequeos de integridad de la conciliación."""
import pandas as pd


def validar(libro, banco, conciliadas, pend_libro, pend_banco, res: dict) -> list[str]:
    fallas = []
    if conciliadas["id_libro"].duplicated().any() or conciliadas["id_banco"].duplicated().any():
        fallas.append("hay movimientos conciliados más de una vez")
    if len(conciliadas) + len(pend_libro) != len(libro):
        fallas.append("libro: conciliadas + pendientes no suma el total")
    if len(conciliadas) + len(pend_banco) != len(banco):
        fallas.append("banco: conciliadas + pendientes no suma el total")
    if res["diferencia_no_explicada"] != 0:
        fallas.append(f"diferencia de saldos sin explicar: {res['diferencia_no_explicada']:,}")
    if not isinstance(libro, pd.DataFrame) or libro["id_libro"].duplicated().any():
        fallas.append("id_libro duplicado")
    return fallas
