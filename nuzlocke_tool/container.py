from dependency_injector import containers, providers

from nuzlocke_tool.data_loader import GameDataLoader
from nuzlocke_tool.services.journal_service import JournalService
from nuzlocke_tool.services.save_service import SaveService


class Container(containers.DeclarativeContainer):
    game_data_loader = providers.Singleton(GameDataLoader)
    journal_service_factory = providers.Factory(JournalService)
    save_service = providers.Singleton(SaveService)
