from datetime import datetime, date
from convenios_app.bitacoras.forms import EQUIPOS
from convenios_app import db
from convenios_app.models import TrayectoriaEquipo, BitacoraAnalista, Convenio, TrayectoriaEtapa, SdInvolucrada
from convenios_app.main.utils import formato_nombre
from sqlalchemy import and_, or_


def obtener_etapa_actual_dias(convenio):
    etapa = TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == convenio.id,
                                               TrayectoriaEtapa.salida == None)).first()
    return f'{etapa.etapa.etapa} ({(date.today() - etapa.ingreso).days})'


def obtener_equipos_actual_dias(convenio):
    equipos = TrayectoriaEquipo.query.filter(and_(TrayectoriaEquipo.id_convenio == convenio.id,
                                                  TrayectoriaEquipo.salida == None)).all()
    lista = '<ul style="text-align: left; list-style: none; padding: 0;">'
    for equipo in equipos:
        lista += f"<li>{equipo.equipo.sigla} ({(date.today() - equipo.ingreso).days})</li>"
    lista += '</u>'
    return lista
