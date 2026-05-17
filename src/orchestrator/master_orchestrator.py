import asyncio
import logging
from collections import defaultdict
from typing import Optional

from src.agents import BaseAgent, ScraperAgent, AnalystAgent, PublisherAgent, Task
from src.agents.base_agent import AgentStatus
from src.browser import BrowserManager, ProxyManager
from src.config.settings import AgentConfig, settings
from src.orchestrator.session_manager import SessionManager, SessionState


class MasterOrchestrator:
    """
    Orchestrateur principal — le coeur du système multi-agents.

    Rôles :
      - Enregistrer et gérer les agents autonomes (Scraper, Analyst, Publisher…).
      - Recevoir des tâches (Task) via une file prioritaire asynchrone.
      - Distribuer ces tâches aux agents compétents en mode concurrent (asyncio).
      - Assurer l'isolation des sessions (cookies, proxies, contexte navigateur).
      - Surveiller le cycle de vie : soumission → exécution → reprise sur échec → résultats.
    """

    def __init__(self):
        # Journaliseur dédié pour tracer l'activité de l'orchestrateur
        self.logger = logging.getLogger("orchestrator.master")

        # Sous-systèmes spécialisés
        self.session_manager = SessionManager()       # cycles de vie des sessions
        self.proxy_manager = ProxyManager()            # rotation et isolation des proxies
        self.browser_manager = BrowserManager()        # contextes navigateur isolés

        # Dictionnaire des agents enregistrés (agent_id → instance BaseAgent)
        self._agents: dict[str, BaseAgent] = {}

        # File d'attente prioritaire (tri par task.priority, FIFO pour priorité égale)
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=settings.task_queue_size
        )

        # Drapeau de fonctionnement (les boucles worker tournent tant que True)
        self._running = False

        # Compteur de tâches encore en file ou en cours (permet l'arrêt propre)
        self._pending_tasks: int = 0

        # Résultats groupés par agent
        self._results: dict[str, list[Task]] = defaultdict(list)

        # Registre des types d'agents : le préfixe de l'agent_id détermine la classe instanciée
        self._agent_registry: dict[str, type[BaseAgent]] = {
            "scraper":   ScraperAgent,
            "analyst":   AnalystAgent,
            "publisher": PublisherAgent,
        }

    # ------------------------------------------------------------------
    # Gestion des types d'agents
    # ------------------------------------------------------------------

    def register_agent_type(self, name: str, cls: type[BaseAgent]):
        """
        Enregistre un nouveau type d'agent dans le registre interne.
        Permet d'étendre le système sans modifier le code noyau.

        Paramètres
        ----------
        name : str
            Identifiant court du type (ex: "curator", "monitor").
        cls  : type[BaseAgent]
            Classe fille de BaseAgent à instancier pour ce type.
        """
        self._agent_registry[name] = cls

    # ------------------------------------------------------------------
    # Gestion des agents
    # ------------------------------------------------------------------

    def add_agent(self, config: AgentConfig) -> BaseAgent:
        """
        Crée et enregistre un agent à partir de sa configuration.

        Le type est déduit du préfixe du nom (ex: "scraper_01" → ScraperAgent).
        La configuration doit contenir au minimum un agent_id unique.

        Retourne l'instance de l'agent créé.
        """
        # Extraction du type : "scraper_alpha" -> "scraper"
        agent_type = config.agent_id.split("_")[0]
        cls = self._agent_registry.get(agent_type, ScraperAgent)
        agent = cls(config)
        self._agents[config.agent_id] = agent
        self.logger.info(f"Agent enregistré : {config.agent_id} (type={agent_type})")
        return agent

    def remove_agent(self, agent_id: str):
        """Retire un agent du dictionnaire. Aucun effet s'il n'existe pas."""
        self._agents.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Retourne l'instance d'agent par son identifiant, ou None."""
        return self._agents.get(agent_id)

    # ------------------------------------------------------------------
    # Soumission de tâches
    # ------------------------------------------------------------------

    async def submit_task(self, task: Task):
        """
        Ajoute une tâche dans la file prioritaire et incrémente le
        compteur de tâches en attente.

        Les workers asynchrones piochent dans cette file dès qu'ils
        sont disponibles.
        """
        # asyncio.PriorityQueue trie par le premier élément du tuple
        await self._task_queue.put((task.priority, task))
        self._pending_tasks += 1
        self.logger.info(f"Tâche mise en file : {task.id} ({task.action})")

    # ------------------------------------------------------------------
    # Worker asynchrone (un par agent actif)
    # ------------------------------------------------------------------

    async def _worker(self, agent_id: str):
        """
        Boucle de traitement propre à un agent.

        1. Récupère ou crée une session isolée (cookies, proxy).
        2. Attache un contexte navigateur dédié.
        3. Boucle : pioche une tâche → vérifie la compatibilité → exécute.
        4. Gère les reprises (retry) en cas d'échec transitoire.
        5. Sort proprement quand `_running` passe à False et que le
           compteur de tâches est à zéro.
        """
        agent = self._agents[agent_id]

        # --- Initialisation de la session ---
        session = self.session_manager.get_by_agent(agent_id)
        if not session:
            proxy = self.proxy_manager.get_for_agent(agent_id)
            session = self.session_manager.create(
                agent_id,
                proxy.url if proxy else ""
            )
            session.state = SessionState.ACTIVE

        # Liaison session ⇔ agent
        agent.session_id = session.session_id
        await agent.attach_browser(
            await self.browser_manager.assign_context(agent.config)
        )

        # Chargement des cookies existants (précédente session)
        cookies = self.session_manager.load_cookies(session.session_id)
        self.logger.info(
            f"Worker démarré pour {agent_id} "
            f"(session={session.session_id}, cookies={len(cookies)})"
        )

        # --- Boucle de traitement ---
        while self._running:
            try:
                # Attente bloquante avec timeout (évite de lock le worker)
                priority, task = await asyncio.wait_for(
                    self._task_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                # Si toutes les tâches sont terminées et file vide, on sort
                if self._pending_tasks == 0 and self._task_queue.empty():
                    break
                continue

            # Routage : si l'agent ne correspond pas au type demandé,
            # on remet la tâche dans la file pour un autre worker.
            if task.agent_type != "any" and task.agent_type not in agent_id:
                await self._task_queue.put((priority, task))
                await asyncio.sleep(0.1)  # cède la main
                continue

            # --- Exécution ---
            self.logger.info(f"Agent {agent_id} exécute la tâche {task.id}")
            try:
                result = await agent.run(task)
                task.result = result
                self._results[agent_id].append(task)
                self.logger.info(f"Tâche {task.id} terminée par {agent_id}")
            except Exception as e:
                self.logger.error(
                    f"Tâche {task.id} échouée pour {agent_id} : {e}"
                )
                task.error = str(e)
                task.retry_count += 1

                # Reprise automatique (jusqu'à max_retries épuisé)
                if not task.is_expired:
                    await self._task_queue.put((priority, task))
                else:
                    self._results[agent_id].append(task)
            finally:
                # Décrémentation sécurisée du compteur
                self._pending_tasks = max(0, self._pending_tasks - 1)

        # --- Nettoyage ---
        await agent.detach_browser()

    # ------------------------------------------------------------------
    # Cycle de vie : start / stop / run_batch
    # ------------------------------------------------------------------

    async def start(self, concurrency: int = 3):
        """
        Lance les workers asynchrones en parallèle.

        Paramètres
        ----------
        concurrency : int
            Nombre de workers simultanés (≤ nombre d'agents).
            Si concurrency < nombre d'agents, les agents non sollicités
            restent inactifs jusqu'à la prochaine session.
        """
        self._running = True
        self.logger.info(
            f"Orchestrateur démarré avec {len(self._agents)} agent(s), "
            f"concurrence={concurrency}"
        )

        workers = []
        agent_ids = list(self._agents.keys())
        for i in range(min(concurrency, len(agent_ids))):
            agent_id = agent_ids[i % len(agent_ids)]
            workers.append(asyncio.create_task(self._worker(agent_id)))

        self._workers = workers

    async def stop(self):
        """
        Arrêt progressif de l'orchestrateur.

        1. Passe le drapeau _running à False → les boucles worker se terminent.
        2. Attends la fin de tous les workers (avec tolérance aux exceptions).
        3. Ferme tous les contextes navigateur.
        4. Ferme toutes les sessions actives.
        """
        self.logger.info("Arrêt de l'orchestrateur en cours…")
        self._running = False

        if hasattr(self, "_workers"):
            await asyncio.gather(*self._workers, return_exceptions=True)

        await self.browser_manager.shutdown_all()

        for sid in list(self.session_manager._sessions.keys()):
            self.session_manager.close(sid)

        self.logger.info("Orchestrateur arrêté.")

    async def run_batch(self, tasks: list[Task], concurrency: int = 3):
        """
        Méthode de commodité : soumet un lot de tâches, démarre
        l'orchestrateur, attend la complétion, puis arrête proprement.

        Paramètres
        ----------
        tasks       : list[Task]
            Liste des tâches à exécuter.
        concurrency : int
            Degré de parallélisme (défaut : 3).
        """
        for t in tasks:
            await self.submit_task(t)

        await self.start(concurrency=concurrency)

        # Attente active : on reste en vie tant qu'il reste des tâches
        # en file ou en cours de traitement.
        while self._running and (
            self._pending_tasks > 0 or not self._task_queue.empty()
        ):
            await asyncio.sleep(0.5)

        await self.stop()

    # ------------------------------------------------------------------
    # Propriétés d'inspection (utilisées par l'interface graphique)
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """L'orchestrateur est-il en cours d'exécution ?"""
        return self._running

    @property
    def pending_tasks(self) -> int:
        """Nombre de tâches encore en file ou en cours d'exécution."""
        return self._pending_tasks

    @property
    def queue_empty(self) -> bool:
        """La file de tâches est-elle vide ?"""
        return self._task_queue.empty()

    # ------------------------------------------------------------------
    # Consultation des résultats et statistiques
    # ------------------------------------------------------------------

    def get_agent_stats(self) -> dict:
        """
        Retourne un dictionnaire {agent_id → statistiques} pour chaque
        agent enregistré (tâches réussies, échouées, statut actuel).
        """
        return {aid: agent.stats for aid, agent in self._agents.items()}

    def get_results(self, agent_id: Optional[str] = None) -> dict:
        """
        Retourne les résultats des tâches exécutées.

        Si `agent_id` est fourni, filtre les résultats pour cet agent.
        Sinon, retourne l'intégralité des résultats groupés par agent.
        """
        if agent_id:
            return {agent_id: self._results.get(agent_id, [])}
        return dict(self._results)
