import ConfigParser
import logging
import logging.handlers
import os

import constants

logger = logging.getLogger("rlmclient")
init_logging = True

class Parser(ConfigParser.ConfigParser):

    def get(self, section, option, default):
        """
        Override ConfigParser.get: If the request option is not in the
        config file then return the value of default rather than raise
        an exception.  We still raise exceptions on missing sections.
        """
        try:
            return ConfigParser.ConfigParser.get(self, section, option)
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return default


def initConfig(config_files=constants.defaultConfFiles):
    global init_logging
    if not init_logging: return

    parser = Parser()
    parser.read(config_files)

    logfile = parser.get('main', 'logfile', constants.logfile)
    level = int(parser.get('main', 'log_level', constants.log_level))
    URL = parser.get('client', 'URL', constants.URL)
    logger = logging.getLogger("rlmclient")

    def syslogHandler():
        # When syslog isn't running we need to catch the socket errors
        try:
            return logging.handlers.SysLogHandler("/dev/log")
        except:
            return logging.StreamHandler()

    fileError = None
    if logfile == '-':
        handler = logging.StreamHandler()
    elif logfile == '':
        handler = syslogHandler()
    else:
        if not os.access(logfile, os.W_OK):
            fileError = "IO Error accessing: %s" % logfile
            handler = syslogHandler()
        else:
            handler = logging.FileHandler(logfile)

    # Time format: Jun 24 10:16:54
    formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s',
            '%b %2d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    if fileError is not None:
        logger.warning(fileError)

    init_logging = False
    return URL

if __name__ == "__main__":
    URL = initConfig()
    logger.info("Test rlmclient initConfig() INFO")
    logger.warning("Test rlmclient initConfig() WARNING")
    logger.critical("Test rlmclient initConfig() CRIT")

