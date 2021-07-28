import importlib
import sys
from unittest import mock

class MockConfig:
	def __init__(self):
		self.bot = mock.MagicMock()
		self.state = mock.Mock()

def set_up_class(cls, *module_names):
	mock_config = MockConfig()
	sys.modules['config'] = mock_config
	try:
		for module_name in module_names:
			module = importlib.import_module(module_name)
			setattr(cls, module_name, module)
	except Exception:
		del sys.modules['config']
		raise

def tear_down_class(cls):
	del sys.modules['config']
