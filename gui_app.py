#!/usr/bin/env python3
"""
Application GUI Flet pour le Multi-Agent Orchestrator.
Tableau de bord temps réel avec console de logs intégrée.
Commande : python gui_app.py
"""

import asyncio
import logging
import queue
from datetime import datetime
from typing import Optional

import flet as ft

from src.agents import Task
from src.config.settings import AgentConfig, ProxyConfig
from src.orchestrator import MasterOrchestrator

# ---------------------------------------------------------------------------
# Gestionnaire de logs thread-safe
# ---------------------------------------------------------------------------

class _QueueLogHandler(logging.Handler):
    """
    Handler personnalisé qui ne fait qu'empiler les messages formatés
    dans une file thread-safe (queue.Queue).
    Le dépot dans l'interface Flet est fait périodiquement par une
    coroutine de fond, évitant tout problème de concurrence.
    """

    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue
        self.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record):
        try:
            self.log_queue.put(self.format(record))
        except Exception:
            pass  # ne jamais casser le logging


# ---------------------------------------------------------------------------
# Constantes UI
# ---------------------------------------------------------------------------

_COULEURS = {
    "scraper":   ft.Colors.LIGHT_BLUE_400,
    "analyst":   ft.Colors.PURPLE_400,
    "publisher": ft.Colors.ORANGE_400,
}

_ICONES = {
    "scraper":   ft.Icons.SEARCH,
    "analyst":   ft.Icons.ANALYTICS,
    "publisher": ft.Icons.PUBLISH,
}

# ---------------------------------------------------------------------------
# Application principale
# ---------------------------------------------------------------------------

def main(page: ft.Page):
    # --- Configuration de la page ---
    page.title = "Multi-Agent Orchestrator — Pilotage Centralisé"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.spacing = 20
    page.window.width = 1100
    page.window.height = 800

    # --- Références partagées entre callbacks et coroutines ---
    orchestrator: Optional[MasterOrchestrator] = None
    orchestrator_lock = asyncio.Lock()
    campagne_task: Optional[asyncio.Task] = None  # stockée dans un conteneur mutable
    _campagne_ref: list[Optional[asyncio.Task]] = [None]

    log_queue: queue.Queue = queue.Queue()

    # --- Configuration du logging vers la GUI ---
    _setup_gui_logging(log_queue)

    # ======================================================================
    # Constructions des contrôles Flet
    # ======================================================================

    # -- Console de logs --
    log_list = ft.ListView(
        auto_scroll=True,
        expand=True,
        spacing=1,
        padding=10,
    )

    log_container = ft.Container(
        content=log_list,
        border=ft.border.all(1, ft.Colors.GREY_700),
        border_radius=8,
        expand=True,
        bgcolor=ft.Colors.BLACK87,
    )

    # -- Cartes agents --
    cartes_agents = {}
    for agent_id, agent_type in [
        ("scraper_01", "scraper"),
        ("analyst_01", "analyst"),
        ("publisher_01", "publisher"),
    ]:
        carte = _cree_carte_agent(agent_id, agent_type)
        cartes_agents[agent_id] = carte

    # -- Boutons de contrôle --
    btn_lancer = ft.ElevatedButton(
        text="🚀 Lancer la campagne",
        icon=ft.Icons.PLAY_ARROW,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN_700,
            padding=20,
        ),
        on_click=lambda e: _on_lancer(
            page, btn_lancer, btn_arreter, cartes_agents,
            _campagne_ref,
        ),
    )

    btn_arreter = ft.ElevatedButton(
        text="⏹ Arrêter",
        icon=ft.Icons.STOP,
        disabled=True,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.RED_800,
            padding=20,
        ),
        on_click=lambda e: _on_arreter(
            btn_lancer, btn_arreter, _campagne_ref,
        ),
    )

    # ======================================================================
    # Mise en page
    # ======================================================================

    page.add(
        # En-tête
        ft.Row(
            controls=[
                ft.Icon(ft.Icons.AUTO_AWESOME, size=32, color=ft.Colors.AMBER_400),
                ft.Text("Multi-Agent Orchestrator", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("— Pilotage Centralisé", size=16, color=ft.Colors.GREY_400),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),

        # Cartes agents
        ft.ResponsiveRow(
            controls=[
                ft.Column(col={"sm": 12, "md": 4}, controls=[cartes_agents["scraper_01"]]),
                ft.Column(col={"sm": 12, "md": 4}, controls=[cartes_agents["analyst_01"]]),
                ft.Column(col={"sm": 12, "md": 4}, controls=[cartes_agents["publisher_01"]]),
            ],
        ),

        # Boutons
        ft.Row(
            controls=[btn_lancer, btn_arreter],
            spacing=20,
        ),

        # Console
        ft.Text("Console temps réel", size=16, weight=ft.FontWeight.BOLD),
        log_container,
    )

    # ======================================================================
    # Coroutine de fond : vidage de la queue de logs
    # ======================================================================

    async def _drain_log_queue():
        """
        Vide périodiquement la queue de logs et alimente la ListView.
        Tourne en tâche de fond tant que l'application est ouverte.
        """
        while True:
            try:
                while not log_queue.empty():
                    msg = log_queue.get_nowait()
                    log_list.controls.append(
                        ft.Text(msg, size=12, font_family="monospace", selectable=True)
                    )
                # Limite : garde les 500 dernières lignes
                if len(log_list.controls) > 500:
                    log_list.controls = log_list.controls[-300:]
                page.update()
            except Exception:
                pass
            await asyncio.sleep(0.3)

    # Lance la coroutine de fond sur la boucle asyncio de Flet
    page.run_task(_drain_log_queue)


# ===========================================================================
# Fonctions utilitaires
# ===========================================================================

def _setup_gui_logging(log_queue: queue.Queue):
    """
    Ajoute le handler personnalisé au logger racine.
    Les logs existants (flet, orchestre, agents) seront tous redirigés
    vers l'interface graphique.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Supprime les handlers existants (notamment le StreamHandler du terminal)
    for h in list(logger.handlers):
        if not isinstance(h, _QueueLogHandler):
            logger.removeHandler(h)

    logger.addHandler(_QueueLogHandler(log_queue))


def _cree_carte_agent(agent_id: str, agent_type: str) -> ft.Container:
    """
    Construit un bloc visuel représentant un agent.
    Retourne un Container qui sera mis à jour dynamiquement.
    """
    couleur = _COULEURS.get(agent_type, ft.Colors.GREY_400)
    icone = _ICONES.get(agent_type, ft.Icons.ANDROID)

    # Texte statique
    nom = ft.Text(agent_id, size=16, weight=ft.FontWeight.BOLD)
    type_label = ft.Text(f"Type : {agent_type}", size=12, color=ft.Colors.GREY_400)

    # Indicateur de statut (mis à jour en direct)
    statut = ft.Text("● Inactif", size=13, color=ft.Colors.GREY_500)

    # Statistiques (mis à jour en direct)
    stats_col = ft.Column(
        controls=[
            ft.Text("Tâches complétées : —", size=12),
            ft.Text("Tâches échouées  : —", size=12),
        ],
        spacing=2,
    )

    # On stocke les références dans le Container pour y accéder plus tard
    conteneur = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icone, size=28, color=couleur),
                        ft.Column(controls=[nom, type_label], spacing=0),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=8, color=ft.Colors.GREY_800),
                statut,
                stats_col,
            ],
            spacing=6,
        ),
        padding=15,
        border=ft.border.all(1, couleur),
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.08, couleur),
        ink=True,
    )

    # Accroche les contrôles modifiables comme attributs sur le Container
    conteneur._statut = statut
    conteneur._stats_col = stats_col

    return conteneur


# ===========================================================================
# Callbacks événementiels
# ===========================================================================

def _on_lancer(
    page: ft.Page,
    btn_lancer: ft.ElevatedButton,
    btn_arreter: ft.ElevatedButton,
    cartes_agents: dict,
    campagne_ref: list,
):
    """
    Callback du bouton "Lancer la campagne".
    Désactive le bouton, active "Arrêter", et lance la coroutine
    de campagne sur la boucle asyncio de Flet.
    """
    btn_lancer.disabled = True
    btn_arreter.disabled = False
    page.update()

    task = page.run_task(
        _run_campaign,
        page, btn_lancer, btn_arreter, cartes_agents, campagne_ref,
    )
    campagne_ref[0] = task


def _on_arreter(
    btn_lancer: ft.ElevatedButton,
    btn_arreter: ft.ElevatedButton,
    campagne_ref: list,
):
    """
    Callback du bouton "Arrêter".
    Annule la tâche asynchrone de campagne en cours.
    """
    btn_arreter.disabled = True
    task = campagne_ref[0]
    if task and not task.done():
        task.cancel()
    campagne_ref[0] = None
    btn_lancer.disabled = False
    logging.getLogger("gui").warning("⏹ Campagne interrompue par l'utilisateur")


# ===========================================================================
# Logique métier asynchrone de la campagne
# ===========================================================================

async def _run_campaign(
    page: ft.Page,
    btn_lancer: ft.ElevatedButton,
    btn_arreter: ft.ElevatedButton,
    cartes_agents: dict,
    campagne_ref: list,
):
    """
    Coroutine principale de la campagne.
    1. Crée l'orchestrateur et enregistre les agents.
    2. Soumet les tâches de démonstration.
    3. Boucle de monitoring : met à jour l'UI et vérifie l'arrêt.
    """
    logger = logging.getLogger("gui.campaign")

    orchestrator = MasterOrchestrator()

    # Configuration des agents (identique à main.py demo)
    agent_1 = AgentConfig(
        agent_id="scraper_01",
        proxy=ProxyConfig(host="127.0.0.1", port=8080),
        timezone="America/New_York",
        locale="en-US",
    )
    agent_2 = AgentConfig(
        agent_id="analyst_01",
        timezone="Europe/London",
        locale="en-GB",
    )
    agent_3 = AgentConfig(
        agent_id="publisher_01",
        timezone="Asia/Dubai",
        locale="ar-AE",
    )

    orchestrator.add_agent(agent_1)
    orchestrator.add_agent(agent_2)
    orchestrator.add_agent(agent_3)

    # Soumission des tâches
    taches = [
        Task(id="scrape-1",   agent_type="scraper",   action="extract_content",
             params={"url": "https://example.com", "selector": "h1"}, priority=1),
        Task(id="scrape-2",   agent_type="scraper",   action="extract_content",
             params={"url": "https://httpbin.org/html", "selector": "body"}, priority=1),
        Task(id="analyze-1",  agent_type="analyst",   action="keywords",
             params={"data": {"text": "Great product with amazing quality and excellent service"}}, priority=2),
        Task(id="analyze-2",  agent_type="analyst",   action="sentiment",
             params={"data": {"text": "Amazing quality, excellent service, highly recommended"}}, priority=2),
        Task(id="publish-1",  agent_type="publisher", action="post_content",
             params={"content": "Check out our latest product!", "platform": "twitter"}, priority=0),
        Task(id="publish-2",  agent_type="publisher", action="post_content",
             params={"content": "New blog post is live!", "platform": "blog"}, priority=0),
    ]

    for t in taches:
        await orchestrator.submit_task(t)

    # Démarrage de l'orchestrateur
    await orchestrator.start(concurrency=3)

    # Boucle de monitoring : met à jour les cartes et attend la fin
    try:
        while orchestrator.is_running and (
            orchestrator.pending_tasks > 0 or not orchestrator.queue_empty
        ):
            stats = orchestrator.get_agent_stats()
            for agent_id, stat in stats.items():
                carte = cartes_agents.get(agent_id)
                if carte:
                    _maj_carte(carte, stat)

            page.update()
            await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        logger.info("Campagne interrompue par l'utilisateur")
    finally:
        await orchestrator.stop()

        stats = orchestrator.get_agent_stats()
        for agent_id, stat in stats.items():
            carte = cartes_agents.get(agent_id)
            if carte:
                _maj_carte(carte, stat)

        logger.info("=== Campagne terminée ===")
        for aid, res_list in orchestrator.get_results().items():
            for t in res_list:
                etat = "OK" if t.result else f"ÉCHEC: {t.error}"
                logger.info(f"  [{etat}] {t.id}")

        btn_lancer.disabled = False
        btn_arreter.disabled = True
        page.update()


def _maj_carte(carte: ft.Container, stats: dict):
    """
    Met à jour les champs dynamiques d'une carte agent.
    `stats` est le dictionnaire retourné par BaseAgent.stats.
    """
    statut = stats.get("status", "STOPPED")
    completed = stats.get("completed", 0)
    failed = stats.get("failed", 0)

    # Couleur du statut
    couleur_statut = ft.Colors.GREY_500
    texte_statut = "● Inactif"
    if statut == "BUSY":
        couleur_statut = ft.Colors.GREEN_400
        texte_statut = "● Occupé"
    elif statut == "ERROR":
        couleur_statut = ft.Colors.RED_400
        texte_statut = "● Erreur"
    elif statut == "IDLE":
        couleur_statut = ft.Colors.AMBER_400
        texte_statut = "● En attente"

    carte._statut.value = texte_statut
    carte._statut.color = couleur_statut

    carte._stats_col.controls[0].value = f"Tâches complétées : {completed}"
    carte._stats_col.controls[1].value = f"Tâches échouées   : {failed}"


# ===========================================================================
# Point d'entrée
# ===========================================================================

if __name__ == "__main__":
    ft.app(target=main)
