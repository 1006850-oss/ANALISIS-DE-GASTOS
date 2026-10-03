"""Hilo 8 – Orquestador del ciclo semestral: ejecuta todo el flujo con un solo comando.

  python scripts/ejecutar_ciclo.py --entrada <exportación del ERP.xlsx> --periodo 2026-S2 [--raiz <carpeta de Drive>]

Orden: 1 limpiar y validar → 2 clasificar → 3 analizar → 4 alertas → 5 Kraljic → 6 plan (solo S2)
       → 7 Excel, tablero e informe → 8 histórico y comparación con el ciclo anterior.

Puntos de parada humanos (el orquestador guarda el estado y termina con código 3; al volver a ejecutarlo con el
mismo --periodo continúa desde donde quedó):
  - una validación BLOQUEA en la limpieza (código 2: hay que corregir la exportación y usar --reiniciar);
  - hay artículos o combinaciones nuevas sin validar → llenar 2_clasificacion/validar_nuevas.xlsx y reanudar con
    --validacion <archivo> (o --aceptar-propuestas para aceptar lo que proponen las reglas);
  - los puntajes de riesgo de Kraljic no están confirmados por el taller → reanudar con --taller <archivo> o
    --kraljic-provisional (decisión que queda registrada).

Estructura de la raíz (carpeta "analisis de gastos" de Drive, ver config/parametros.yaml > rutas):
  maestro/   maestro_categorias.xlsx, codigos_personas.xlsx, kraljic_taller_completado.xlsx (cambian cada ciclo)
  salida/<periodo>/   1_limpieza … 8_historico, estado.json, log_ejecucion.md
  historico/          un subcarpeta por ciclo (ver historico.py)

La consola y el log NO muestran nombres de personas, RUC ni descripciones: solo conteos, montos y rutas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import yaml

RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import alertas as al  # noqa: E402
import analizar as an  # noqa: E402
import clasificar as cl  # noqa: E402
import generar_excel as ge  # noqa: E402
import generar_informe as gi  # noqa: E402
import historico as hi  # noqa: E402
import kraljic as kr  # noqa: E402
import limpiar_validar as lv  # noqa: E402
import proyectar as pr  # noqa: E402

PASOS = ["1_limpieza", "2_clasificacion", "3_descriptivo", "4_alertas", "5_kraljic", "6_plan", "7_salidas",
         "8_historico"]
NOMBRES = {"1_limpieza": "Limpiar y validar", "2_clasificacion": "Clasificar", "3_descriptivo": "Analizar",
           "4_alertas": "Alertas", "5_kraljic": "Kraljic", "6_plan": "Plan de compras",
           "7_salidas": "Excel, tablero e informe", "8_historico": "Histórico y comparación"}
OK, PAUSA, BLOQUEO, ERROR = 0, 3, 2, 1


LOCAL = RAIZ_REPO / "config" / "local.yaml"   # ruta de Drive de ESTE equipo (no se versiona; ver preparar_equipo.py)


def raiz_local() -> str | None:
    """Carpeta raíz de datos guardada para este equipo en config/local.yaml (si existe)."""
    if LOCAL.exists():
        return (yaml.safe_load(LOCAL.read_text(encoding="utf-8")) or {}).get("raiz_datos")
    return None


class Pausa(Exception):
    """Punto de parada humano: el ciclo espera una decisión o una validación."""

    def __init__(self, mensaje: str, codigo: int = PAUSA):
        super().__init__(mensaje)
        self.codigo = codigo


# --------------------------------------------------------------------------- utilidades

def semestre_menos(periodo: str, n: int) -> str:
    anio, s = int(periodo[:4]), int(periodo[-1])
    idx = anio * 2 + (s - 1) - n
    return f"{idx // 2}-S{idx % 2 + 1}"


def ventana(periodo: str, C: dict) -> tuple[str, str]:
    desde = semestre_menos(periodo, C["semestres_ventana"] - 1)
    return max(desde, C["periodo_minimo"]), periodo


def version_yaml(ruta: Path) -> str:
    """Versión declarada en un YAML (clave `version` o comentario '# Versión: …')."""
    texto = ruta.read_text(encoding="utf-8")
    try:
        v = (yaml.safe_load(texto) or {}).get("version")
    except yaml.YAMLError:
        v = None
    if v:
        return str(v)
    for linea in texto.splitlines()[:10]:
        if "Versión:" in linea:
            return linea.split("Versión:")[1].strip()
    return "(sin versión)"


def huella(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()[:12]


def commit_repo() -> str:
    """Commit del repositorio; dentro de la skill empaquetada, la versión de VERSION.txt."""
    ver = RAIZ_REPO / "VERSION.txt"
    if ver.exists():
        return "skill " + ver.read_text(encoding="utf-8").strip()
    try:
        c = subprocess.run(["git", "-C", str(RAIZ_REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                           text=True, check=True).stdout.strip()
        sucio = subprocess.run(["git", "-C", str(RAIZ_REPO), "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True).stdout.strip()
        return c + (" (con cambios sin commit)" if sucio else "")
    except (OSError, subprocess.CalledProcessError):
        return "(sin git: versión de la skill)"


def _m(x: float) -> str:
    return f"S/ {x:,.2f}"


# --------------------------------------------------------------------------- ciclo

class Ciclo:
    def __init__(self, a: argparse.Namespace):
        self.a = a
        self.params = lv.cargar_parametros(a.parametros)
        self.C = self.params["ciclo"]
        R = self.params["rutas"]
        self.raiz = Path(a.raiz or raiz_local() or R["raiz_datos"])
        if not self.raiz.exists():
            raise SystemExit(f"No existe la carpeta raíz de datos: {self.raiz}. Configure el equipo con "
                             "'python scripts/preparar_equipo.py --raiz <carpeta de Drive>' o use --raiz.")
        self.dir = self.raiz / R["salida"] / a.periodo
        self.maestro_dir = self.raiz / R["maestro"]
        self.historico = self.raiz / R["historico"]
        self.maestro = Path(a.maestro) if a.maestro else self.maestro_dir / self.C["maestro_archivo"]
        self.codigos = self.maestro_dir / self.C["codigos_archivo"]
        if a.reiniciar and self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ruta_estado = self.dir / "estado.json"
        self.estado = json.loads(self.ruta_estado.read_text(encoding="utf-8")) if self.ruta_estado.exists() else {
            "periodo": a.periodo, "creado": datetime.now().isoformat(timespec="seconds"), "pasos": {},
            "decisiones": [], "advertencias": [], "cuadres": []}
        self.desde, self.hasta = ventana(a.periodo, self.C)

    # ------------------------------------------------------------- estado y log
    def guardar(self) -> None:
        self.ruta_estado.write_text(json.dumps(self.estado, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        self.escribir_log()

    def decision(self, texto: str) -> None:
        self.estado["decisiones"].append(f"{datetime.now():%Y-%m-%d %H:%M} – {texto}")

    def paso(self, clave: str) -> dict:
        return self.estado["pasos"].setdefault(clave, {"estado": "pendiente"})

    def invalidar_desde(self, clave: str) -> None:
        for p in PASOS[PASOS.index(clave):]:
            if p in self.estado["pasos"]:
                self.estado["pasos"][p]["estado"] = "pendiente"

    def escribir_log(self) -> None:
        e = self.estado
        v = e.get("versiones", {})
        L = [f"# Bitácora de ejecución – ciclo {e['periodo']}", "",
             f"- Creado: {e['creado']} · última actualización: {datetime.now():%Y-%m-%d %H:%M:%S}",
             f"- Entrada: {e.get('entrada', {}).get('nombre', '')} (huella {e.get('entrada', {}).get('huella', '')})",
             f"- Ventana analizada: {self.desde} a {self.hasta}",
             f"- Código (commit): {v.get('codigo', '')}",
             f"- Parámetros: {v.get('parametros', '')} · reglas de taxonomía: {v.get('reglas_taxonomia', '')} · "
             f"reglas de alertas: {v.get('reglas_alertas', '')} · Kraljic: {v.get('kraljic', '')} · "
             f"plan: {v.get('plan', '')}",
             f"- Maestro de categorías: {v.get('maestro', '')}", "",
             "## Pasos", "", "| Paso | Estado | Inicio | Duración (s) | Nota |", "|---|---|---|---|---|"]
        for p in PASOS:
            x = e["pasos"].get(p, {"estado": "pendiente"})
            L.append(f"| {p} {NOMBRES[p]} | {x['estado']} | {x.get('inicio', '')} | {x.get('duracion_s', '')} | "
                     f"{x.get('nota', '')} |")
        L += ["", "## Cuadres", ""] + ([f"- {c}" for c in e["cuadres"]] or ["- (aún no calculados)"])
        L += ["", "## Advertencias", ""] + ([f"- {c}" for c in e["advertencias"]] or ["- Ninguna"])
        L += ["", "## Decisiones humanas registradas", ""] + ([f"- {c}" for c in e["decisiones"]] or ["- Ninguna"])
        if e.get("pausa"):
            L += ["", "## ⏸ Punto de parada", "", e["pausa"]]
        (self.dir / "log_ejecucion.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ------------------------------------------------------------- ejecución
    def ejecutar(self) -> int:
        entrada = Path(self.a.entrada)
        if not entrada.exists():
            print(f"No existe el archivo de entrada: {entrada}", file=sys.stderr)
            return ERROR
        hu = huella(entrada)
        previa = self.estado.get("entrada", {}).get("huella")
        if previa and previa != hu:
            print("La entrada cambió respecto de la ejecución guardada de este ciclo. Use --reiniciar para empezar "
                  "de nuevo.", file=sys.stderr)
            return ERROR
        self.estado["entrada"] = {"nombre": entrada.name, "huella": hu}
        self.estado["versiones"] = {
            "codigo": commit_repo(), "parametros": version_yaml(Path(self.a.parametros)),
            "reglas_taxonomia": version_yaml(RAIZ_REPO / "config" / "reglas_taxonomia.yaml"),
            "reglas_alertas": version_yaml(RAIZ_REPO / "config" / "reglas_alertas.yaml"),
            "kraljic": version_yaml(RAIZ_REPO / "config" / "kraljic.yaml"),
            "plan": version_yaml(RAIZ_REPO / "config" / "plan_compras.yaml"),
            "maestro": self.version_maestro()}
        self.estado.pop("pausa", None)
        self.escribir_parametros_ciclo()
        print(f"Ciclo {self.a.periodo} · ventana {self.desde} a {self.hasta} · carpeta {self.dir}")
        for clave in PASOS:
            x = self.paso(clave)
            if x["estado"] in ("ok", "omitido"):
                print(f"  ✔ {clave} {NOMBRES[clave]} (ya hecho)")
                continue
            x.update(estado="en curso", inicio=datetime.now().strftime("%H:%M:%S"))
            self.guardar()
            t0 = time.perf_counter()
            try:
                nota = getattr(self, "p" + clave[0])()
                x.update(estado="omitido" if nota and nota.startswith("No aplica") else "ok", nota=nota or "")
            except Pausa as p:
                x.update(estado="PAUSA" if p.codigo == PAUSA else "BLOQUEADO", nota="ver punto de parada")
                self.estado["pausa"] = str(p)
                x["duracion_s"] = round(time.perf_counter() - t0, 1)
                self.guardar()
                print(f"\n⏸ PUNTO DE PARADA en {clave} {NOMBRES[clave]}:\n{p}\n\nEstado guardado en {self.ruta_estado}")
                return p.codigo
            except Exception as ex:  # noqa: BLE001
                x.update(estado="ERROR", nota=f"{type(ex).__name__}: {ex}"[:300])
                x["duracion_s"] = round(time.perf_counter() - t0, 1)
                self.guardar()
                print(f"\n✖ ERROR en {clave}: {type(ex).__name__}: {ex}", file=sys.stderr)
                return ERROR
            x["duracion_s"] = round(time.perf_counter() - t0, 1)
            self.guardar()
            print(f"  ✔ {clave} {NOMBRES[clave]} ({x['duracion_s']} s) {x['nota']}")
        print(f"\nCiclo {self.a.periodo} completo. Bitácora: {self.dir / 'log_ejecucion.md'}")
        return OK

    def version_maestro(self) -> str:
        if not self.maestro.exists():
            return "(no existe)"
        mt = datetime.fromtimestamp(self.maestro.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        return f"{self.maestro.name} · modificado {mt} · huella {huella(self.maestro)}"

    def escribir_parametros_ciclo(self) -> None:
        p = json.loads(json.dumps(self.params))
        p["analisis"]["periodo_desde"], p["analisis"]["periodo_hasta"] = self.desde, self.hasta
        self.params_ciclo = self.dir / "parametros_ciclo.yaml"
        self.params_ciclo.write_text("# Copia de config/parametros.yaml con la ventana de este ciclo (generada).\n"
                                     + yaml.safe_dump(p, allow_unicode=True, sort_keys=False), encoding="utf-8")
        self.params = p

    def d(self, clave: str) -> Path:
        return self.dir / clave

    # ------------------------------------------------------------- 1 limpieza
    def p1(self) -> str:
        crudo = lv.leer_entrada(self.a.entrada)
        previos = pd.read_excel(self.codigos, dtype=str) if self.codigos.exists() else None
        res = lv.procesar(crudo, self.params, None, previos)
        if self.a.simular_corte and res.tabla is not None:
            fin = pd.Period(f"{self.hasta[:4]}-{6 if self.hasta.endswith('1') else 12}", "M").to_timestamp(how="end")
            t = res.tabla
            fecha = t["periodo_factura"].fillna(t["fecha_oc"])
            antes = len(t)
            res.tabla = t[fecha <= fin].reset_index(drop=True)
            self.decision(f"SIMULACIÓN: se usan solo las filas con factura (u OC) hasta {self.hasta} "
                          f"({len(res.tabla):,} de {antes:,} filas).")
        lv.guardar(res, self.d("1_limpieza"), self.params, self.a.entrada, self.a.periodo)
        v = res.validaciones
        for _, r in v[(v["estado"] == "FALLA") & (v["nivel"] != lv.BLOQUEA)].iterrows():
            self.estado["advertencias"].append(f"[{r['n']}] {r['validacion']}: {r['detalle']}")
        if res.bloqueado:
            fallas = v[(v["estado"] == "FALLA") & (v["nivel"] == lv.BLOQUEA)]
            lista = "\n".join(f"  - [{r['n']}] {r['validacion']}: {r['detalle']}" for _, r in fallas.iterrows())
            raise Pausa("Una validación BLOQUEA el proceso (la data no es confiable para seguir):\n" + lista +
                        "\nQué hacer: corrija la exportación del ERP (o el mapeo de columnas en config/parametros.yaml)"
                        " y vuelva a ejecutar con --reiniciar. Detalle en 1_limpieza/reporte_calidad.xlsx.", BLOQUEO)
        # Códigos de personas: se conservan y se agregan los nuevos (tabla solo en Drive: tiene nombres).
        self.maestro_dir.mkdir(parents=True, exist_ok=True)
        nuevos = len(res.codigos) - (len(previos) if previos is not None else 0)
        res.codigos.to_excel(self.codigos, index=False)
        t = res.tabla
        self.estado["cuadres"].append(f"Limpieza: {len(crudo):,} filas leídas; gasto de la tabla limpia "
                                      f"{_m(t['monto_gasto'].sum())}; control de totales OK")
        return f"{len(t):,} filas, {t['oc'].nunique():,} OC; {nuevos} códigos de persona nuevos"

    # ------------------------------------------------------------- 2 clasificación
    def p2(self) -> str:
        d = self.d("2_clasificacion")
        d.mkdir(parents=True, exist_ok=True)
        if not self.maestro.exists():
            raise Pausa(f"No existe el maestro de categorías en {self.maestro}. Cópielo a la carpeta 'maestro' de "
                        "Drive (primer ciclo: ver Hilo 2, clasificar.py --construir-maestro) y reanude.")
        if self.a.validacion:
            cambios = aplicar_nuevas(Path(self.a.validacion), self.maestro, d / "tabla_clasificada.parquet")
            self.decision(f"Validación de nuevas aplicada al maestro ({Path(self.a.validacion).name}): {cambios}")
            self.estado["versiones"]["maestro"] = self.version_maestro()
        t = pd.read_parquet(self.d("1_limpieza") / "tabla_limpia.parquet")
        reglas = cl.cargar_reglas()
        art, comb = cl.leer_maestro(self.maestro)
        tc, _ = cl.clasificar(t, reglas, art, comb)
        tc.to_parquet(d / "tabla_clasificada.parquet", index=False)
        res = cl.resumen(tc)
        cl.escribir_excel(d / "resumen_clasificacion.xlsx", res)
        art_n, comb_n = cl.nuevas_para_validar(tc, art, comb)
        oblig = combinaciones_obligatorias(comb_n, self.C["validacion_nuevas"])
        if len(art_n) or len(comb_n):
            if self.a.aceptar_propuestas:
                cambios = agregar_al_maestro(self.maestro, art_n, comb_n, reglas)
                self.decision(f"Se aceptaron las propuestas de las reglas para {len(art_n)} artículos y {len(comb_n)} "
                              "combinaciones nuevas (origen 'regla', sin validación humana).")
                self.estado["versiones"]["maestro"] = self.version_maestro()
                return f"nuevas aceptadas con la propuesta de las reglas: {cambios}"
            if len(art_n) or oblig.any():
                escribir_validacion_nuevas(d / "validar_nuevas.xlsx", art_n, comb_n, oblig, reglas)
                raise Pausa(
                    f"Hay descripciones nuevas que no están en el maestro: {len(art_n)} artículos nuevos y "
                    f"{len(comb_n)} combinaciones nuevas ({int(oblig.sum())} de validación obligatoria, "
                    f"{_m(comb_n.loc[oblig, 'gasto'].sum())} de gasto; el resto es opcional).\n"
                    f"Qué hacer: la persona responsable llena '¿Correcto? (SI/NO)' en {d / 'validar_nuevas.xlsx'} y "
                    "se reanuda con --validacion <archivo>. Alternativa: --aceptar-propuestas (queda registrado).")
            agregar_al_maestro(self.maestro, art_n, comb_n, reglas)
            self.estado["versiones"]["maestro"] = self.version_maestro()
        cuadre = res["Cuadre"].set_index("control")["valor"]
        self.estado["cuadres"].append(f"Clasificación: gasto {_m(cuadre['Gasto total de la tabla limpia'])} = suma por "
                                      f"categoría {_m(cuadre['Suma del gasto por categoría'])}; sin clasificar: "
                                      f"{int(cuadre['Filas sin clasificar'])} filas")
        return f"{len(art_n)} artículos y {len(comb_n)} combinaciones nuevas"

    # ------------------------------------------------------------- 3 a 6
    @property
    def tabla(self) -> str:
        return str(self.d("2_clasificacion") / "tabla_clasificada.parquet")

    def p3(self) -> str:
        r = an.main(["--tabla", self.tabla, "--salida", str(self.d("3_descriptivo")), "--desde", self.desde,
                     "--hasta", self.hasta, "--parametros", str(self.params_ciclo)])
        if r:
            raise RuntimeError(f"analizar.py terminó con código {r}")
        c = pd.read_parquet(self.d("3_descriptivo") / "tablas" / "control.parquet")
        v = c.set_index("control")["valor_soles"]
        total = [x for k, x in v.items() if k.startswith("Gasto de la tabla")][0]
        dentro = [x for k, x in v.items() if k.startswith("Gasto analizado")][0]
        fuera = [x for k, x in v.items() if k.startswith("Gasto fuera")][0]
        malos = c[c["resultado"].astype(str).str.startswith("NO CUADRA")]
        self.estado["cuadres"].append(f"Análisis: gasto analizado {_m(dentro)} + fuera de la ventana {_m(fuera)} = "
                                      f"{_m(dentro + fuera)} (tabla clasificada {_m(total)}); "
                                      f"sumas de tablas: {'OK' if malos.empty else 'CON DIFERENCIAS'}")
        if abs(dentro + fuera - total) > self.params["validacion"]["tolerancia_control_totales"] or not malos.empty:
            raise RuntimeError("Los cuadres del análisis no cierran (ver 3_descriptivo/tablas/control.parquet)")
        return f"gasto analizado {_m(dentro)}"

    def p4(self) -> str:
        r = al.main(["--tabla", self.tabla, "--salida", str(self.d("4_alertas")), "--parametros", str(self.params_ciclo)])
        if r:
            raise RuntimeError(f"alertas.py terminó con código {r}")
        R = pd.read_parquet(self.d("4_alertas") / "tablas" / "resumen.parquet")
        return f"{int(R['casos'].sum()):,} señales ({int(R['alta'].sum()):,} de prioridad alta)"

    def p5(self) -> str:
        taller = Path(self.a.taller) if self.a.taller else self.maestro_dir / self.C["kraljic_taller_archivo"]
        args = ["--tabla", self.tabla, "--salida", str(self.d("5_kraljic")), "--parametros", str(self.params_ciclo)]
        if taller.exists():
            args += ["--taller", str(taller)]
            self.decision(f"Kraljic con puntajes del taller: {taller.name}")
        r = kr.main(args)
        if r:
            raise RuntimeError(f"kraljic.py terminó con código {r}")
        if not taller.exists():
            if not self.a.kraljic_provisional:
                raise Pausa(
                    "Los puntajes de riesgo de Kraljic no están confirmados por el taller de expertos (se usaría la "
                    "propuesta de IA).\nQué hacer: completar 5_kraljic/kraljic_taller.xlsx en el taller y reanudar con "
                    f"--taller <archivo> (o guardarlo como maestro/{self.C['kraljic_taller_archivo']}); o reanudar con "
                    "--kraljic-provisional para seguir con la propuesta de IA marcada como provisional.")
            self.decision("Kraljic continúa con la propuesta de IA (provisional), por decisión --kraljic-provisional.")
        u = pd.read_parquet(self.d("5_kraljic") / "tablas" / "kraljic_unidades.parquet")
        return f"{len(u)} unidades; estado: {', '.join(sorted(u['estado'].astype(str).unique()))}"

    def p6(self) -> str:
        if not self.hasta.endswith(self.C["plan_en_semestre"]):
            return f"No aplica: el plan anual se recalcula en los ciclos {self.C['plan_en_semestre']}"
        P = kr.cargar_yaml(pr.PLAN_DEFECTO)
        anio = int(self.hasta[:4])
        P["anio_plan"], P["anios_historia"] = anio + 1, [anio - 2, anio - 1, anio]
        ruta = self.dir / "plan_ciclo.yaml"
        ruta.write_text("# Copia de config/plan_compras.yaml con los años de este ciclo (generada).\n"
                        + yaml.safe_dump(P, allow_unicode=True, sort_keys=False), encoding="utf-8")
        r = pr.main(["--tabla", self.tabla, "--kraljic", str(self.d("5_kraljic") / "tablas" / "kraljic_unidades.parquet"),
                     "--salida", str(self.d("6_plan")), "--parametros", str(self.params_ciclo), "--config-plan", str(ruta)])
        if r:
            raise RuntimeError(f"proyectar.py terminó con código {r}")
        return f"plan {anio + 1} con historia {anio - 2}–{anio}"

    # ------------------------------------------------------------- 7 salidas
    def p7(self) -> str:
        d = self.d("7_salidas")
        plan = self.d("6_plan") if (self.d("6_plan") / "tablas").exists() else None
        comunes = ["--descriptivo", str(self.d("3_descriptivo")), "--alertas", str(self.d("4_alertas")),
                   "--kraljic", str(self.d("5_kraljic")), "--periodo", self.a.periodo]
        if plan:
            comunes += ["--plan", str(plan)]
        ge.main(comunes + ["--tabla", self.tabla, "--calidad", str(self.d("1_limpieza") / "reporte_calidad.xlsx"),
                           "--salida", str(d)])
        r = gi.main(comunes + ["--ventana", f"{self.desde} a {self.hasta}", "--salida", str(d)])
        if r:
            raise RuntimeError("La verificación de cifras del informe falló (ver 7_salidas/informe_trazabilidad.xlsx)")
        self.estado["cuadres"].append("Informe ejecutivo: todas las cifras coinciden con sus tablas de origen")
        return "resultados, tablero (modelo en estrella) e informe ejecutivo"

    # ------------------------------------------------------------- 8 histórico
    def p8(self) -> str:
        if self.a.sin_historico:
            return "No aplica: ejecución con --sin-historico"
        meta = {"codigo": self.estado["versiones"]["codigo"], "maestro": self.estado["versiones"]["maestro"],
                "reglas_taxonomia": self.estado["versiones"]["reglas_taxonomia"],
                "reglas_alertas": self.estado["versiones"]["reglas_alertas"], "ventana": f"{self.desde} a {self.hasta}",
                "entrada_huella": self.estado["entrada"]["huella"]}
        destino = hi.agregar(self.dir, self.historico, self.a.periodo, meta)
        anterior = hi.periodo_anterior(self.historico, self.a.periodo)
        if anterior is None:
            return f"guardado en {destino.name}; no hay ciclo anterior para comparar"
        r = hi.comparar(self.historico, self.a.periodo, anterior)
        d = self.d("8_historico")
        d.mkdir(parents=True, exist_ok=True)
        cl.escribir_excel(d / f"comparacion_{self.a.periodo}_vs_{anterior}.xlsx", {k: v for k, v in r.items() if k[0] != "_"})
        (d / "comparacion_resumen.md").write_text(hi.texto_resumen(r, self.a.periodo), encoding="utf-8")
        return f"guardado en {destino.name}; comparado con {anterior}"


# --------------------------------------------------------------------------- nuevas descripciones

def combinaciones_obligatorias(comb_n: pd.DataFrame, V: dict) -> pd.Series:
    """Marca las combinaciones nuevas de mayor gasto que suman el % indicado (tope max_combinaciones)."""
    if comb_n.empty:
        return pd.Series(dtype=bool)
    orden = comb_n["gasto"].sort_values(ascending=False)
    tot = orden.clip(lower=0).sum()
    acum = orden.clip(lower=0).cumsum() / tot if tot > 0 else orden * 0
    sel = (acum.shift(fill_value=0) < V["pct_gasto_combinaciones"]) & (orden > 0)
    sel &= pd.Series(range(len(orden)), index=orden.index) < V["max_combinaciones"]
    return sel.reindex(comb_n.index).fillna(False).astype(bool)


INSTRUCCIONES_NUEVAS = [
    "Validación de descripciones NUEVAS del ciclo (solo lo que no está en el maestro)",
    "",
    "1. Hoja 'Articulos_nuevos' (obligatoria): escribe SI si la categoría/subcategoría propuesta es correcta;",
    "   si no, NO y llena 'Categoría corregida' y/o 'Subcategoría corregida' (usa la hoja 'Categorias').",
    "2. Hoja 'Combinaciones_nuevas': las filas con Prioridad = Obligatoria deben tener SI o NO;",
    "   si es NO, escribe el 'Producto corregido'. Las Opcionales pueden quedar vacías (entran con la propuesta).",
    "3. Guarda el archivo y reanuda: python scripts/ejecutar_ciclo.py … --validacion validar_nuevas.xlsx",
]


def escribir_validacion_nuevas(ruta: Path, art_n: pd.DataFrame, comb_n: pd.DataFrame, oblig: pd.Series,
                               reglas: dict) -> None:
    a = art_n.rename(columns={"articulo_normalizado": "Artículo", "categoria": "Categoría propuesta",
                              "subcategoria": "Subcategoría propuesta", "gasto": "Gasto S/", "filas": "Filas"})
    for c in ["¿Correcto? (SI/NO)", "Categoría corregida", "Subcategoría corregida", "Comentario"]:
        a[c] = ""
    c = comb_n.assign(Prioridad=oblig.map({True: "Obligatoria", False: "Opcional"}))
    c = c.sort_values(["Prioridad", "gasto"], ascending=[True, False])
    c = c[["Prioridad", "llave_combinacion", "articulo_normalizado", "descripcion_ejemplo", "concepto_ejemplo",
           "categoria", "subcategoria", "producto", "origen", "gasto", "filas"]].rename(columns={
        "llave_combinacion": "Llave", "articulo_normalizado": "Artículo", "descripcion_ejemplo": "Descripción",
        "concepto_ejemplo": "Concepto", "categoria": "Categoría", "subcategoria": "Subcategoría",
        "producto": "Producto propuesto", "origen": "Origen del producto", "gasto": "Gasto S/", "filas": "Filas"})
    c["¿Correcto? (SI/NO)"] = ""
    c["Producto corregido"] = ""
    cl.escribir_excel(ruta, {"Instrucciones": pd.DataFrame({"Instrucciones": INSTRUCCIONES_NUEVAS}),
                             "Articulos_nuevos": a, "Combinaciones_nuevas": c,
                             "Categorias": pd.DataFrame({"Categoría": reglas["categorias"]})})


def _respaldo(maestro: Path) -> None:
    resp = maestro.parent / "respaldos"
    resp.mkdir(exist_ok=True)
    shutil.copy2(maestro, resp / f"{maestro.stem}_{datetime.now():%Y%m%d_%H%M%S}{maestro.suffix}")


def agregar_al_maestro(maestro: Path, art_n: pd.DataFrame, comb_n: pd.DataFrame, reglas: dict,
                       validados_art: pd.DataFrame | None = None, validados_comb: pd.DataFrame | None = None) -> dict:
    """Agrega al maestro los artículos y combinaciones nuevos (con respaldo previo). Nunca borra filas."""
    art, comb = cl.leer_maestro(maestro)
    hoy = date.today().isoformat()
    na = pd.DataFrame({"articulo_normalizado": art_n["articulo_normalizado"], "categoria": art_n["categoria"],
                       "subcategoria": art_n["subcategoria"], "origen": "regla", "confianza": "media",
                       "regla": "ciclo", "fecha": hoy, "version": reglas["version"]})
    nc = pd.DataFrame({"llave_combinacion": comb_n["llave_combinacion"],
                       "articulo_normalizado": comb_n["articulo_normalizado"],
                       "descripcion_ejemplo": comb_n["descripcion_ejemplo"], "categoria": comb_n["categoria"],
                       "subcategoria": comb_n["subcategoria"], "producto": comb_n["producto"],
                       "origen": comb_n["origen"], "corregido": "False", "fecha": hoy, "version": reglas["version"]})
    if validados_art is not None:
        na = na.set_index("articulo_normalizado")
        na.update(validados_art.set_index("articulo_normalizado"))
        na = na.reset_index()
    if validados_comb is not None:
        nc = nc.set_index("llave_combinacion")
        nc.update(validados_comb.set_index("llave_combinacion"))
        nc = nc.reset_index()
    art = pd.concat([art, na[~na["articulo_normalizado"].isin(art["articulo_normalizado"])]], ignore_index=True)
    comb = pd.concat([comb, nc[~nc["llave_combinacion"].isin(comb["llave_combinacion"])]], ignore_index=True)
    _respaldo(maestro)
    cl.escribir_excel(maestro, {"articulos": art.astype(str).replace({"nan": ""}),
                                "combinaciones": comb.astype(str).replace({"nan": ""})})
    return {"articulos_agregados": len(na), "combinaciones_agregadas": len(nc)}


def aplicar_nuevas(ruta: Path, maestro: Path, tabla_clasificada: Path) -> dict:
    """Lee validar_nuevas.xlsx completado y agrega lo validado al maestro. Falta algo obligatorio → Pausa."""
    xl = pd.ExcelFile(ruta)
    va = pd.read_excel(xl, "Articulos_nuevos", dtype=str).fillna("")
    vc = pd.read_excel(xl, "Combinaciones_nuevas", dtype=str).fillna("")
    ok = lambda s: s.str.strip().str.upper().str.replace("Í", "I")  # noqa: E731
    va["_ok"], vc["_ok"] = ok(va["¿Correcto? (SI/NO)"]), ok(vc["¿Correcto? (SI/NO)"])
    falta_a = va[~va["_ok"].isin(["SI", "NO"])]
    falta_c = vc[(vc["Prioridad"] == "Obligatoria") & ~vc["_ok"].isin(["SI", "NO"])]
    sin_corr = vc[(vc["_ok"] == "NO") & (vc["Producto corregido"].str.strip() == "")]
    if len(falta_a) or len(falta_c) or len(sin_corr):
        raise Pausa(f"La validación está incompleta: faltan {len(falta_a)} artículos y {len(falta_c)} combinaciones "
                    f"obligatorias sin SI/NO, y {len(sin_corr)} NO sin 'Producto corregido'. Complete {ruta} y reanude.")
    hoy = date.today().isoformat()
    art_n = pd.DataFrame({"articulo_normalizado": va["Artículo"], "categoria": va["Categoría propuesta"],
                          "subcategoria": va["Subcategoría propuesta"]})
    val_a = art_n.copy()
    corr = va["_ok"] == "NO"
    val_a.loc[corr & (va["Categoría corregida"].str.strip() != ""), "categoria"] = va["Categoría corregida"].str.strip()
    val_a.loc[corr & (va["Subcategoría corregida"].str.strip() != ""), "subcategoria"] = va["Subcategoría corregida"].str.strip()
    val_a = val_a.assign(origen="humano", confianza="alta", fecha=hoy)
    comb_n = pd.DataFrame({"llave_combinacion": vc["Llave"], "articulo_normalizado": vc["Artículo"],
                           "descripcion_ejemplo": vc["Descripción"], "categoria": vc["Categoría"],
                           "subcategoria": vc["Subcategoría"], "producto": vc["Producto propuesto"],
                           "origen": vc["Origen del producto"]})
    rev = vc[vc["_ok"].isin(["SI", "NO"])]
    val_c = pd.DataFrame({"llave_combinacion": rev["Llave"], "origen": "humano", "fecha": hoy,
                          "producto": rev["Producto propuesto"], "corregido": "False"})
    m = (rev["_ok"] == "NO").to_numpy()
    val_c.loc[m, "producto"] = rev.loc[m, "Producto corregido"].str.strip().to_numpy()
    val_c.loc[m, "corregido"] = "True"
    cambios = agregar_al_maestro(maestro, art_n, comb_n, cl.cargar_reglas(), val_a, val_c)
    cambios.update(articulos_corregidos=int(corr.sum()), productos_corregidos=int(m.sum()),
                   combinaciones_revisadas=len(rev))
    return cambios


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ejecuta el ciclo semestral completo del análisis de gastos (Hilo 8).")
    ap.add_argument("--entrada", required=True, help="Exportación del ERP (xlsx o csv)")
    ap.add_argument("--periodo", required=True, help="Ciclo, ej. 2026-S2 (último semestre de la ventana)")
    ap.add_argument("--raiz", help="Carpeta raíz de datos (Drive sincronizado). Por defecto: config/local.yaml "
                                   "(lo crea preparar_equipo.py) o parametros.yaml > rutas")
    ap.add_argument("--parametros", default=str(lv.PARAMETROS_DEFECTO))
    ap.add_argument("--maestro", help="Ruta del maestro (por defecto <raiz>/maestro/maestro_categorias.xlsx)")
    ap.add_argument("--validacion", help="validar_nuevas.xlsx completado por la persona")
    ap.add_argument("--aceptar-propuestas", action="store_true", help="Acepta las propuestas de las reglas para las nuevas")
    ap.add_argument("--taller", help="kraljic_taller.xlsx completado por los expertos")
    ap.add_argument("--kraljic-provisional", action="store_true", help="Continúa con la propuesta de IA de Kraljic")
    ap.add_argument("--reiniciar", action="store_true", help="Borra el estado del ciclo y empieza de nuevo")
    ap.add_argument("--simular-corte", action="store_true",
                    help="SOLO PRUEBAS: usa las filas con factura hasta el fin del periodo (simula un extracto anterior)")
    ap.add_argument("--sin-historico", action="store_true", help="No guarda el ciclo en el histórico (pruebas)")
    a = ap.parse_args(argv)
    if not hi.PERIODO.match(a.periodo):
        ap.error("--periodo debe tener la forma AAAA-S1 o AAAA-S2")
    return Ciclo(a).ejecutar()


if __name__ == "__main__":
    sys.exit(main())
