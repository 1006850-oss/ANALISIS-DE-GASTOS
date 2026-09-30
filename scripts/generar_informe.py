"""Hilo 7 – Informe ejecutivo para el CEO (Excel, máximo 5 hojas).

Cada cifra del informe sale de las tablas de los Hilos 3 a 6 (diccionario CIFRAS con su fuente) y se verifica
automáticamente al final (`verificar_informe`). El texto es un BORRADOR redactado con IA para revisión humana.

Hojas: 1. Resumen · 2. Cumplimiento y anomalías · 3. Optimizar políticas · 4. Estrategias y plan · 5. Alcance y límites
Además genera informe_trazabilidad.xlsx (cada cifra, su valor y la tabla de origen).

Uso:
  python scripts/generar_informe.py --descriptivo <dir> --alertas <dir> --kraljic <dir> --plan <dir> \
         --periodo 2015-2017 --salida <carpeta>
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generar_excel import cargar_tablas  # noqa: E402

AZUL, GRIS = "2A78D6", "F0EFEC"


# --------------------------------------------------------------------------- formato de cifras

def f_m(x: float) -> str:
    return f"S/ {x / 1e6:,.1f} M".replace(",", " ")


def f_int(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", " ")


def f_pct(x: float) -> str:
    return f"{x:.1f} %"


class Cifras:
    """Registro de cifras: texto formateado + valor + fuente. El informe solo usa cifras registradas."""

    def __init__(self):
        self.d: dict[str, dict] = {}

    def add(self, clave: str, valor: float, formato, fuente: str) -> str:
        texto = formato(valor)
        self.d[clave] = {"cifra": clave, "texto": texto, "valor": float(valor), "fuente": fuente}
        return texto

    def __getitem__(self, clave: str) -> str:
        return self.d[clave]["texto"]

    def tabla(self) -> pd.DataFrame:
        return pd.DataFrame(self.d.values())


def calcular_cifras(T: dict[str, pd.DataFrame]) -> Cifras:
    c = Cifras()
    ctrl = T["desc.control"].set_index("control")["valor_soles"]
    c.add("gasto", float([v for k, v in ctrl.items() if k.startswith("Gasto analizado")][0]), f_m, "desc.control")
    p = T["desc.pareto_proveedores"]
    abc = T["desc.resumen_abc"].set_index("clase_abc")
    c.add("proveedores", len(p), f_int, "desc.pareto_proveedores (filas)")
    c.add("prov_a", abc.loc["A", "proveedores"], f_int, "desc.resumen_abc[A].proveedores")
    c.add("pct_gasto_a", abc.loc["A", "pct_gasto"], f_pct, "desc.resumen_abc[A].pct_gasto")
    fr = T["desc.frecuencia_proveedores"]
    c.add("prov_una_oc", (fr["n_oc"] == 1).sum(), f_int, "desc.frecuencia_proveedores (n_oc = 1)")
    c.add("pct_prov_una_oc", (fr["n_oc"] == 1).mean() * 100, f_pct, "desc.frecuencia_proveedores")
    anio = T["desc.tendencia_categoria_anio"].groupby("anio_gasto")["gasto"].sum()
    c.add("gasto_primer_anio", anio.iloc[0], f_m, f"desc.tendencia_categoria_anio[{anio.index[0]}]")
    c.add("gasto_ultimo_anio", anio.iloc[-1], f_m, f"desc.tendencia_categoria_anio[{anio.index[-1]}]")
    c.add("crecimiento", anio.iloc[-1] / anio.iloc[0], lambda x: f"×{x:.1f}", "desc.tendencia_categoria_anio")
    cat = T["desc.gasto_categoria"]
    c.add("pct_obras", cat.loc[cat["categoria"] == "Infraestructura y obras", "pct_gasto"].sum(), f_pct,
          "desc.gasto_categoria[Infraestructura y obras]")
    esp = T["desc.especializacion_comprador"]
    c.add("pct_top5_compradores", esp.head(5)["gasto"].sum() / esp["gasto"].sum() * 100, f_pct,
          "desc.especializacion_comprador (5 mayores)")
    # Alertas
    R = T["alert.resumen"]
    def res(alerta, subtipo=""):
        x = R[(R["alerta"].str.startswith(alerta)) & (R["subtipo"].fillna("") == subtipo)]
        return x.iloc[0] if len(x) else pd.Series({"casos": 0, "monto_soles": 0.0, "alta": 0})
    fr_ = res("1."); au = res("2.")
    c.add("frac_casos", fr_["casos"], f_int, "alert.resumen[1]"); c.add("frac_alta", fr_["alta"], f_int, "alert.resumen[1].alta")
    c.add("frac_monto", fr_["monto_soles"], f_m, "alert.resumen[1].monto_soles")
    c.add("frac_proveedores", T["alert.fraccionamiento"].get("proveedor_id", pd.Series(dtype=str)).nunique(), f_int, "alert.fraccionamiento")
    c.add("auto_oc", au["casos"], f_int, "alert.resumen[2]"); c.add("auto_monto", au["monto_soles"], f_m, "alert.resumen[2]")
    c.add("auto_alta", au["alta"], f_int, "alert.resumen[2].alta")
    niv = T["alert.autoaprobacion_por_nivel"]
    alto = niv[niv["nivel_aprobacion_oc"] >= 4]
    c.add("auto_n45", alto["autoaprobadas"].sum(), f_int, "alert.autoaprobacion_por_nivel[4-5].autoaprobadas")
    c.add("oc_n45", alto["oc"].sum(), f_int, "alert.autoaprobacion_por_nivel[4-5].oc")
    antes = res("4.", "Factura anterior a la OC")
    c.add("fact_antes_oc", antes["casos"], f_int, "alert.resumen[4 Factura anterior a la OC]")
    c.add("fact_antes_alta", antes["alta"], f_int, "alert.resumen[4 Factura anterior a la OC].alta")
    c.add("fact_antes_monto", antes["monto_soles"], f_m, "alert.resumen[4 Factura anterior a la OC]")
    exc = res("4.", "Facturado mayor al monto de la OC (+5 %)")
    c.add("excede_oc", exc["casos"], f_int, "alert.resumen[4 Facturado > OC]")
    c.add("excede_monto", exc["monto_soles"], f_m, "alert.resumen[4 Facturado > OC]")
    du = R[R["alerta"].str.startswith("3.")]
    c.add("dup_casos", du["casos"].sum(), f_int, "alert.resumen[3].casos")
    c.add("dup_alta", du["alta"].sum(), f_int, "alert.resumen[3].alta")
    c.add("dup_monto", du["monto_soles"].sum(), f_m, "alert.resumen[3].monto_soles")
    c.add("alertas_alta", R["alta"].sum(), f_int, "alert.resumen.alta (total)")
    ad_s = T["alert.adicionales_sede"]
    c.add("adic_monto", ad_s["gasto_adicionales"].sum(), f_m, "alert.adicionales_sede.gasto_adicionales")
    obras = ad_s["gasto_obras"].sum() if len(ad_s) else 0
    c.add("adic_pct", ad_s["gasto_adicionales"].sum() / obras * 100 if obras else 0, f_pct, "alert.adicionales_sede")
    c.add("adic_sedes", ad_s["alerta"].sum() if len(ad_s) else 0, f_int, "alert.adicionales_sede.alerta")
    c.add("adic_top_pct", ad_s["pct_adicionales"].max() if len(ad_s) else 0, f_pct,
          "alert.adicionales_sede.pct_adicionales (máximo)")
    conc = T["alert.concentracion_comprador"]
    c.add("conc_prov", len(conc), f_int, "alert.concentracion_comprador"); c.add("conc_monto", conc["gasto"].sum(), f_m,
                                                                             "alert.concentracion_comprador.gasto")
    c.add("giro", len(T["alert.giro_proveedor"]), f_int, "alert.giro_proveedor")
    # Plan
    pl = T["plan.plan_plan"]
    pp = pl[pl["segmento"] != "Por proyecto"]
    cons = pp[(pp["modalidad_si_se_consolida"] == "Licitación") & (pp["modalidad_por_oc_tipica"] != "Licitación")]
    c.add("cons_unidades", len(cons), f_int, "plan.plan_plan (consolidables)")
    c.add("cons_monto", cons["linea_base"].sum(), f_m, "plan.plan_plan.linea_base (consolidables)")
    c.add("cons_oc", cons["n_oc_ultimo_anio"].sum(), f_int, "plan.plan_plan.n_oc_ultimo_anio (consolidables)")
    c.add("plan_base", pp["linea_base"].sum(), f_m, "plan.plan_plan.linea_base (sin obras)")
    val = T["plan.plan_validacion"]
    v = val[val["metodo"].str.startswith("Gasto por sede") & val["segmento"].isin(["Recurrente", "Variable"])]
    cal = T["plan.plan_calendario"]
    ini = cal.loc[cal["segmento"] == "Recurrente", "inicio_proceso"].min()
    c.d["inicio_rec"] = {"cifra": "inicio_rec", "texto": ini.strftime("%d/%m/%Y") if pd.notna(ini) else "(sin dato)",
                         "valor": float("nan"), "fuente": "plan.plan_calendario[Recurrente].inicio_proceso (mínimo)"}
    c.add("plan_error", v["error_anual_pct"].abs().max() if len(v) else 0, f_pct, "plan.plan_validacion (máx. error anual)")
    # Kraljic
    kr = T["kraljic.kraljic_resumen"].set_index("cuadrante").reindex(
        ["Estratégico", "Apalancamiento", "Cuello de botella", "No crítico"]).fillna(0)
    for q, k in [("Estratégico", "est"), ("Apalancamiento", "apa"), ("Cuello de botella", "cue"), ("No crítico", "noc")]:
        c.add(f"kr_{k}_n", kr.loc[q, "unidades"], f_int, f"kraljic.kraljic_resumen[{q}].unidades")
        c.add(f"kr_{k}_pct", kr.loc[q, "pct_gasto"], f_pct, f"kraljic.kraljic_resumen[{q}].pct_gasto")
    return c


# --------------------------------------------------------------------------- contenido

def contenido(c: Cifras, T: dict[str, pd.DataFrame], periodo: str) -> dict[str, list]:
    """Cada hoja: lista de bloques (titulo, texto) o ('tabla', DataFrame)."""
    ku = T["kraljic.kraljic_unidades"]
    def principales(q, n=4):
        return ", ".join(ku[ku["cuadrante"] == q].nlargest(n, "gasto")["unidad"].str.replace("Obras › ", "", regex=False))
    fr = T["alert.fraccionamiento"]
    cols_fr = ["caso", "sede", "subcategoria", "n_oc", "dias", "suma_oc", "limite_superado", "prioridad"]
    if fr.empty:
        fr = pd.DataFrame(columns=cols_fr)
    top_fr = fr[fr["prioridad"] == "Alta"].sort_values("suma_oc", ascending=False).head(5)
    tabla_fr = pd.DataFrame({
        "Caso": top_fr["caso"], "Sede": top_fr["sede"], "Subcategoría": top_fr["subcategoria"],
        "N° OC": top_fr["n_oc"], "Días": top_fr["dias"], "Suma de OC": top_fr["suma_oc"].map(f_m),
        "Límite superado": top_fr["limite_superado"].map(lambda x: f"S/ {x:,.0f}".replace(",", " "))})
    senales = pd.DataFrame([
        ("Posibles compras fraccionadas", c["frac_casos"], c["frac_alta"], c["frac_monto"]),
        ("Autoaprobación (OC de nivel 2 o más)", c["auto_oc"], c["auto_alta"], c["auto_monto"]),
        ("Facturas anteriores a la OC", c["fact_antes_oc"], c["fact_antes_alta"], c["fact_antes_monto"]),
        ("Facturado mayor al monto de la OC (+5 %)", c["excede_oc"], "–", c["excede_monto"]),
        ("Posibles duplicados (facturas y filas)", c["dup_casos"], c["dup_alta"], c["dup_monto"]),
    ], columns=["Señal", "Casos", "Prioridad alta", "Monto"])
    kr_tab = pd.DataFrame([
        ("Estratégico", c["kr_est_n"], c["kr_est_pct"], principales("Estratégico"), "Contratos plurianuales, proveedor alternativo, plan de contingencia"),
        ("Apalancamiento", c["kr_apa_n"], c["kr_apa_pct"], principales("Apalancamiento"), "Licitar y consolidar volumen de todas las sedes"),
        ("Cuello de botella", c["kr_cue_n"], c["kr_cue_pct"], principales("Cuello de botella"), "Asegurar continuidad; trámites y renovaciones con anticipación"),
        ("No crítico", c["kr_noc_n"], c["kr_noc_pct"], principales("No crítico", 3), "Catálogos y compra delegada en sedes"),
    ], columns=["Cuadrante", "Unidades", "% gasto", "Principales", "Estrategia"])
    return {
        "1. Resumen": [
            ("Análisis de gastos de compras – Informe ejecutivo",
             f"Periodo {periodo} · soles nominales · BORRADOR redactado con IA para revisión · {date.today().isoformat()}"),
            ("Mensaje principal",
             f"El gasto analizado fue {c['gasto']} y creció {c['crecimiento']} entre el primer y el último año "
             f"({c['gasto_primer_anio']} → {c['gasto_ultimo_anio']}). Está muy concentrado: {c['prov_a']} proveedores "
             f"concentran el {c['pct_gasto_a']} del gasto y las obras representan el {c['pct_obras']}. Se detectaron "
             f"{c['alertas_alta']} señales de control de prioridad alta y una oportunidad de consolidar compras por "
             f"{c['cons_monto']} que hoy se hacen en {c['cons_oc']} órdenes pequeñas."),
            ("Tres decisiones que se proponen",
             f"1) Separar funciones: que el aprobador de la OC sea distinto del comprador desde el nivel 2 "
             f"(hoy {c['auto_oc']} OC de nivel 2 o más se registran como autoaprobadas, incluidas {c['auto_n45']} de "
             f"{c['oc_n45']} OC de niveles 4 y 5).\n"
             f"2) Consolidar {c['cons_unidades']} tipos de compra en procesos anuales (licitación o acuerdo marco), "
             f"con catálogo para las sedes.\n"
             f"3) Poner un tope y una aprobación previa a los adicionales de obra ({c['adic_pct']} del gasto en obras) "
             f"y revisar los {c['frac_alta']} casos de posible fraccionamiento de prioridad alta."),
            ("Indicadores clave", "tabla_kpi"),
        ],
        "2. Cumplimiento y anomalías": [
            ("Posibles incumplimientos de política y compras anómalas",
             "Son SEÑALES para revisar con los documentos; ninguna es una conclusión de irregularidad."),
            ("Resumen de señales", senales),
            ("Casos de fraccionamiento de mayor monto (prioridad alta)",
             f"{c['frac_casos']} casos en {c['frac_proveedores']} proveedores: OC del mismo proveedor, sede y subcategoría "
             "emitidas en 60 días que por separado quedan bajo un límite de aprobación y juntas lo superan."),
            ("Top 5", tabla_fr),
            ("Otras señales",
             f"Facturas con fecha anterior a su OC ({c['fact_antes_oc']}): posible regularización de compras ya hechas. "
             f"OC donde lo facturado supera el monto aprobado en más de 5 % ({c['excede_oc']}). "
             f"{c['giro']} proveedores facturan una parte relevante fuera de su rubro principal."),
        ],
        "3. Optimizar políticas": [
            ("Oportunidades para optimizar la política de compras", "Propuestas del análisis; requieren validación de la gerencia."),
            ("1. Consolidar compras",
             f"{c['cons_unidades']} tipos de compra ({c['cons_monto']}) se compraron en {c['cons_oc']} OC pequeñas por "
             "cotización, pero su volumen anual corresponde a licitación según la política. Proponer contratos anuales o "
             "acuerdos marco con catálogo (no aplica, por ejemplo, a alquileres de locales distintos)."),
            ("2. Reducir proveedores ocasionales",
             f"{c['prov_una_oc']} proveedores ({c['pct_prov_una_oc']}) tuvieron una sola OC: homologar y usar proveedores "
             "de catálogo."),
            ("3. Segregación de funciones y cadena de firmas",
             f"Registrar en el ERP todas las firmas que exige la política por nivel. Hoy la exportación trae un solo "
             f"aprobador y coincide con el comprador en {c['auto_oc']} OC de nivel 2 o más."),
            ("4. Control automático de fraccionamiento",
             "Bloqueo o alerta en el ERP cuando un mismo proveedor, sede y subcategoría acumula en 60 días un monto que "
             "supera el límite de aprobación."),
            ("5. OC antes de la compra", f"Prohibir OC posteriores a la factura salvo emergencia documentada ({c['fact_antes_oc']} casos)."),
            ("6. Adicionales de obra",
             f"Tope porcentual por contrato y aprobación previa. Adicionales: {c['adic_monto']} ({c['adic_pct']} del gasto "
             f"en obras); {c['adic_sedes']} sedes superan el 20 % y la mayor llega a {c['adic_top_pct']}."),
            ("7. Rotación de compradores",
             f"En {c['conc_prov']} proveedores clase A un solo comprador maneja el 90 % o más ({c['conc_monto']}); "
             f"los 5 compradores principales manejan el {c['pct_top5_compradores']} del gasto."),
        ],
        "4. Estrategias y plan": [
            ("Estrategias por tipo de compra (matriz de Kraljic)",
             "Cuadrantes PROVISIONALES: el riesgo usa una propuesta de IA hasta el taller de expertos."),
            ("Matriz", kr_tab),
            ("Plan de compras (línea base, ejercicio metodológico)",
             f"Línea base de compras recurrentes, variables y esporádicas: {c['plan_base']} (54 sedes, sin inflación). Error del método "
             f"en la validación hacia atrás: hasta {c['plan_error']} en el total anual. Las obras se toman del plan de obras "
             f"aprobado. Los procesos de las compras recurrentes deben iniciar el {c['inicio_rec']} para regir desde enero."),
        ],
        "5. Alcance y límites": [
            ("Alcance, límites y próximos pasos", ""),
            ("Alcance", f"Órdenes de compra y facturas del ERP, facturas {periodo}. Gasto = monto facturado (sin doble conteo)."),
            ("Límites",
             "Data hasta 2017. La exportación trae un solo aprobador por OC. La clasificación de productos tiene un acierto "
             "estimado de 84.5 % (categorías validadas por el usuario). Kraljic provisional hasta el taller. Plazos de las "
             "modalidades de compra: supuestos."),
            ("Próximos pasos",
             "1) Revisar las señales de prioridad alta con Auditoría Interna. 2) Taller de Kraljic con expertos. "
             "3) Decidir las políticas propuestas. 4) Correr el análisis con data reciente y repetirlo cada semestre."),
            ("Fuentes y trazabilidad", "Cada cifra de este informe está en informe_trazabilidad.xlsx con su tabla de origen."),
        ],
    }


def escribir_informe(bloques: dict[str, list], c: Cifras, ruta: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    for hoja, items in bloques.items():
        ws = wb.create_sheet(hoja[:31])
        ws.sheet_view.showGridLines = False
        ws.column_dimensions["A"].width = 30
        for col in "BCDEFG":
            ws.column_dimensions[col].width = 22
        fila = 1
        for k, (titulo, cuerpo) in enumerate(items):
            t = ws.cell(row=fila, column=1, value=titulo)
            t.font = Font(size=15 if k == 0 else 11, bold=True, color="0B0B0B" if k == 0 else AZUL)
            fila += 1
            if isinstance(cuerpo, pd.DataFrame):
                for j, col in enumerate(cuerpo.columns, start=1):
                    h = ws.cell(row=fila, column=j, value=col)
                    h.font, h.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor=AZUL)
                    h.alignment = Alignment(wrap_text=True)
                for r in cuerpo.itertuples(index=False):
                    fila += 1
                    for j, v in enumerate(r, start=1):
                        cel = ws.cell(row=fila, column=j, value=v.item() if hasattr(v, "item") else v)
                        cel.alignment = Alignment(wrap_text=True, vertical="top")
                fila += 2
            elif cuerpo == "tabla_kpi":
                kpis = [("Gasto analizado", c["gasto"]), ("Crecimiento primer → último año", c["crecimiento"]),
                        ("Proveedores / clase A", f"{c['proveedores']} / {c['prov_a']}"),
                        ("% del gasto en clase A", c["pct_gasto_a"]), ("% del gasto en obras", c["pct_obras"]),
                        ("Señales de control de prioridad alta", c["alertas_alta"]),
                        ("Compras consolidables", c["cons_monto"])]
                for etiqueta, valor in kpis:
                    ws.cell(row=fila, column=1, value=etiqueta).fill = PatternFill("solid", fgColor=GRIS)
                    v = ws.cell(row=fila, column=2, value=valor)
                    v.font = Font(bold=True, size=12)
                    fila += 1
                fila += 1
            else:
                cel = ws.cell(row=fila, column=1, value=cuerpo)
                ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=7)
                cel.alignment = Alignment(wrap_text=True, vertical="top")
                lineas = max(1, len(str(cuerpo)) // 150 + str(cuerpo).count("\n") + 1)
                ws.row_dimensions[fila].height = 15 * lineas
                fila += 2
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    ruta.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta)
    return ruta


# --------------------------------------------------------------------------- verificación

NUMERO = re.compile(r"(?:S/ )?\d[\d ]*(?:\.\d+)?(?: M| %)?|×\d+(?:\.\d+)?")


def textos_informe(ruta: Path) -> str:
    wb = load_workbook(ruta)
    return "\n".join(str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None)


def verificar_informe(ruta: Path, c: Cifras) -> list[str]:
    """Devuelve la lista de problemas: cifras registradas que no aparecen tal cual en el informe."""
    texto = textos_informe(ruta)
    return [f"Falta o fue alterada la cifra '{k}' = {v['texto']} (fuente: {v['fuente']})"
            for k, v in c.d.items() if v["texto"] not in texto]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Informe ejecutivo (Hilo 7).")
    for d in ["descriptivo", "alertas", "kraljic", "plan"]:
        ap.add_argument(f"--{d}", required=True)
    ap.add_argument("--periodo", required=True)
    ap.add_argument("--salida", required=True)
    a = ap.parse_args(argv)
    T = cargar_tablas({"desc": a.descriptivo, "alert": a.alertas, "kraljic": a.kraljic, "plan": a.plan})
    c = calcular_cifras(T)
    ruta = escribir_informe(contenido(c, T, a.periodo), c, Path(a.salida) / f"informe_ejecutivo_{a.periodo}.xlsx")
    c.tabla().to_excel(Path(a.salida) / "informe_trazabilidad.xlsx", index=False)
    problemas = verificar_informe(ruta, c)
    print("Generado:", ruta)
    print("Verificación de cifras:", "OK" if not problemas else f"{len(problemas)} problemas")
    for p in problemas:
        print(" -", p)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
