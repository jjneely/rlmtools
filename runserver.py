import os
import optparse

def main():
    # Load up the webapp module
    import rlmtools

    #rlmtools.app.run(host="0.0.0.0", debug=True)
    rlmtools.app.run(debug=True)


if __name__ == "__main__":
    main()

