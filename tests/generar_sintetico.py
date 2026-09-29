"""Genera una exportación sintética con la estructura real del ERP (sin datos reales).

Reproduce los patrones del extracto 2015–2017:
  - líneas de OC con una factura (lo más común);
  - caso A: una línea pagada con varias facturas ("Monto MN" de la línea se repite);
  - caso B: varias líneas iguales en una sola factura;
  - caso C: el total de la OC repetido en cada factura (como en la muestra);
  - OC en dólares, OC sin facturar, proveedores del exterior sin RUC.
Y siembra errores a propósito: filas idénticas, una factura en dos OC, "_x000D_",
descripciones y clases vacías, estados contradictorios y OC con facturado > monto.

Uso:
  python tests/generar_sintetico.py --filas 250000 --salida data/sintetico.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
COLUMNAS_REALES = [
    "", "Mes", "Fecha de OC", "N° de Orden de Compra", "Proveedor", "Sede", "Moneda", "Monto MN",
    "Monto ME", "TC de OC", "Nota", "Monto facturado", "Monto FA ME", "TC de FA", "N° de Factura",
    "Periodo Factura", "Estado Factura", "Empleado", "Supervisor", "Articulo", "Descripcion",
    "Concepto", "Departamento", "Clase", "ID Interno OC", "Estado de OC",
]


def generar(filas: int = 250_000, semilla: int = 42) -> tuple[pd.DataFrame, dict]:
    """Devuelve (DataFrame con columnas reales, dict con los casos sembrados)."""
    rng = np.random.default_rng(semilla)
    proveedores = [f"20{rng.integers(100000000, 999999999)} PROVEEDOR {i:04d} S.A.C." for i in range(1200)]
    proveedores += [f"EXTRANJERO {i} INC" for i in range(40)]
    sedes = [f"SEDE {i:02d}" for i in range(85)]
    personas = [f"PERSONA {i:02d}" for i in range(55)]
    articulos = ["Construccion", "Capacitación", "Pasajes", "Internet", "Ventas : Call Center",
                 "VENTAS : Materiales Adq. Alumnos", "Mantenimiento y Reparacion de Instalaciones",
                 "Suministros diversos", "Equipamiento", "Seguridad"]
    clases = ["Ampliaciones 2017", "Obras Nuevas 2018", "Gasto", "Gestion Interna", "Ventas"]
    fechas = pd.date_range("2015-01-01", "2017-12-31", freq="D")

    registros: list[list] = []
    oc_num = 10000
    siembras = {"filas_duplicadas": 0, "factura_en_dos_oc": 0}
    while len(registros) < filas:
        oc_num += 1
        prov = proveedores[rng.integers(len(proveedores))]
        fecha = fechas[rng.integers(len(fechas))]
        usd = rng.random() < 0.16
        tc = round(float(rng.uniform(3.2, 3.4)), 3) if usd else 1.0
        persona = personas[rng.integers(len(personas))]
        aprobador = persona if rng.random() < 0.94 else personas[rng.integers(len(personas))]
        comunes = dict(sede=sedes[rng.integers(len(sedes))], articulo=articulos[rng.integers(len(articulos))],
                       clase=None if rng.random() < 0.3 else clases[rng.integers(len(clases))])
        patron = rng.choice(["normal", "A", "B", "C", "sin_factura"], p=[0.70, 0.12, 0.08, 0.09, 0.01])
        n_fac = 0

        def factura():
            nonlocal n_fac
            n_fac += 1
            return f"FA {rng.integers(1, 999):04d}-{oc_num:06d}{n_fac}"

        def periodo(desfase):
            f = fecha + pd.DateOffset(months=int(desfase))
            return f"{MESES[f.month - 1]} {f.year}"

        lineas: list[tuple[float, float, str, str]] = []  # (monto_mn_fila, facturado, factura, periodo)
        if patron == "normal":
            fac = factura()
            for _ in range(int(rng.integers(1, 5))):
                m = round(float(rng.lognormal(7, 1.3)), 2)
                lineas.append((m, m, fac, periodo(rng.integers(0, 3))))
        elif patron == "A":
            m = round(float(rng.lognormal(8, 1.2)), 2)
            p = round(float(rng.uniform(0.1, 0.5)), 2)
            primero = round(m * p, 2)
            lineas.append((m, primero, factura(), periodo(1)))
            lineas.append((m, round(m - primero, 2), factura(), periodo(3)))
        elif patron == "B":
            fac = factura()
            m = round(float(rng.lognormal(6.5, 0.8)), 2)
            for _ in range(int(rng.integers(2, 6))):
                lineas.append((m, m, fac, periodo(1)))
        elif patron == "C":
            k = int(rng.integers(2, 7))
            total = round(float(rng.lognormal(10, 1.3)), 2)
            partes = np.round(np.full(k, total / k), 2)
            partes[-1] = round(total - partes[:-1].sum(), 2)
            for i in range(k):
                lineas.append((total, float(partes[i]), factura(), periodo(i + 1)))
        else:  # OC sin facturar
            m = round(float(rng.lognormal(7, 1)), 2)
            lineas.append((m, 0.0, None, None))

        pendiente = rng.random() < 0.02
        for m, fa, fac, per in lineas:
            desc = "AMPLIACION OBRA CIVIL_x000D_" if rng.random() < 0.13 else f"  SERVICIO {rng.integers(1, 5000)}"
            if rng.random() < 0.045:
                desc = None
            registros.append([
                fecha.year, fecha.month, fecha, oc_num, prov, comunes["sede"],
                "Dolares Americanos" if usd else "Soles",
                m, round(m / tc, 3) if usd else 0.0, tc, None if rng.random() < 0.06 else "nota libre",
                fa, round(fa / tc, 3) if usd else 0.0, tc if fac else None, fac, per,
                None if fac is None else ("Pendiente" if pendiente and rng.random() < 0.3 else "Pagado por completo"),
                persona, aprobador, comunes["articulo"], desc, "Mantenimiento", "CONST",
                comunes["clase"], 6_000_000 + oc_num,
                "Factura pendiente" if (pendiente or fac is None) else "Totalmente facturado",
            ])

    df = pd.DataFrame(registros[:filas], columns=COLUMNAS_REALES)

    # Siembra: filas idénticas (duplicados exactos).
    idx = rng.choice(len(df) - 1, size=50, replace=False)
    dup = df.iloc[idx]
    df = pd.concat([df.iloc[: filas - len(dup)], dup], ignore_index=True)
    siembras["filas_duplicadas"] = int(df.duplicated(keep=False).sum())

    # Siembra: una misma factura en dos OC distintas del mismo proveedor.
    # Se escribe con guion en vez de espacio para probar la normalización del N° de factura.
    con_fac = df.index[df["N° de Factura"].notna() & ~df.duplicated(keep=False)]
    i = con_fac[0]
    j = next(k for k in con_fac if df.at[k, "N° de Orden de Compra"] != df.at[i, "N° de Orden de Compra"])
    df.at[j, "Proveedor"] = df.at[i, "Proveedor"]
    df.at[j, "N° de Factura"] = str(df.at[i, "N° de Factura"]).replace(" ", "-")
    siembras["factura_en_dos_oc"] = {"oc": sorted([int(df.at[i, "N° de Orden de Compra"]),
                                                   int(df.at[j, "N° de Orden de Compra"])])}
    return df, siembras


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--filas", type=int, default=250_000)
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--salida", default="data/sintetico.csv", help=".csv o .xlsx")
    a = ap.parse_args()
    df, s = generar(a.filas, a.semilla)
    ruta = Path(a.salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.suffix.lower() == ".xlsx":
        df.to_excel(ruta, index=False)
    else:
        df.to_csv(ruta, index=False)
    print(f"{len(df):,} filas → {ruta} | siembras: {s}")


if __name__ == "__main__":
    main()
