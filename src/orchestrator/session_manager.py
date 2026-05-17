import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class SessionState(Enum):
    """
    Cycle de vie d'une session agent.

    Créée → Active ↔ Idle → Expirée | Fermée

    - CREATED :  session fraîche, pas encore assignée à un worker
    - ACTIVE  :  session en cours d'utilisation par un agent
    - IDLE    :  session inactive (timeout potentiel)
    - EXPIRED :  session expirée après inactivité prolongée
    - CLOSED  :  session fermée proprement
    """
    CREATED = auto()
    ACTIVE = auto()
    IDLE = auto()
    EXPIRED = auto()
    CLOSED = auto()


@dataclass
class Session:
    """
    Représentation complète d'une session agent.

    Chaque session est associée à un agent unique et contient :
      - Un identifiant UUID
      - Le chemin vers son fichier de cookies
      - Le proxy qui lui a été attribué
      - Les métadonnées temporelles (création, dernière activité)
      - Un dictionnaire extensible de métadonnées métier

    L'isolation des sessions est la clé de voûte du système :
    chaque agent possède son propre fichier cookies, son proxy,
    et son contexte navigateur.
    """

    session_id: str                           # UUID unique de la session
    agent_id: str                            # Référence vers l'agent propriétaire
    state: SessionState = SessionState.CREATED

    # Horodatages pour le suivi d'activité
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    # Ressources isolées
    cookie_file: str = ""                     # Chemin vers agents_data/<agent>/cookies.json
    proxy_url: str = ""                       # URL du proxy assigné

    # Stockage extensible pour données annexes
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Propriétés calculées
    # ------------------------------------------------------------------

    @property
    def age_seconds(self) -> float:
        """Âge de la session en secondes depuis sa création."""
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        """Temps écoulé depuis la dernière activité enregistrée."""
        return time.time() - self.last_active

    def is_expired(self, max_idle: int = 600) -> bool:
        """
        Vérifie si la session a dépassé le seuil d'inactivité.

        Paramètres
        ----------
        max_idle : int
            Durée maximale d'inactivité en secondes (défaut : 600s = 10 min).

        Retourne True si la session doit être considérée comme expirée.
        """
        return self.idle_seconds > max_idle

    def touch(self):
        """
        Marque un regain d'activité sur la session.

        Met à jour `last_active` et rebascule l'état de IDLE → ACTIVE
        si la session était en sommeil.
        """
        self.last_active = time.time()
        if self.state == SessionState.IDLE:
            self.state = SessionState.ACTIVE


class SessionManager:
    """
    Gestionnaire central des sessions agents.

    Responsabilités :
      - Créer des sessions isolées (chaque agent a son répertoire dédié)
      - Sauvegarder / restaurer les cookies depuis le disque
      - Retrouver une session active par agent_id
      - Nettoyer les sessions expirées
      - Assurer la persistance entre les redémarrages du système

    Structure des répertoires :
        agents_data/
        ├── scraper_01/
        │   └── cookies.json
        ├── analyst_01/
        │   └── cookies.json
        └── publisher_01/
            └── cookies.json
    """

    def __init__(self, data_dir: str = "agents_data"):
        """
        Initialise le gestionnaire.

        Paramètres
        ----------
        data_dir : str
            Chemin racine où sont stockés les répertoires de sessions.
            Créé automatiquement s'il n'existe pas.
        """
        self._sessions: dict[str, Session] = {}   # index : session_id → Session
        self._data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # CRUD des sessions
    # ------------------------------------------------------------------

    def create(self, agent_id: str, proxy_url: str = "") -> Session:
        """
        Crée une nouvelle session pour un agent donné.

        - Génère un UUID unique comme identifiant de session.
        - Crée le répertoire dédié si absent : agents_data/<agent_id>/
        - Configure le fichier de cookies : agents_data/<agent_id>/cookies.json

        Paramètres
        ----------
        agent_id  : str
            Identifiant de l'agent propriétaire.
        proxy_url : str
            URL du proxy assigné à cette session (optionnel).

        Retourne l'instance Session créée.
        """
        session_id = str(uuid.uuid4())
        agent_dir = os.path.join(self._data_dir, agent_id)
        os.makedirs(agent_dir, exist_ok=True)

        session = Session(
            session_id=session_id,
            agent_id=agent_id,
            cookie_file=os.path.join(agent_dir, "cookies.json"),
            proxy_url=proxy_url,
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        """
        Récupère une session par son UUID.

        Retourne None si la session n'existe pas.
        """
        return self._sessions.get(session_id)

    def get_by_agent(self, agent_id: str) -> Optional[Session]:
        """
        Retourne la session active d'un agent, ou None.

        Parcourt les sessions pour trouver celle dont l'agent_id
        correspond et dont l'état est ACTIVE ou CREATED.
        Un agent ne possède qu'une seule session active à la fois.
        """
        for s in self._sessions.values():
            if s.agent_id == agent_id and s.state in (
                SessionState.ACTIVE, SessionState.CREATED
            ):
                return s
        return None

    def close(self, session_id: str):
        """
        Ferme une session en basculant son état à CLOSED.

        La session reste dans l'index (consultable) mais n'est
        plus considérée comme active.
        """
        session = self._sessions.get(session_id)
        if session:
            session.state = SessionState.CLOSED

    # ------------------------------------------------------------------
    # Persistance des cookies
    # ------------------------------------------------------------------

    def save_cookies(self, session_id: str, cookies: list[dict]):
        """
        Sauvegarde les cookies d'une session sur le disque.

        Le fichier est stocké à l'emplacement défini dans Session.cookie_file,
        soit : agents_data/<agent_id>/cookies.json

        Paramètres
        ----------
        session_id : str
            UUID de la session cible.
        cookies    : list[dict]
            Liste des cookies au format standard navigateur.
        """
        session = self.get(session_id)
        if session:
            # Création atomique : écriture dans un fichier tampon puis rename
            # (simplifié ici en écriture directe pour la clarté)
            with open(session.cookie_file, "w") as f:
                json.dump(cookies, f, indent=2)

    def load_cookies(self, session_id: str) -> list[dict]:
        """
        Restaure les cookies d'une session depuis le disque.

        Retourne une liste vide si :
          - la session n'existe pas, ou
          - le fichier de cookies est absent (première exécution).

        Paramètres
        ----------
        session_id : str
            UUID de la session cible.

        Retourne
        --------
        list[dict] : cookies désérialisés ou liste vide.
        """
        session = self.get(session_id)
        if session and os.path.exists(session.cookie_file):
            with open(session.cookie_file) as f:
                return json.load(f)
        return []

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def cleanup_expired(self, max_idle: int = 600):
        """
        Parcourt toutes les sessions et marque comme EXPIRED celles
        qui dépassent le seuil d'inactivité.

        À appeler périodiquement depuis une tâche de fond.

        Paramètres
        ----------
        max_idle : int
            Durée maximale d'inactivité en secondes (défaut : 600).
        """
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired(max_idle)
        ]
        for sid in expired:
            self._sessions[sid].state = SessionState.EXPIRED

    # ------------------------------------------------------------------
    # Propriétés d'inspection
    # ------------------------------------------------------------------

    @property
    def active_count(self) -> int:
        """Nombre de sessions actuellement actives ou créées."""
        return sum(
            1 for s in self._sessions.values()
            if s.state in (SessionState.ACTIVE, SessionState.CREATED)
        )

    @property
    def all_sessions(self) -> list[Session]:
        """Liste complète de toutes les sessions (quel que soit l'état)."""
        return list(self._sessions.values())
