import logging
from datetime import datetime


class Logger:
    def __init__(self, name=datetime.now().strftime('%Y-%m-%d') + '.log', format='%(asctime)s - %(levelname)s - %(message)s'):
        # build logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # log to file
        fh = logging.FileHandler(name)
        fh.setLevel(logging.DEBUG)

        # log to console
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # format logger
        formatter = logging.Formatter(format)
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        self.logger = logger

    def info(self, url='', msg=''):
        self.logger.info('%s - %s' % (url, msg))

    def error(self, url='', msg=''):
        self.logger.error('%s - %s' % (url, msg))