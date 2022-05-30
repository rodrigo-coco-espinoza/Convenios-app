from datetime import datetime, date
from convenios_app.bitacoras.forms import EQUIPOS
from convenios_app import db
from convenios_app.models import TrayectoriaEquipo, BitacoraAnalista, Convenio, TrayectoriaEtapa, SdInvolucrada
from convenios_app.bitacoras.utils import dias_habiles
from sqlalchemy import and_, or_


def obtener_etapa_actual_dias(convenio):
    etapa = TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == convenio.id,
                                               TrayectoriaEtapa.salida == None)).first()
    return f'{etapa.etapa.etapa} ({dias_habiles(etapa.ingreso, date.today())})'


def obtener_equipos_actual_dias(convenio):
    equipos = TrayectoriaEquipo.query.filter(and_(TrayectoriaEquipo.id_convenio == convenio.id,
                                                  TrayectoriaEquipo.salida == None)).all()
    lista = '<ul style="text-align: left; list-style: none; padding: 0;">'
    for equipo in equipos:
        lista += f"<li>{equipo.equipo.sigla} ({dias_habiles(equipo.ingreso, date.today())})</li>"
    lista += '</u>'
    return lista
