"""Tests des DTO Prediction (Create / Read) et de la route GET /predictions/."""
from contextlib import asynccontextmanager
from pathlib import Path
import sys
from types import ModuleType

import pytest
from fastapi.exceptions import ResponseValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError

API_ROOT = Path(__file__).resolve().parents[1] / "e5-2026-cnn" / "api"
sys.path.insert(0, str(API_ROOT))
sys.modules["app.modele.cnn"] = ModuleType("app.modele.cnn")

from app.bdd.prediction import PredictionCreate, PredictionRead
from app.bdd.service import Service_Prediction
from app.main import app

CREATE_DATA = {
    "image": "images/satellite.jpg",
    "label": "forêt",
    "commentaire": "OK",
    "modele": "CNN",
}
READ_DATA = {**CREATE_DATA, "id": 1}

@pytest.fixture
def client(monkeypatch):
    """Client de test sans chargement du modèle CNN."""
    @asynccontextmanager
    async def lifespan_without_model_loading(_app):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", lifespan_without_model_loading)
    with TestClient(app) as test_client:
        yield test_client


def stub_service(monkeypatch, rows):
    """Remplace lister_predictions pour qu'il renvoie `rows`."""
    monkeypatch.setattr(Service_Prediction, "lister_predictions", lambda: rows)


# --- DTO seuls : rapides, sans client HTTP -------------------------------

class TestPredictionCreate:
    """Prédiction avant insertion : pas d'id."""

    def test_accepte_donnees_sans_id(self):
        print("Test OK: création de donnée sans id")
        assert PredictionCreate(**CREATE_DATA).label == "forêt"

    @pytest.mark.parametrize(
        "extra",
        [pytest.param({"id": 1}, id="id_interdit"),
         pytest.param({"greeting": "bonjour"}, id="cle_supplementaire")],
    )
    def test_rejette_champs_inattendus(self, extra, request):
        print(f"Test KO: création de donnée avec champs invalide {request.node.callspec.id} ")
        with pytest.raises(ValidationError):
            PredictionCreate(**CREATE_DATA, **extra)


class TestPredictionRead:
    """Prédiction relue en base : id obligatoire (non-régression ticket 3)."""

    def test_accepte_id_entier(self):
        print("Test OK: donnée persistée avec id")
        assert PredictionRead(**READ_DATA).id == 1
        
    INVALID_READ = [
    pytest.param(CREATE_DATA, id="id_absent"),
    pytest.param({**CREATE_DATA, "id": None}, id="type_none"),
    pytest.param({**CREATE_DATA, "id": "abc&"}, id="type_str"),
    pytest.param({**CREATE_DATA, "id": 1.1}, id="type_float"),
]
    @pytest.mark.parametrize("data", INVALID_READ)
    def test_rejette_id_invalide(self, data, request):
        print(f"Test KO: Donnée persistée avec champs id de type invalide {request.node.callspec.id} ")
        with pytest.raises(ValidationError):
            PredictionRead(**data)
