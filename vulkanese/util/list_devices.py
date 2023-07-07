import os
import sys
import numpy as np
import pkg_resources
import json

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(here, "..", "..")))

import vulkanese as ve

# get vulkanese instance
instance_inst = ve.instance.Instance(verbose=False)
print(json.dumps(instance_inst.getDeviceList(), indent=2))
instance_inst.release()
#
