from pydantic import BaseModel, ConfigDict

# Debug Ticket-3 Séparation DTO / Responsabilité unique et héritage

class PredictionCreate(BaseModel):
    """Prédiction avant insertion : pas d'id."""
    model_config = ConfigDict(extra="forbid")

    image: str
    label: str
    commentaire: str
    modele: str

class PredictionRead(PredictionCreate):
    """Prédiction relue en base : id obligatoire."""
    id: int