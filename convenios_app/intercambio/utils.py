from datetime import datetime, date
from convenios_app.bitacoras.forms import EQUIPOS
from convenios_app import db
from convenios_app.models import TrayectoriaEquipo, BitacoraAnalista, Convenio, TrayectoriaEtapa, SdInvolucrada
from convenios_app.bitacoras.utils import dias_habiles
from sqlalchemy import and_, or_
import pandas as pd


class Archivo:
    """
    Crea un objeto archivo con la información en un DataFrame. Los métodos se utilizan para generar las filas de las distintas tablas.
    Se asume que el tipo de archivo y separador son los correctos.
    """

    def __init__(self, filename, file, sep):
        self.filename = filename
        self.df = pd.read_csv(file, sep=sep, encoding="latin-1")
        # Se asume que la primera columna de todos los archivos es el RUT
        self.rutColumn = self.df[self.df.columns[0]]

    def contarRuts(self, limInf, limSup):
        """
        Cuenta la cantidad de RUTs entre dos intervalos
        :param limInf: límite inferior (mnayor o igual)
        :param limSup: límite superior (menor estricto)
        :return: cantidad de RUTs tal que limInf <= return < limSup
        """
        return f"{self.df[(self.rutColumn >= limInf) & (self.rutColumn < limSup)].shape[0]:,.0f}"

    def hayRUTsNA(self):
        """
        Verifica si el archivo tiene filas NA
        :return: true si hay filas NA, false si no.
        """
        return f"{self.rutColumn.isna().values.any()}"

    def hayFilasRepetidas(self):
        """
        Verifica si el archivo cuenta con filas repetidas
        :return: true si hay filas repetidas, false si no.
        """
        return f"{self.df.duplicated().values.any()}"

    def contarFilas(self):
        """
        Cuenta la cantidad de registros (filas) del archivo.
        :return: Número de filas en el archivo.
        """
        return f"{self.df.shape[0]:,.0f}"

    def rutMin(self):
        """
        Obtiene el RUT mínimo del archivo.
        """
        return f"{int(self.rutColumn.min()):,.0f}"

    def rutMax(self):
        """
        Obtiene el RUT máximo del archivo.
        """
        return f"{int(self.rutColumn.max()):,.0f}"

    def contarRutsUnicos(self):
        """
        Cuenta la cantidad de declarantes (RUTs) únicos
        """
        return f"{self.rutColumn.nunique():,.0f}"

    def rut_por_tramos(self):
        data = []
        inf = 0
        for sup in range(5000000, 55000000, 5000000):
            data.append((f"[{inf:,.0f} - {sup:,.0f})", self.contarRuts(inf, sup)))
            inf = sup
        data.append(("[50,000,000 - ∞)", self.contarRuts(inf, inf * 10)))
        data.append(("TOTAL", f"{len(self.rutColumn):,.0f}"))

        return data

    def validacion_archivo(self):
        data = {
            "RUTs NA": self.hayRUTsNA(),
            "Filas repetidas": self.hayFilasRepetidas(),
            "Cantidad de registros": self.contarFilas(),
            "RUT mínimo": self.rutMin(),
            "RUT máximo": self.rutMax(),
            "RUTs únicos": self.contarRutsUnicos()
        }
        return data