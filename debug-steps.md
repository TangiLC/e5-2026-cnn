# historisation du process de debug

Ce fichier est append-only.

Pour le fun of it, le débug se fera à la main (sans assistant de code) et sera bruité intégralement à la bouche.

## Rappel du Bug

1. Lancer l'application.
2. Sélectionner *Voir les prédictions*.
3. La *liste des prédictions enregistrées* n'affiche que des *prédiction None*.

### Résultat actuel
Toutes les *prédictions* sont nommées *none*.

## Intuition n.1

Les id ne sont pas stockées dans la BDD
- Aperçu des entrées de la bdd dans adminer
![Capture d'écran de adminer](./ressources/adminer_001.png)
Les id sont bien présents, incrémentiels, identité (PK)

## Intuition n.2
- Passage des id vers le streamlit
Récupération des id dans la bdd, syntaxe

Ouverture du swagger, test de la route GET/list
![Capture d'écran de swagger](./ressources/swagger_001.png)

> L'API retourne id:'null'
> Le bug semble se situer au niveau de l'API

Requête SQL initiale :
cursor.execute(
                "SELECT predictions.image as image, labels.label as label, predictions.commentaire as commentaire, predictions.modele as modele FROM predictions JOIN labels ON predictions.label = labels.id"
            )
L'id n'est pas passé dans la requête, le schema pydantic est :

class Prediction(BaseModel) :
    id: int | None = None
    image : str
    label : str
    commentaire : str
    modele : str

(Pas d'erreur car None autorisé dans le schéma pydantic)

### Corrections

1. Correction de la requête SQL

cursor.execute(
                **"SELECT predictions.id as id**, predictions.image as image, labels.label as label, predictions.commentaire as commentaire, predictions.modele as modele FROM predictions JOIN labels ON predictions.label = labels.id"
            )

2. Correction / optimisation du schéma pydantic

Utilisation d'un schéma pydantic plus rigide pour lever une exception en cas de problème
class Prediction(BaseModel) :
   **model_config = ConfigDict(extra="forbid")**
- Ajout de forbid pour lever une exception si le schéma contient une clé supplémentaire
- Le type None doit être conservé car le pipeline est requête 1 (avant infarence -> None puis après inférence écriture en base avec id)
- Comme aucun des autres champs n'accepte le type None, le schéma doit recevoir tous les champs avec une valeur typée non null

### Test unitaire

En s'appuyant sur le schema pydantic, création de test unitaires pour validation (mock du retour API avec des cas test)
Cas de test pour id
 "int_mauvais_type_str"
 "int_mauvais_type_float"
 "cle_supplementaire"
 "cle-absente"


### Mise en place de monitoring et logging

1. Ajout d'un logger horodaté

Création d'un script logger utilisant logging et timestamp

Ajout d'une table "logs" à la base mysql

le logger écrit dans la base.

La methode purge est appelée toutes les 24h pour supprimer les logs anciens 
(config dans .env : LOG_RETENTION_DAYS) si le champs existe et est valide (>0)

2. Ajout d'une route GET all_logs, ajout d'une page dans streamlit

Récupération des logs stockés dans la bdd

Affichage des logs

La route n'est pas sécurisée...


3. Mise en place du monitoring

Utilisation de Langfuse v4 auto-hébergé pour monitorer les inférences CNN

Ajout d'une route check_health pour monitorer la disponibilité du modèle




