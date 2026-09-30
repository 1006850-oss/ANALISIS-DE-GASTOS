"""Hilo 6 – Plan de compras anual (línea base).

EJERCICIO METODOLÓGICO: la data termina en 2017 y el plan proyecta el año siguiente al histórico. La línea base
es un punto de partida que las personas ajustan con el plan de obras y el presupuesto; no es un pronóstico confiable.

Segmentos (por unidad de compra de Kraljic):
  - Por proyecto (Obras y terrenos): NO se proyecta; sale del plan de obras. Se entregan referencias históricas.
  - Recurrente: gasto por sede × sedes del plan, distribuido con el índice estacional propio.
  - Variable: gasto por sede × sedes del plan, distribuido con el índice estacional del grupo.
  - Esporádica: reserva anual sin detalle mensual.
Validación hacia atrás: se estima el último año de historia con el anterior y se mide el error por segmento.

Uso:
  python scripts/proyectar.py --tabla <tabla_clasificada.parquet> --kraljic <kraljic_unidades.parquet> --salida <carpeta>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analizar import filtrar_periodo  # noqa: E402
from clasificar import escribir_excel  # noqa: E402
from kraljic import cargar_yaml, preparar  # noqa: E402

PARAMETROS_DEFECTO = RAIZ / "config" / "parametros.yaml"
KRALJIC_DEFECTO = RAIZ / "config" / "kraljic.yaml"
PLAN_DEFECTO = RAIZ / "config" / "plan_compras.yaml"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
ESTRATEGIA_CORTA = {"Estratégico": "Contrato marco plurianual y proveedor alternativo precalificado",
                    "Apalancamiento": "Licitar y consolidar el volumen de todas las sedes",
                    "Cuello de botella": "Asegurar continuidad; iniciar trámites/renovaciones con anticipación",
                    "No crítico": "Catálogo o compra delegada en sedes"}


# --------------------------------------------------------------------------- base

def base_mensual(t: pd.DataFrame, P: dict) -> pd.DataFrame:
    """Matriz unidad × mes (gasto), con todos los meses de la historia."""
    anios = P["anios_historia"]
    mes = t["periodo_factura"].fillna(t["fecha_oc"]).dt.to_period("M")
    rango = pd.period_range(f"{anios[0]}-01", f"{anios[-1]}-12", freq="M")
    m = t.assign(_mes=mes).pivot_table(index="unidad", columns="_mes", values="monto_gasto", aggfunc="sum", fill_value=0)
    return m.reindex(columns=rango, fill_value=0.0)


def sedes_activas(t: pd.DataFrame, P: dict) -> pd.Series:
    x = t[t["categoria"] == P["sedes"]["categoria_referencia"]]
    return x.groupby("anio_gasto")["sede"].nunique().reindex(P["anios_historia"])


def segmentar(m: pd.DataFrame, categoria: pd.Series, P: dict) -> pd.DataFrame:
    S = P["segmentacion"]
    activos = (m > 0).sum(axis=1)
    cv = m.std(axis=1) / m.mean(axis=1).replace(0, np.nan)
    proyecto = categoria.reindex(m.index).isin(S["categorias_proyecto"]) | m.index.isin(S["unidades_proyecto"])
    recurrente = ~proyecto & (activos >= S["recurrente_meses_minimos"]) & (cv <= S["recurrente_cv_maximo"])
    esporadica = ~proyecto & ~recurrente & (activos <= S["esporadica_meses_maximos"])
    seg = np.select([proyecto, recurrente, esporadica], ["Por proyecto", "Recurrente", "Esporádica"], "Variable")
    return pd.DataFrame({"segmento": seg, "meses_activos": activos, "cv_mensual": cv}, index=m.index)


def anual(m: pd.DataFrame) -> pd.DataFrame:
    return m.T.groupby(m.columns.year).sum().T


def indice_estacional(m: pd.DataFrame) -> pd.DataFrame:
    """Participación de cada mes calendario en el gasto de la historia (suma 1)."""
    x = m.T.groupby(m.columns.month).sum().T
    tot = x.sum(axis=1).replace(0, np.nan)
    return x.div(tot, axis=0).fillna(1 / 12)


def modalidad(monto: float, modalidades: list[dict]) -> tuple[str, int]:
    for mod in modalidades:
        if mod["hasta_pen"] is None or monto <= mod["hasta_pen"]:
            return mod["nombre"], mod["plazo_semanas"]
    return modalidades[-1]["nombre"], modalidades[-1]["plazo_semanas"]


# --------------------------------------------------------------------------- validación hacia atrás

def validacion_atras(m: pd.DataFrame, seg: pd.DataFrame, sedes: pd.Series, P: dict) -> pd.DataFrame:
    """Estima el último año con el anterior (por sede y por tendencia) y mide el error por segmento."""
    a = anual(m)
    anios = P["anios_historia"]
    ult, prev, prev2 = anios[-1], anios[-2], anios[-3] if len(anios) >= 3 else None
    filas = []
    for s in ["Recurrente", "Variable", "Esporádica"]:
        u = seg.index[seg["segmento"] == s]
        if len(u) == 0:
            continue
        real = a.loc[u, ult].sum()
        por_sede = a.loc[u, prev].sum() / sedes[prev] * sedes[ult]
        tendencia = a.loc[u, prev] .sum() + (a.loc[u, prev].sum() - a.loc[u, prev2].sum()) if prev2 else np.nan
        ultimo = a.loc[u, prev].sum()
        idx = indice_estacional(m[[c for c in m.columns if c.year < ult]].loc[u].sum().to_frame().T)
        mens_real = m.loc[u, [c for c in m.columns if c.year == ult]].sum().to_numpy()
        for metodo, est in [("Gasto por sede (principal)", por_sede), ("Tendencia lineal (comparación)", tendencia),
                            ("Repetir el último año", ultimo)]:
            mens = est * idx.to_numpy().ravel()
            con = mens_real > 0
            mape = float(np.mean(np.abs(mens[con] - mens_real[con]) / mens_real[con]) * 100) if con.any() else np.nan
            filas.append({"segmento": s, "metodo": metodo, "anio_validado": ult, "real": real, "estimado": est,
                          "error_anual_pct": (est - real) / real * 100 if real else np.nan, "mape_mensual_pct": mape})
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------- plan

def plan_compras(t_completa: pd.DataFrame, kraljic_u: pd.DataFrame | None, params: dict, K: dict, P: dict) -> dict:
    t = preparar(t_completa, params, K)
    m = base_mensual(t, P)
    categoria = t.groupby("unidad")["categoria"].first()
    seg = segmentar(m, categoria, P)
    sedes = sedes_activas(t, P)
    a = anual(m)
    ult = P["anios_historia"][-1]
    factor_sedes = P["sedes"]["plan"] / sedes[ult]
    infl = 1 + P["inflacion_anual"]
    val = validacion_atras(m, seg, sedes, P)
    error = val[val["metodo"].str.startswith("Gasto por sede")].set_index("segmento")["error_anual_pct"].abs()

    idx_propio = indice_estacional(m)
    idx_grupo = {s: indice_estacional(m.loc[seg.index[seg["segmento"] == s]].sum().to_frame().T).iloc[0]
                 for s in ["Recurrente", "Variable"] if (seg["segmento"] == s).any()}

    # Tamaño típico de OC por unidad en el último año (para sugerir modalidad por OC)
    oc_ult = t[t["anio_gasto"] == ult].groupby(["unidad", "oc"])["monto_gasto"].sum().reset_index()
    oc_tipica = oc_ult.groupby("unidad")["monto_gasto"].median()
    n_oc = oc_ult.groupby("unidad")["oc"].nunique()
    cuad = kraljic_u.set_index("unidad")["cuadrante"] if kraljic_u is not None else pd.Series(dtype=str)
    estado_k = kraljic_u.set_index("unidad")["estado"] if kraljic_u is not None else pd.Series(dtype=str)
    mods = P["modalidades"]

    filas, meses = [], []
    for u, r in seg.iterrows():
        s = r["segmento"]
        hist = {f"gasto_{y}": float(a.loc[u, y]) for y in P["anios_historia"]}
        tendencia = a.loc[u, ult] + (a.loc[u, ult] - a.loc[u, ult - 1])
        if s == "Por proyecto":
            base, metodo = np.nan, "Plan de obras aprobado (sin proyección automática)"
        else:
            base = float(a.loc[u, ult] * factor_sedes * infl)
            metodo = "Reserva anual (gasto por sede × sedes)" if s == "Esporádica" else "Gasto por sede × sedes del plan"
        e = error.get(s, np.nan) / 100
        mod_oc, _ = modalidad(float(oc_tipica.get(u, 0)), mods)
        mod_anual, plazo = modalidad(base if pd.notna(base) else float(a.loc[u, ult]), mods)
        if s == "Por proyecto":
            plazo = P["plazo_licitacion_obras_semanas"]
        filas.append({
            "unidad": u, "categoria": categoria[u], "segmento": s, "cuadrante_kraljic": cuad.get(u, ""),
            "estado_kraljic": estado_k.get(u, ""), **hist,
            "linea_base": base, "rango_min": base * (1 - e) if pd.notna(base) and pd.notna(e) else np.nan,
            "rango_max": base * (1 + e) if pd.notna(base) and pd.notna(e) else np.nan,
            "tendencia_comparacion": float(max(tendencia, 0)) if s != "Por proyecto" else np.nan,
            "metodo": metodo, "n_oc_ultimo_anio": int(n_oc.get(u, 0)), "oc_tipica": float(oc_tipica.get(u, 0)),
            "modalidad_por_oc_tipica": mod_oc, "modalidad_si_se_consolida": mod_anual, "plazo_semanas": plazo,
            "estrategia_kraljic": ESTRATEGIA_CORTA.get(cuad.get(u, ""), ""),
            "meses_activos": int(r["meses_activos"]), "cv_mensual": r["cv_mensual"],
            "Monto ajustado": "", "Fuente del ajuste (plan de obras / presupuesto / otro)": "", "Comentario": ""})
        if s in ("Recurrente", "Variable"):
            idx = idx_propio.loc[u] if s == "Recurrente" else idx_grupo[s]
            for mes in range(1, 13):
                meses.append({"unidad": u, "segmento": s, "mes": mes, "mes_nombre": MESES[mes - 1],
                              "linea_base": base * float(idx[mes])})
    plan = pd.DataFrame(filas).sort_values(["segmento", "gasto_%d" % ult], ascending=[True, False]).reset_index(drop=True)
    mensual = pd.DataFrame(meses)
    pivote = (mensual.pivot_table(index="unidad", columns="mes", values="linea_base", aggfunc="sum")
              .rename(columns=lambda c: MESES[c - 1]) if len(mensual) else pd.DataFrame())
    return {"plan": plan, "mensual": mensual, "pivote": pivote, "validacion": val, "segmentos": seg.reset_index(),
            "sedes": sedes.rename("sedes_activas").reset_index(), "calendario": calendario(plan, mensual, P),
            "obras": referencias_obras(t, m, seg, P)}


def calendario(plan: pd.DataFrame, mensual: pd.DataFrame, P: dict) -> pd.DataFrame:
    """Cuándo iniciar cada proceso: el contrato debe estar listo en el mes de necesidad."""
    C = P["calendario"]
    anio = P["anio_plan"]
    pico = (mensual.sort_values(["unidad", "linea_base"], ascending=[True, False]).drop_duplicates("unidad")
            .set_index("unidad")["mes"]) if len(mensual) else pd.Series(dtype=int)
    filas = []
    for _, r in plan.iterrows():
        if r["segmento"] == "Recurrente":
            mes, motivo = C["mes_inicio_contratos_anuales"], "Contrato anual vigente desde enero"
        elif r["segmento"] == "Por proyecto":
            mes, motivo = C["inicio_anio_escolar_mes"], "Según plan de obras (referencia: obras listas antes de marzo)"
        elif r["segmento"] == "Variable":
            mes, motivo = int(pico.get(r["unidad"], C["inicio_anio_escolar_mes"])), "Mes de mayor gasto histórico"
        else:
            mes, motivo = None, "Reserva anual: comprar cuando surja la necesidad"
        if mes is None:
            inicio = pd.NaT
        else:
            necesidad = pd.Timestamp(anio, mes, 1)
            inicio = necesidad - pd.Timedelta(weeks=int(r["plazo_semanas"]))
        filas.append({"unidad": r["unidad"], "segmento": r["segmento"], "cuadrante_kraljic": r["cuadrante_kraljic"],
                      "modalidad_si_se_consolida": r["modalidad_si_se_consolida"], "plazo_semanas": r["plazo_semanas"],
                      "mes_necesidad": MESES[mes - 1] if mes else "", "inicio_proceso": inicio,
                      "motivo": motivo, "linea_base": r["linea_base"]})
    return (pd.DataFrame(filas).sort_values(["inicio_proceso", "linea_base"], ascending=[True, False], na_position="last")
            .reset_index(drop=True))


def referencias_obras(t: pd.DataFrame, m: pd.DataFrame, seg: pd.DataFrame, P: dict) -> pd.DataFrame:
    u = seg.index[seg["segmento"] == "Por proyecto"]
    a = anual(m.loc[u])
    idx = indice_estacional(m.loc[u])
    obras_total = a.sum()
    civil = a.loc[a.index.str.endswith("Obra civil")].sum() if a.index.str.endswith("Obra civil").any() else np.nan
    r = pd.DataFrame(index=u)
    for y in P["anios_historia"]:
        r[f"gasto_{y}"] = a[y]
    r["pct_del_total_proyecto"] = a.sum(axis=1) / obras_total.sum() * 100
    if isinstance(civil, pd.Series):
        r["ratio_sobre_obra_civil_pct"] = a.sum(axis=1) / civil.sum() * 100
    r["meses_de_mayor_gasto"] = idx.apply(lambda s: ", ".join(MESES[k - 1] for k in s.nlargest(3).index), axis=1)
    return r.sort_values("pct_del_total_proyecto", ascending=False).reset_index().rename(columns={"index": "unidad"})


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Plan de compras anual – línea base (Hilo 6).")
    ap.add_argument("--tabla", required=True)
    ap.add_argument("--kraljic", help="tablas/kraljic_unidades.parquet del Hilo 5 (opcional)")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--parametros", default=str(PARAMETROS_DEFECTO))
    ap.add_argument("--config-kraljic", default=str(KRALJIC_DEFECTO))
    ap.add_argument("--config-plan", default=str(PLAN_DEFECTO))
    a = ap.parse_args(argv)
    params, K, P = cargar_yaml(a.parametros), cargar_yaml(a.config_kraljic), cargar_yaml(a.config_plan)
    ku = pd.read_parquet(a.kraljic) if a.kraljic else None
    r = plan_compras(pd.read_parquet(a.tabla), ku, params, K, P)
    carpeta = Path(a.salida)
    (carpeta / "tablas").mkdir(parents=True, exist_ok=True)
    for k in ["plan", "mensual", "validacion", "calendario", "obras"]:
        r[k].to_parquet(carpeta / "tablas" / f"plan_{k}.parquet", index=False)
    nota = pd.DataFrame({"Nota": [
        f"PLAN DE COMPRAS {P['anio_plan']} – EJERCICIO METODOLÓGICO: la data termina en {P['anios_historia'][-1]}.",
        "La línea base es un punto de partida; se ajusta con el plan de obras y el presupuesto (columnas de ajuste).",
        f"Método principal: gasto por sede × {P['sedes']['plan']} sedes. Soles nominales (sin inflación).",
        "Obras y terrenos NO se proyectan: se toman del plan de obras (ver hoja Obras_referencias).",
        "Modalidades según la política interna; plazos = SUPUESTOS a reemplazar por los reales.",
        "Cuadrantes de Kraljic provisionales mientras no se haga el taller de expertos."]})
    escribir_excel(carpeta / "plan_compras.xlsx", {
        "Notas": nota, "Plan_anual": r["plan"], "Plan_mensual": r["pivote"].reset_index() if len(r["pivote"]) else r["pivote"],
        "Calendario_procesos": r["calendario"], "Obras_referencias": r["obras"], "Validacion_atras": r["validacion"],
        "Segmentos": r["segmentos"], "Sedes_activas": r["sedes"]})
    p = r["plan"]
    print(p.groupby("segmento").agg(unidades=("unidad", "size"), linea_base=("linea_base", "sum"),
                                     gasto_ult=(f"gasto_{P['anios_historia'][-1]}", "sum")).round(0).to_string())
    print(r["validacion"].round(1).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
