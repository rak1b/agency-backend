import sys, os

# Passenger on cPanel runs the default python, which is python 2
# so the first thing we do is force a switch to python3 in the virtualenv

INTERP = "/home/payinpos/inventory.payinpos.com/venv/bin/python"

if sys.executable != INTERP: os.execl(INTERP, INTERP, *sys.argv)

import Config.wsgi
application = Config.wsgi.application