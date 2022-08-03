import logging
from logging.config import dictConfig

logging_config = dict(
    version=1,
    formatters={
        'f': {'format': '%(asctime)s | %(name)-23s | %(levelname)-5s | %(message)s'}
    },
    handlers={
        'h': {'class': 'logging.StreamHandler',
              'formatter': 'f',
              'level': logging.DEBUG,
              'stream': 'ext://sys.stdout', }
    },
    root={
        'handlers': ['h'],
        'level': logging.DEBUG,
    },
)

dictConfig(logging_config)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
