#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor de renderizado de NetPlotBrain
=======================================

Recibe los parámetros de una figura, la renderiza con netplotbrain y devuelve
un PNG. Pensado para equipos que no tienen recursos para renderizar en local.

Endpoints:
    GET  /salud       comprobación de conectividad (la usa la aplicación)
    POST /renderizar  recibe los parámetros y devuelve image/png

Arranque local:
    uvicorn app:app --host 0.0.0.0 --port 7860

Con Docker:
    docker build -t netplotbrain-servidor .
    docker run -p 7860:7860 netplotbrain-servidor

PRIVACIDAD: si trabajas con datos de pacientes, lee el README de esta carpeta
antes de subir este servidor a un proveedor en la nube. La opción recomendada
en ese caso es levantarlo en un equipo de tu propia red local.
"""

import os
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

import matplotlib
matplotlib.use("Agg")  # imprescindible: no hay pantalla en un servidor

import matplotlib.pyplot as plt  # noqa: E402
import netplotbrain  # noqa: E402
import pandas as pd  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field  # noqa: E402

# Límites para que una petición mal formada no tumbe el servidor
MAX_NODOS = int(os.environ.get("MAX_NODOS", "500"))
MAX_ARISTAS = int(os.environ.get("MAX_ARISTAS", "20000"))
TOKEN = os.environ.get("TOKEN_NETPLOTBRAIN", "").strip()

app = FastAPI(title="Servidor de renderizado NetPlotBrain", version="9.5")


class Peticion(BaseModel):
    # extra="forbid" rechaza parámetros desconocidos en lugar de ignorarlos en
    # silencio: si la aplicación y el servidor se desincronizan, se nota.
    model_config = ConfigDict(extra="forbid")

    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    template: str = "MNI152NLin2009cAsym"
    template_style: str = "surface"
    template_voxelsize: int = 2
    template_color: Optional[str] = None
    template_alpha: Optional[float] = None
    view: str = "LSR"
    hemisphere: Optional[str] = None
    frames: Optional[int] = None
    node_type: str = "circles"
    node_scale: Optional[float] = None
    node_alpha: Optional[float] = None
    node_color: Optional[Union[str, List[str]]] = None
    node_size: Optional[Union[str, float, List[float]]] = None
    node_sizevminvmax: Optional[List[float]] = None
    node_colorby: Optional[str] = None
    edge_color: Optional[str] = None
    edge_alpha: Optional[float] = None
    edge_widthscale: Optional[float] = None
    edge_threshold: Optional[float] = None
    title: Optional[str] = None
    dpi: int = Field(default=150, ge=50, le=300)
    token: Optional[str] = None


def _a_dataframe(filas, maximo, etiqueta):
    """Convierte la lista de diccionarios en DataFrame con columnas numéricas."""
    if not filas:
        return None
    if len(filas) > maximo:
        raise HTTPException(413, f"Demasiadas {etiqueta}: {len(filas)} (máximo {maximo}).")
    df = pd.DataFrame(filas)
    for col in df.columns:
        # pandas 3.x quitó errors="ignore": hay que convertir y revisar aparte.
        convertida = pd.to_numeric(df[col], errors="coerce")
        if not convertida.isna().all():
            df[col] = convertida
    return df


@app.get("/salud")
def salud():
    return {"estado": "ok", "version": app.version,
            "requiere_token": bool(TOKEN),
            "max_nodos": MAX_NODOS, "max_aristas": MAX_ARISTAS}


@app.post("/renderizar")
def renderizar(p: Peticion):
    if TOKEN and p.token != TOKEN:
        raise HTTPException(401, "Token incorrecto o ausente.")

    if p.node_type == "parcels":
        raise HTTPException(
            400, "El tipo de nodo 'parcels' necesita un atlas en el servidor y "
                 "es demasiado lento para una petición HTTP. Usa 'circles' o 'spheres'.")

    nodos = _a_dataframe(p.nodes, MAX_NODOS, "nodos")
    aristas = _a_dataframe(p.edges, MAX_ARISTAS, "aristas")
    if nodos is None:
        raise HTTPException(400, "No se recibió ningún nodo.")
    faltan = [c for c in "xyz" if c not in nodos.columns]
    if faltan:
        raise HTTPException(400, f"A los nodos les faltan las columnas: {', '.join(faltan)}.")

    kw = {k: v for k, v in p.model_dump().items()
          if v is not None and k not in ("nodes", "edges", "dpi", "token")}
    kw["nodes"] = nodos
    if aristas is not None:
        kw["edges"] = aristas

    try:
        plt.close("all")
        fig, _ = netplotbrain.plot(**kw)
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=p.dpi, facecolor="white", bbox_inches="tight")
        plt.close(fig)
        return Response(content=buf.getvalue(), media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        plt.close("all")
        raise HTTPException(500, f"No se pudo renderizar: {type(e).__name__}: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "7860")))
