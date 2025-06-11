from Backend import HighLevelControl
from Agilent_Controller_RS232 import Agilent33250A

"""HighLevelControl.initialize_hardware()
HighLevelControl.n_burst_series(10)"""

Instance = Agilent33250A()
Instance.set_burst_mode()
