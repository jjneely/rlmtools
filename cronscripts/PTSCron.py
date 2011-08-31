import rlmtools.miscServer as miscServer
import rlmtools.configDragon as configDragon
import optparse

from rlmtools.constants import defaultConfFiles

def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases
    configDragon.initConfig(options.configfile)
    m = miscServer.MiscServer()
    m.watchPTS()

if __name__ == "__main__":
    main()

