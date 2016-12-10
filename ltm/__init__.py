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
    elif kwargs['objtype'] == 'Pool':
        defaults = template['Defaults']['Pools']
    elif kwargs['objtype'] == 'VirtualServer':
        defaults = template['Defaults']['VirtualServer']
    else:
        defaults = {}
    return defaults


class Node(dict):
    def __init__(self, **kwargs):
        # super the dict stuff in
        super(Node, self).__init__(**kwargs)

        # first init the node with yaml defaults
        defaults = load_defaults(objtype='Node')
        self.update(defaults)

        # populate the Node params with things we passed in on the object creation
        self.update(kwargs)


class Pool(object):
    def __init__(self, **kwargs):
        # super the dict stuff in
        super(Pool, self).__init__(**kwargs)

        # first init the pool with defaults
        defaults = load_defaults(objtype='Pool')
        self.update(defaults)

        # populate the pool params with things we passed in
        self.update(kwargs)


class VirtualServer(object):
    def __init__(self, **kwargs):
        # super the dict stuff in
        super(VirtualServer, self).__init__(**kwargs)

        # first init the VIP with defaults
        defaults = load_defaults(objtype='VirtualServer')
        self.update(defaults)

        # populate the VIP params with things we passed in
        self.update(kwargs)

