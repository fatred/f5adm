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
        pass
    elif kwargs['objtype'] == 'Pool':
        pass
    elif kwargs['objtype'] == 'VirtualServer':
        pass
    return dict


class Node(object):
    def __init__(self, **kwargs):
        # first init the node with defaults
        defaults = load_defaults(objtype='Node')
        for (k, v) in defaults.items():
            setattr(self, k, v)
        # populate the Node params with things we passed in
        for (k, v) in kwargs:
            setattr(self, k, v)

