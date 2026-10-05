from contextlib import asynccontextmanager
from pathlib import Path
import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from fastapi.exceptions import ResponseValidationError


API_ROOT = Path(__file__).resolve().parents[1] / "e5-2026-cnn" / "api"
sys.path.insert(0, str(API_ROOT))
sys.modules["app.modele.cnn"] = ModuleType("app.modele.cnn")

from app.bdd.service import Service_Prediction
from app.main import app


PREDICTION = {
    "image": "images/satellite.jpg",
    "label": "forest",
    "commentaire": "OK",
    "modele": "CNN",
}


@pytest.fixture
def client(monkeypatch):
    @asynccontextmanager
    async def lifespan_without_model_loading(_app):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", lifespan_without_model_loading)
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    "prediction",
    [
        pytest.param({**PREDICTION, "id": 1}, id="id_int"),
        pytest.param({**PREDICTION, "id": None}, id="id_none"),
    ],
)
def test_prediction_schema_accepts_valid_response(client, monkeypatch, prediction, request):
    monkeypatch.setattr(Service_Prediction, "lister_predictions", lambda: [prediction])

    response = client.get("/predictions/")

    print(f"Test true {request.node.callspec.id} : assert {response.json()} == {[prediction]}")
    assert response.status_code == 200
    assert response.json() == [prediction]


@pytest.mark.parametrize(
    "prediction",
    [
        pytest.param({**PREDICTION, "id": "abc&"}, id="int_mauvais_type_str"),
        pytest.param({**PREDICTION, "id": "1.1"}, id="int_mauvais_type_float"),
        pytest.param({**PREDICTION, "id": 1, "greeting": "bonjour"}, id="cle_supplementaire"),
    ],
)
def test_prediction_schema_rejects_invalid_response(client, monkeypatch, prediction, request):
    monkeypatch.setattr(Service_Prediction, "lister_predictions", lambda: [prediction])

    print(f"Test falty {request.node.callspec.id} : assert {prediction} raises {ResponseValidationError}")

    with pytest.raises(ResponseValidationError):
        client.get("/predictions/")