"""Estandarización de datos de clientes (nombres, cédula, RUC, teléfono, email, dirección)."""
import re
import unicodedata

import pandas as pd

CIUDADES = {
    "ASUNCION": "Asunción", "ASU": "Asunción",
    "FERNANDO DE LA MORA": "Fernando de la Mora", "FDO. DE LA MORA": "Fernando de la Mora",
    "FERNANDO D.L. MORA": "Fernando de la Mora",
    "LUQUE": "Luque", "SAN LORENZO": "San Lorenzo", "S. LORENZO": "San Lorenzo",
    "LAMBARE": "Lambaré", "CAPIATA": "Capiatá", "ENCARNACION": "Encarnación",
    "CIUDAD DEL ESTE": "Ciudad del Este", "C. DEL ESTE": "Ciudad del Este", "CDE": "Ciudad del Este",
}
EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")


def sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar_nombre(valor) -> str | None:
    """'GONZALEZ BENITEZ, JUAN' -> 'JUAN GONZALEZ BENITEZ' (mayúsculas, sin acentos ni signos)."""
    if pd.isna(valor) or not str(valor).strip():
        return None
    t = sin_acentos(str(valor)).upper()
    if "," in t:
        apellidos, nombres = t.split(",", 1)
        t = f"{nombres} {apellidos}"
    t = re.sub(r"[^A-Z ]", " ", t)
    return re.sub(r"\s+", " ", t).strip() or None


def normalizar_cedula(valor) -> str | None:
    """Deja solo dígitos; válida si tiene entre 5 y 8 dígitos y no es un valor basura."""
    if pd.isna(valor):
        return None
    d = re.sub(r"\D", "", str(valor)).lstrip("0")
    if not 5 <= len(d) <= 8 or len(set(d)) == 1:
        return None
    return d


def calcular_dv_ruc(ci: str, base_max: int = 11) -> int:
    """Dígito verificador del RUC paraguayo (módulo 11)."""
    total, k = 0, 2
    for dig in reversed(ci):
        total += int(dig) * k
        k = k + 1 if k < base_max else 2
    resto = total % 11
    return 11 - resto if resto > 1 else 0


def validar_ruc(valor) -> bool:
    """True si el RUC tiene formato 'numero-DV' y el DV es correcto."""
    if pd.isna(valor):
        return False
    m = re.fullmatch(r"\s*(\d{5,9})-(\d)\s*", str(valor))
    return bool(m) and calcular_dv_ruc(m.group(1)) == int(m.group(2))


def normalizar_telefono(valor) -> str | None:
    """Celulares paraguayos -> '+595 9XX XXXXXX'. Otros formatos o incompletos -> None."""
    if pd.isna(valor):
        return None
    d = re.sub(r"\D", "", str(valor))
    if d.startswith("595"):
        d = d[3:]
    d = d.lstrip("0")
    if len(d) == 9 and d.startswith("9"):
        return f"+595 {d[:3]} {d[3:]}"
    return None


def validar_email(valor) -> str | None:
    if pd.isna(valor):
        return None
    e = str(valor).strip().lower()
    return e if EMAIL_RE.match(e) else None


def normalizar_ciudad(valor) -> str | None:
    if pd.isna(valor):
        return None
    clave = sin_acentos(str(valor)).upper().strip()
    return CIUDADES.get(clave, str(valor).strip().title())


def normalizar_direccion(valor) -> str | None:
    if pd.isna(valor):
        return None
    t = sin_acentos(str(valor)).upper()
    t = re.sub(r"\bAVDA?\b\.?", "AVENIDA", t)
    t = re.sub(r"\bC/", "CALLE ", t)
    return re.sub(r"\s+", " ", t).strip()


def transformar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    out["nombre_norm"] = out["nombre_completo"].map(normalizar_nombre)
    out["cedula_raw"] = out["cedula"]
    out["cedula"] = out["cedula"].map(normalizar_cedula)
    out["ruc_valido"] = out["ruc"].map(validar_ruc)
    out["telefono_raw"] = out["telefono"]
    out["telefono"] = out["telefono"].map(normalizar_telefono)
    out["email"] = out["email"].map(validar_email)
    out["ciudad"] = out["ciudad"].map(normalizar_ciudad)
    out["direccion"] = out["direccion"].map(normalizar_direccion)
    out["fecha_nacimiento"] = pd.to_datetime(out["fecha_nacimiento"], errors="coerce")
    out["fecha_alta"] = pd.to_datetime(out["fecha_alta"], errors="coerce")

    # Consistencia: si el RUC es válido pero no hay cédula, la cédula sale del RUC
    ruc_ci = out["ruc"].where(out["ruc_valido"]).str.extract(r"^(\d+)-")[0]
    sin_ci = out["cedula"].isna() & ruc_ci.notna()
    out.loc[sin_ci, "cedula"] = ruc_ci[sin_ci]

    n = len(out)
    metricas = {
        "filas": n,
        "cedulas_invalidas_o_vacias": int(out["cedula"].isna().sum()),
        "cedulas_recuperadas_desde_ruc": int(sin_ci.sum()),
        "ruc_presentes": int(out["ruc"].notna().sum()),
        "ruc_con_dv_incorrecto": int((out["ruc"].notna() & ~out["ruc_valido"]).sum()),
        "telefonos_invalidos": int(out["telefono"].isna().sum()),
        "emails_invalidos_o_vacios": int(out["email"].isna().sum()),
    }
    return out, metricas
