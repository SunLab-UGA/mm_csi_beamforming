# this is the main file which test the functions with a new pyi interface and wrapper

import os
import sys

# Add the project root to the PYTHONPATH
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
tlkServicePath = './TLKCore/lib' # Path to give the TLKCoreService for initialization

# Now use an absolute import
from TLKCore.lib.tlkcore.TLKCoreService import TLKCoreService

# Create an instance of TLKCoreService
service = TLKCoreService(tlkServicePath)
