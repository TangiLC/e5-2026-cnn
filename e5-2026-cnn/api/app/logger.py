import logging
from datetime import datetime, timedelta

from app.bdd.connexion import Connexion
from app.config import LOG_RETENTION_DAYS


class _DateTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        timestamp = datetime.fromtimestamp(record.created)
        return timestamp.strftime("%Y%m%d-%H:%M:%S.%f")[:-3]


class _MysqlHandler(logging.Handler):
    def emit(self, record):
        try:
            with Connexion.ouvrir_connexion() as (bdd, cursor):
                cursor.execute(
                    "INSERT INTO logs (timestamp, level, module, message) VALUES (%s, %s, %s, %s)",
                    [
                        datetime.fromtimestamp(record.created),
                        record.levelname,
                        record.module,
                        record.getMessage(),
                    ],
                )
                bdd.commit()
        except Exception:
            # Un échec d'écriture en base ne doit jamais impacter l'application.
            pass


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        _DateTimeFormatter("%(asctime)s [%(levelname)s] %(module)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.addHandler(_MysqlHandler())


def purge_old(retention_days=LOG_RETENTION_DAYS):
    """Supprime les logs plus anciens que la rétention ; retourne le nombre de lignes supprimées."""
    if not retention_days:
        return 0
    limite = datetime.now() - timedelta(days=retention_days)
    with Connexion.ouvrir_connexion() as (bdd, cursor):
        cursor.execute("DELETE FROM logs WHERE timestamp < %s", [limite])
        bdd.commit()
        supprimes = cursor.rowcount
    logger.info("Purge des logs (rétention=%dj, supprimés=%d)", retention_days, supprimes)
    return supprimes
