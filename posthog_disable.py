"""
PostHog Disable Module

Simple module that provides dummy PostHog functionality.
Since PostHog has been uninstalled, this module just provides dummy functions
to ensure any code that tries to use PostHog will continue to work without errors.

This implementation uses a simpler approach that won't interfere with other imports.
"""

import os
import sys
import logging
import types

# Set environment variables to disable PostHog
os.environ["POSTHOG_DISABLED"] = "1"
os.environ["DISABLE_POSTHOG"] = "true"
os.environ["POSTHOG_DEBUG"] = "0"
os.environ["POSTHOG_LOG_LEVEL"] = "CRITICAL"
os.environ["POSTHOG_HOST"] = "localhost"
os.environ["POSTHOG_API_KEY"] = "fake_key_that_will_never_work"

# Silence any PostHog logging
logging.getLogger('posthog').setLevel(logging.CRITICAL)
logging.getLogger('posthog').propagate = False
logging.getLogger('posthog').disabled = True
logging.getLogger('posthog').addHandler(logging.NullHandler())

# Create a dummy PostHog class that does nothing
class DummyPostHog:
    def __init__(self, *args, **kwargs):
        pass
        
    def capture(self, *args, **kwargs):
        return None
        
    def identify(self, *args, **kwargs):
        return None
        
    def group(self, *args, **kwargs):
        return None
        
    def alias(self, *args, **kwargs):
        return None
        
    def page(self, *args, **kwargs):
        return None
        
    def debug(self, *args, **kwargs):
        return None
        
    def feature_enabled(self, *args, **kwargs):
        return False
        
    def get_feature_flag(self, *args, **kwargs):
        return None
        
    def get_all_flags(self, *args, **kwargs):
        return {}
        
    def shutdown(self, *args, **kwargs):
        return None
        
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

# Create a dummy Client class
class Client(DummyPostHog):
    pass

# Create a dummy posthog module
dummy_posthog = types.ModuleType('posthog')
dummy_posthog.__file__ = __file__
dummy_posthog.__path__ = []
dummy_posthog.__package__ = 'posthog'

# Add all the dummy classes and functions to the module
dummy_posthog.posthog = DummyPostHog()
dummy_posthog.Posthog = DummyPostHog
dummy_posthog.Client = Client

# Add a __getattr__ function to handle any other attributes
def __getattr__(name):
    if name.startswith('__'):
        raise AttributeError(name)
    return lambda *args, **kwargs: None

dummy_posthog.__getattr__ = __getattr__

# Register the dummy module in sys.modules
sys.modules['posthog'] = dummy_posthog

# Handle any existing posthog submodules
for module_name in list(sys.modules.keys()):
    if module_name.startswith('posthog.') and module_name != 'posthog':
        # Create a dummy submodule
        submodule_name = module_name.split('.')[-1]
        dummy_submodule = types.ModuleType(module_name)
        dummy_submodule.__file__ = __file__
        dummy_submodule.__package__ = module_name
        dummy_submodule.__getattr__ = __getattr__
        
        # Register the dummy submodule
        sys.modules[module_name] = dummy_submodule

# Create a dummy instance for direct imports
posthog = DummyPostHog()

# Print a message to confirm the module is loaded
print("PostHog analytics disabled without affecting other imports")
