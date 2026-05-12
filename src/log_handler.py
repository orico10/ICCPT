import logging
import os
from src import config

class LogHandler:
    USER_LEVEL = 35


    @staticmethod
    def _add_user_level():
        """
        Define a new log level 'USER'.
        """
        logging.addLevelName(LogHandler.USER_LEVEL, "USER")

        def user(self, message, *args, **kwargs):
            if self.isEnabledFor(LogHandler.USER_LEVEL):
                self._log(LogHandler.USER_LEVEL, message, args, **kwargs)

        logging.Logger.user = user

    @staticmethod
    def configure_logs():
        logs_config = config["logs"]
        os.makedirs(os.path.dirname(config["path"]["logs"]["general"]), exist_ok=True)

        # Añadir nivel USER antes de configurar los logs
        LogHandler._add_user_level()

        logging.basicConfig(
            level= LogHandler.USER_LEVEL,#getattr(logging, logs_config["level"].upper()),
            format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",  # Incluye el método
            handlers=[
                logging.FileHandler(config["path"]["logs"]["general"], mode="w"),
                logging.StreamHandler()
            ]
        )
        #logging.info("Sistema de logging configurado correctamente.")
        logger = logging.getLogger(__name__)
        logger.user("LogHandler configured with USER level.")
