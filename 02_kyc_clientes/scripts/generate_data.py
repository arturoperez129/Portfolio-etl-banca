"""Genera una base de clientes SINTÉTICA (estilo KYC Paraguay) con ruido y duplicados.

Produce:
  data/raw/clientes.csv              -> datos sucios
  data/raw/clientes_ground_truth.csv -> id_cliente -> id_real (para medir precisión/recall)
Las cédulas, RUC, teléfonos y correos son inventados.
"""
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 11
N_BASE = 800
N_DUP = 120
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

NOMBRES = ["José", "Juan", "Carlos", "Luis", "Miguel", "Diego", "Rubén", "Derlis", "Gustavo",
           "María", "Ana", "Rosa", "Liz", "Karina", "Lorena", "Sofía", "Fabiola", "Natalia"]
APELLIDOS = ["González", "Benítez", "Martínez", "López", "Giménez", "Ortiz", "Romero", "Acosta",
             "Villalba", "Báez", "Cabrera", "Duarte", "Fretes", "Ayala", "Insfrán", "Rojas",
             "Torres", "Vera", "Escobar", "Cáceres", "Britez", "Samudio"]
CIUDADES = ["Asunción", "Fernando de la Mora", "Luque", "San Lorenzo", "Lambaré",
            "Capiatá", "Encarnación", "Ciudad del Este"]
VARIANTES_CIUDAD = {
    "Asunción": ["Asuncion", "ASUNCIÓN", "Asu", "asunción"],
    "Fernando de la Mora": ["Fdo. de la Mora", "FERNANDO DE LA MORA", "Fernando d.l. Mora"],
    "San Lorenzo": ["S. Lorenzo", "SAN LORENZO", "San lorenzo"],
    "Ciudad del Este": ["C. del Este", "CDE", "Ciudad Del Este"],
}
CALLES = ["Avenida Mariscal López", "Calle Palma", "Avenida Eusebio Ayala", "Calle Independencia",
          "Avenida España", "Calle Cerro Corá", "Avenida Madame Lynch"]


def dv_ruc(ci: int) -> int:
    total, k = 0, 2
    for d in reversed(str(ci)):
        total += int(d) * k
        k = k + 1 if k < 11 else 2
    resto = total % 11
    return 11 - resto if resto > 1 else 0


def sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def typo(t: str, rng) -> str:
    """Introduce un error de tipeo: omisión, duplicación o intercambio de letras."""
    if len(t) < 5:
        return t
    i = int(rng.integers(1, len(t) - 2))
    op = rng.choice(["omitir", "duplicar", "swap"])
    if op == "omitir":
        return t[:i] + t[i + 1:]
    if op == "duplicar":
        return t[:i] + t[i] + t[i:]
    return t[:i] + t[i + 1] + t[i] + t[i + 2:]


def main() -> None:
    rng = np.random.default_rng(SEED)
    cedulas = rng.choice(np.arange(1_000_000, 7_900_000), N_BASE, replace=False)
    nom = rng.choice(NOMBRES, N_BASE)
    nom2 = rng.choice(NOMBRES, N_BASE)
    ap1, ap2 = rng.choice(APELLIDOS, N_BASE), rng.choice(APELLIDOS, N_BASE)
    base = pd.DataFrame({
        "id_real": [f"R{i:05d}" for i in range(N_BASE)],
        "nombres": [f"{a} {b}" if rng.random() < 0.5 else a for a, b in zip(nom, nom2, strict=False)],
        "apellidos": [f"{a} {b}" for a, b in zip(ap1, ap2, strict=False)],
        "cedula": cedulas,
        "fecha_nacimiento": (pd.Timestamp("1950-01-01")
                             + pd.to_timedelta(rng.integers(0, 365 * 50, N_BASE), unit="D")),
        "telefono": rng.integers(971_000_000, 989_999_999, N_BASE),
        "ciudad": rng.choice(CIUDADES, N_BASE),
        "calle": rng.choice(CALLES, N_BASE),
        "nro": rng.integers(100, 4000, N_BASE),
        "fecha_alta": (pd.Timestamp("2018-01-01")
                       + pd.to_timedelta(rng.integers(0, 365 * 7, N_BASE), unit="D")),
    })

    # Duplicados: mismo cliente real cargado otra vez con errores
    dup = base.sample(N_DUP, random_state=SEED).copy()
    dup["fecha_alta"] = dup["fecha_alta"] + pd.to_timedelta(rng.integers(30, 900, N_DUP), unit="D")
    dup["nombres"] = [typo(v, rng) if rng.random() < 0.7 else v for v in dup["nombres"]]
    dup["apellidos"] = [typo(v, rng) if rng.random() < 0.5 else v for v in dup["apellidos"]]
    dup["_sin_ci"] = rng.random(N_DUP) < 0.40
    dup["_sin_fn"] = rng.random(N_DUP) < 0.08
    base["_sin_ci"] = False
    base["_sin_fn"] = False
    todo = pd.concat([base, dup], ignore_index=True)
    todo["id_cliente"] = [f"C{i:06d}" for i in range(1, len(todo) + 1)]

    # --- Formatos sucios --------------------------------------------------
    def fmt_nombre(r):
        n, a = r["nombres"], r["apellidos"]
        e = rng.random()
        if e < 0.20:
            return f"{a.upper()}, {n.upper()}"
        if e < 0.35:
            return f"{n} {a}".upper()
        if e < 0.45:
            return sin_acentos(f"{n} {a}").lower()
        return f"{n} {a}"

    def fmt_ci(v):
        e = rng.random()
        s = str(v)
        if e < 0.25:
            return f"{int(s):,}".replace(",", ".")
        if e < 0.30:
            return f" {s} "
        if e < 0.33:
            return "0"  # valor basura
        return s

    def fmt_tel(v):
        s = str(v)
        e = rng.random()
        if e < 0.25:
            return f"0{s[:3]} {s[3:6]} {s[6:]}"
        if e < 0.45:
            return f"+595{s}"
        if e < 0.60:
            return f"(0{s[:3]}) {s[3:]}"
        if e < 0.63:
            return s[:6]  # incompleto
        return f"0{s}"

    def fmt_ciudad(c):
        if c in VARIANTES_CIUDAD and rng.random() < 0.4:
            return rng.choice(VARIANTES_CIUDAD[c])
        return c

    def fmt_dir(r):
        calle = r["calle"]
        e = rng.random()
        if e < 0.25:
            calle = calle.replace("Avenida", "Avda.").replace("Calle", "C/")
        elif e < 0.40:
            calle = calle.upper()
        return f"{calle} {r['nro']}"

    def mk_email(r):
        e = rng.random()
        user = sin_acentos(r["nombres"].split()[0] + "." + r["apellidos"].split()[0]).lower()
        dom = rng.choice(["gmail.com", "hotmail.com", "outlook.com", "empresa.com.py"])
        if e < 0.20:
            return None
        if e < 0.25:
            return f"{user}{dom}"          # sin @
        if e < 0.30:
            return f"{user}@gmail"         # sin TLD
        return f"{user}@{dom}".upper() if e < 0.40 else f"{user}@{dom}"

    out = pd.DataFrame({
        "id_cliente": todo["id_cliente"],
        "nombre_completo": todo.apply(fmt_nombre, axis=1),
        "cedula": [None if sc else fmt_ci(v) for v, sc in zip(todo["cedula"], todo["_sin_ci"], strict=False)],
        "ruc": [f"{c}-{dv_ruc(c)}" if rng.random() < 0.55 else None for c in todo["cedula"]],
        "fecha_nacimiento": [None if sf else d.strftime("%Y-%m-%d")
                             for d, sf in zip(todo["fecha_nacimiento"], todo["_sin_fn"], strict=False)],
        "telefono": todo["telefono"].map(fmt_tel),
        "email": todo.apply(mk_email, axis=1),
        "direccion": todo.apply(fmt_dir, axis=1),
        "ciudad": todo["ciudad"].map(fmt_ciudad),
        "fecha_alta": todo["fecha_alta"].dt.strftime("%Y-%m-%d"),
    })
    # RUC con dígito verificador incorrecto (5% de los RUC presentes)
    mal = out.index[out["ruc"].notna() & (rng.random(len(out)) < 0.05)]
    out.loc[mal, "ruc"] = out.loc[mal, "ruc"].str[:-1] + "9"

    perm = rng.permutation(len(out))
    RAW.mkdir(parents=True, exist_ok=True)
    out.iloc[perm].to_csv(RAW / "clientes.csv", index=False)
    todo[["id_cliente", "id_real"]].to_csv(RAW / "clientes_ground_truth.csv", index=False)
    print(f"Generado {RAW/'clientes.csv'} -> {len(out):,} filas "
          f"({N_BASE} clientes reales + {N_DUP} duplicados)")


if __name__ == "__main__":
    main()
