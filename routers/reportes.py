from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from Conexion_DB import get_db
from reportes import datos_del_reporte, generar_excel, generar_pdf, nombre_de_archivo

router = APIRouter(prefix="/reportes", tags=["Reportes"])

TIPO_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def reunir_datos(db: Session, desde: date, hasta: date, obra_id: Optional[int]) -> dict:
    try:
        return datos_del_reporte(db, desde, hasta, obra_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))


def archivo(contenido: bytes, tipo: str, nombre: str) -> Response:
    return Response(
        content=contenido,
        media_type=tipo,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


# 1. RESUMEN DEL PERIODO (lo que muestra el panel; las fechas son días de México)
@router.get("/resumen")
def resumen(
    desde: date,
    hasta: date,
    obra_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    datos = reunir_datos(db, desde, hasta, obra_id)
    return {clave: datos[clave] for clave in ("desde", "hasta", "obra", "resumen", "totales")}


# 2. EXCEL PARA NÓMINAS (resumen, jornadas con horas, faltas e incidencias)
@router.get("/excel")
def excel(
    desde: date,
    hasta: date,
    obra_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    datos = reunir_datos(db, desde, hasta, obra_id)
    return archivo(generar_excel(datos), TIPO_EXCEL, nombre_de_archivo(datos, "xlsx"))


# 3. PDF EJECUTIVO (totales, gráfica y tablas)
@router.get("/pdf")
def pdf(
    desde: date,
    hasta: date,
    obra_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    datos = reunir_datos(db, desde, hasta, obra_id)
    return archivo(generar_pdf(datos), "application/pdf", nombre_de_archivo(datos, "pdf"))
