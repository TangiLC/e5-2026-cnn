import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from pprint import pprint
from uuid import uuid4
import logging
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from mysql.connector import Error as DatabaseError
from PIL import Image, UnidentifiedImageError
from app.modele import cnn
from app.config import UPLOAD_FOLDER
from app.bdd.service import Service_Prediction
from app.bdd.prediction import Prediction
from app.config import LOG_RETENTION_DAYS
from app import logger as journal
from app.observability import flush as flush_observability
from app.observability import observe, update_observation

PURGE_INTERVAL_SECONDS = 24 * 3600


async def purger_logs_periodiquement():
    while True:
        try:
            await asyncio.to_thread(journal.purge_old)
        except Exception:
            logging.getLogger(__name__).exception("Échec de la purge des logs")
        await asyncio.sleep(PURGE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app):
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    cnn.get_model()
    tache_purge = asyncio.create_task(purger_logs_periodiquement()) if LOG_RETENTION_DAYS else None
    yield
    if tache_purge:
        tache_purge.cancel()
    flush_observability()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(DatabaseError)
async def database_error(request: Request, exc: DatabaseError):
    logging.getLogger(__name__).error("Erreur MySQL : %s", exc)
    return JSONResponse(status_code=503, content={"detail": "Base de données indisponible"})


@app.get("/")
def index():
    return "API Prediction!"


@app.get("/model_health")
def model_health():
    with observe("model_health") as observation:
        try:
            cnn.get_model()
        except Exception as exc:
            logging.getLogger(__name__).exception("Le modèle CNN est indisponible")
            update_observation(
                observation,
                level="ERROR",
                status_message="Le modèle CNN est indisponible",
            )
            raise HTTPException(
                status_code=503,
                detail="Modèle indisponible",
            ) from exc

        result = {"status": "ok", "model": "CNN"}
        update_observation(observation, output=result)
        return result


@app.post("/predictions/satellite/")
def upload_image(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    with observe(
        "satellite_prediction",
        input_data={"file_format": suffix},
        metadata={"model": "CNN"},
    ) as observation:
        if suffix not in {".jpg", ".jpeg", ".png"}:
            file.file.close()
            raise HTTPException(status_code=400, detail="Format non supporté")
        file_path = Path(UPLOAD_FOLDER) / f"{uuid4().hex}{suffix}"
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            try:
                with Image.open(file_path) as image:
                    image.verify()
            except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
                raise HTTPException(status_code=400, detail="Image invalide") from exc
            label = cnn.predict_image(file_path)
            prediction = Prediction(image=str(file_path), label=label, commentaire="OK", modele="CNN")
            Service_Prediction.sauvegarder_prediction(prediction)
            result = {"prediction": prediction}
            update_observation(observation, output={"label": label})
            return result
        except Exception:
            file_path.unlink(missing_ok=True)
            raise
        finally:
            file.file.close()


@app.get("/predictions/", response_model=list[Prediction])
def list_predictions():
    predictions = Service_Prediction.lister_predictions()
    pprint(predictions)
    return predictions


@app.get("/all_logs")
def all_logs():
    return journal.lister_logs()
