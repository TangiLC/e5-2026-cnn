import sqlite3
import unittest

SCHEMA = """
CREATE TABLE labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL
);
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image TEXT NOT NULL,
    label INTEGER NOT NULL REFERENCES labels(id),
    commentaire TEXT NOT NULL,
    modele TEXT NOT NULL
);
INSERT INTO labels (label) VALUES ('forêt'), ('mer'), ('désert'), ('nuageux');
INSERT INTO predictions (image, label, commentaire, modele) VALUES
    ('a.jpg', 1, 'OK', 'v1'),
    ('b.jpg', 2, 'OK', 'v2');
"""

REQUETE_CORRIGEE = (
    "SELECT predictions.id as id, predictions.image as image, "
    "labels.label as label, predictions.commentaire as commentaire, "
    "predictions.modele as modele "
    "FROM predictions JOIN labels ON predictions.label = labels.id"
)

# Requête initiale (ticket-3) : le champ id n'est pas sélectionné.
REQUETE_AVEC_BUG = (
    "SELECT predictions.image as image, "
    "labels.label as label, predictions.commentaire as commentaire, "
    "predictions.modele as modele "
    "FROM predictions JOIN labels ON predictions.label = labels.id"
)


def ligne_en_dict(cursor, row):
    """Transforme une ligne SQLite en dict, comme le curseur MySQL."""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


class TestRequeteListerPredictions(unittest.TestCase):
    """Vérifie la présence de l'id selon la requête (ticket-3)."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = ligne_en_dict
        self.conn.executescript(SCHEMA)
        self.addCleanup(self.conn.close)

    def _executer(self, sql):
        """Exécute la requête et retourne toutes les lignes."""
        return self.conn.execute(sql).fetchall()

    def test_requete_corrigee_contient_l_id(self):
        lignes = self._executer(REQUETE_CORRIGEE)

        self.assertEqual(len(lignes), 2)
        self.assertEqual([l["id"] for l in lignes], [1, 2])
        self.assertEqual(lignes[1]["label"], "mer")
        print(f"Test true : assert 'id' in {REQUETE_CORRIGEE}")

    def test_requete_initiale_n_a_pas_d_id(self):
        lignes = self._executer(REQUETE_AVEC_BUG)

        self.assertEqual(len(lignes), 2)
        print(f"Test falty : assert 'id' not in {REQUETE_AVEC_BUG}")
        self.assertNotIn("id", lignes[0])


if __name__ == "__main__":
    unittest.main()