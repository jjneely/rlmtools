import os
import optparse

import rlmtools.configDragon as configDragon
import rlmtools.constants as constants

def main():
    global config
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=constants.defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    parser.add_option("-a", "--auth", action="store", default=None,
                      dest="auth", 
                      help="The webapp will pretend you are this user.")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases
    configDragon.initConfig(options.configfile)

    # Load up the webapp module
    import rlmtools
    rlmtools.config = configDragon.config

    # Handle testing harness authN
    if options.auth is not None:
        rlmtools.config.vars['auth'] = ["", False]
        rlmtools.config.auth = options.auth

    #rlmtools.app.run(host="0.0.0.0", debug=True)
    rlmtools.app.run(debug=True)


if __name__ == "__main__":
    main()

