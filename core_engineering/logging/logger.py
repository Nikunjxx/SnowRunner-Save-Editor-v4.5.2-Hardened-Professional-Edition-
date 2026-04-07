# [PH4-LOG-001] Structured Session Logger
import logging
from logging.handlers import RotatingFileHandler
import os
import json
from datetime import datetime

class AppLogger:
    """
    Mission-Critical Observability Engine.
    Captures every system action with full context.
    """
    
    def __init__(self):
        # [PH4-PROD-LOG] Environment-Aware Pathing
        app_data = os.getenv('APPDATA')
        if app_data:
            self.log_dir = os.path.join(app_data, "SnowRunnerEditor", "logs")
        else:
            self.log_dir = os.path.abspath("logs")

        os.makedirs(self.log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.log_dir, f"session_{timestamp}.log")

        self.logger = logging.getLogger("snowrunner_app")
        self.logger.setLevel(logging.INFO)

        # [PH4-LOG-ROT] Lifecycle Management (1MB max, 3 backups)
        handler = RotatingFileHandler(filename, maxBytes=1*1024*1024, backupCount=3)
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def info(self, message, context=None, severity="INFO"):
        self.logger.info(self._format(message, context, severity))

    def error(self, message, context=None, severity="ERROR"):
        self.logger.error(self._format(message, context, severity))

    def _format(self, message, context, severity):
        data = {
            "time": datetime.now().isoformat(),
            "level": severity,
            "msg": message,
            "ctx": context or {}
        }
        return json.dumps(data)

# [PH4-LOG-SINGLE] Centralized Logging Identity
app_logger = AppLogger()
