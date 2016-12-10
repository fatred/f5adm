import yaml

with open('template.yaml', 'r') as stream:
    try:
        template = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)

with open("ltm.conf", 'r') as stream:
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


class Node(object):
    def __init__(self, **kwargs):
        # first init the node with defaults
        defaults = load_defaults(objtype='Node')
        for (k, v) in defaults.items():
            setattr(self, k, v)
        # populate the Node params with things we passed in
        for (k, v) in kwargs:
            setattr(self, k, v)


class Pool(object):
    def __init__(self, **kwargs):
        # first init the pool with defaults
        defaults = load_defaults(objtype='Pool')
        for (k, v) in defaults.items():
            setattr(self, k, v)
        # populate the pool params with things we passed in
        for (k, v) in kwargs:
            setattr(self, k, v)


class VirtualServer(object):
    def __init__(self, **kwargs):
        # first init the VIP with defaults
        defaults = load_defaults(objtype='VirtualServer')
        for (k, v) in defaults.items():
            setattr(self, k, v)
        # populate the VIP params with things we passed in
        for (k, v) in kwargs:
            setattr(self, k, v)

