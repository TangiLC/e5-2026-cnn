from pydantic import BaseModel, ConfigDict

class Prediction(BaseModel) :
    model_config = ConfigDict(extra="forbid")

    id: int
    image : str
    label : str
    commentaire : str
    modele : str
