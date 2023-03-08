from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify, make_response, \
    send_from_directory, current_app
from flask_login import current_user, login_required
from convenios_app.models import (Convenio, Institucion, SdInvolucrada, BitacoraAnalista, TrayectoriaEtapa, TrayectoriaEquipo,
                                  HitosConvenio, RecepcionConvenio, WSConvenio, EntregaConvenio)
from convenios_app.users.utils import admin_only, analista_only
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import dias_habiles, formato_periodicidad
from convenios_app.main.utils import generar_nombre_convenio, ID_EQUIPOS, COLORES_ETAPAS, COLORES_EQUIPOS
from convenios_app.informes.utils import obtener_etapa_actual_dias, obtener_equipos_actual_dias, adendum, convenio_cuenta, por_firmar, otros

from datetime import datetime, date
from pprint import pprint
from math import ceil, floor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger


intercambio = Blueprint('intercambio', __name__)


@intercambio.route('/recepcion_sftp')
@login_required
@analista_only
def recepcion_sftp():
    return render_template("intercambio/recepcion_sftp.html")
