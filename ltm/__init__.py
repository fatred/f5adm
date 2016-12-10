import yaml
import os

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

with open(os.path.join(__location__, 'template.yaml'), 'r') as stream:
    try:
        template = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)

with open(os.path.join(__location__, "ltm.yaml"), 'r') as stream:
    try:
        ltmconfig = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)


def load_defaults(**kwargs):
    if kwargs['objtype'] == 'Node':
        defaults = template['Defaults']['Nodes']
    elif    kwargs['objtype'] == 'Pool':
        defaults = template['Defaults']['Pools']
    elif kwargs['objtype'] == 'VirtualServer':
        defaults = template['Defaults']['VirtualServers']
    else:
        defaults = {}
    return defaults


class Node:
    def __init__(self, **kwargs):
        self.settings = {}
        self.defaults = {}

        # first init the node with yaml defaults
        self.defaults.update(load_defaults(objtype='Node'))
        self.settings.update(self.defaults)

        # populate the Node params with things we passed in on the object creation
        if kwargs is not None: self.settings.update(kwargs)

    def refresh_defaults(self):
        self.defaults = load_defaults(objtype='Node')
        self.settings.update(self.defaults)

    def refresh(self, **kwargs):
        if kwargs is not None: self.settings.update(kwargs)


class Pool:
    def __init__(self, **kwargs):
        self.settings = {}
        self.defaults = {}

        # first init the pool with defaults
        self.defaults = load_defaults(objtype='Pool')
        self.settings.update(self.defaults)

        # populate the pool params with things we passed in
        if kwargs is not None: self.settings.update(kwargs)

    def refresh_defaults(self):
        self.defaults.update(load_defaults(objtype='Pool'))
        self.settings.update(self.defaults)

    def refresh(self, **kwargs):
        if kwargs is not None: self.settings.update(kwargs)

    def add_member(self, node):
        if not self.settings.__contains__('Members'):
            self.settings['Members'] = node.settings
        else:
            self.settings['Members'].update(node.settings)


class VirtualServer:
    def __init__(self, **kwargs):
        self.settings = {}
        self.defaults = {}

        # first init the VIP with defaults
        self.defaults.update(load_defaults(objtype='VirtualServer'))
        self.settings.update(self.defaults)

        # populate the VIP params with things we passed in
        if kwargs is not None: self.settings.update(kwargs)

    def refresh_defaults(self):
        self.defaults.update(load_defaults(objtype='VirtualServer'))
        self.settings.update(self.defaults)

    def refresh(self, **kwargs):
        if kwargs is not None: self.settings.update(kwargs)

    def set_pool(self, pool):
        self.settings['pool'] = pool.settings
