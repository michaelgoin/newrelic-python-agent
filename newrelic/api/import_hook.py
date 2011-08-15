import os
import sys
import imp

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

_import_hooks = {}

def register_import_hook(name, callable):
    imp.acquire_lock()

    try:
        hooks = _import_hooks.get(name, None)

        if not name in _import_hooks or hooks is None:

            # If no entry in registry or entry already flagged with
            # None then module may have been loaded, in which case
            # need to check and fire hook immediately.

            hooks = _import_hooks.get(name)

            module = sys.modules.get(name, None)

            if module is not None:

                # The module has already been loaded so fire hook
                # immediately.

                _import_hooks[name] = None

                callable(module)

            else:

                # No hook has been registered so far so create list
                # and add current hook.

                _import_hooks[name] = [callable]
            
        else:

	  # Hook has already been registered, so append current
	  # hook.

          _import_hooks[name].append(callable)

    finally:
        imp.release_lock()

def _notify_import_hooks(name, module):

    # Is assumed that this function is called with the global
    # import lock held. This should be the case as should only
    # be called from load_module() of the import hook loader.

    hooks = _import_hooks.get(name, None)

    if hooks is not None:
        _import_hooks[name] = None

        for callable in hooks:
            callable(module)

class _ImportHookLoader:

    def load_module(self, fullname):

        # Call the import hooks on the module being handled.

        module = sys.modules[fullname]
        _notify_import_hooks(fullname, module)

        return module

class ImportHookFinder:

    def __init__(self):
        self._skip = {}

    def find_module(self, fullname, path=None):

        # If not something we are interested in we can return.

        if not fullname in _import_hooks:
            return None

	# Check whether this is being called on the second time
	# through and return.

        if fullname in self._skip:
            return None

	# We are now going to call back into import. We set a
	# flag to see we are handling the module so that check
	# above drops out on subsequent pass and we don't go
	# into an infinite loop.

        self._skip[fullname] = True

        try:
            __import__(fullname)
        finally:
            del self._skip[fullname]

	# If we get this far then the module we are interested
	# in does actually exist and so return our loader to
	# trigger import hooks and then return the module.

        return _ImportHookLoader()

def import_hook(name):
    def decorator(wrapped):
        register_import_hook(name, wrapped)
        return wrapped
    return decorator

def import_module(name):
    __import__(name)
    return sys.modules[name]

if not _agent_mode in ('ungud', 'julunggul'):
    import _newrelic
    register_import_hook = _newrelic.register_import_hook
    import_hook = _newrelic.import_hook
    import_module = _newrelic.import_module
    ImportHookFinder = _newrelic.ImportHookFinder
