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


class Node(object):
    def __init__(self, **kwargs):
        # populate the Node params with things we passed in

        for key in kwargs:
            self[key] = kwargs[key]
