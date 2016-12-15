from f5.bigip import ManagementRoot
import yaml
import os
# TODO: EVERYTHING!!!
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

with open(os.path.join(__location__, "vip_request.yaml"), 'r') as stream:
    try:
        vip_request = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)


def load_defaults(**kwargs):
    if kwargs['objtype'] == 'Node':
        defaults = template['Defaults']['Nodes']
    elif kwargs['objtype'] == 'Pool':
        defaults = template['Defaults']['Pools']
    elif kwargs['objtype'] == 'VirtualServer':
        defaults = template['Defaults']['VirtualServers']
    else:
        defaults = {}
    return defaults

mgmt = ManagementRoot(ltmconfig['LTM1']['IP'], ltmconfig['LTM1']['Username'], ltmconfig['LTM1']['Password'])

# Create a new pool on the BIG-IP
mypool = mgmt.tm.ltm.pools.pool.create(name='horsepool', partition='Common')

# Load an existing pool and update its description
pool_a = mgmt.tm.ltm.pools.pool.load(name='horsepool', partition='Common')
pool_a.description = "New description"
pool_a.update()

# Delete a pool if it exists
if mgmt.tm.ltm.pools.pool.exists(name='horsepool', partition='Common'):
    pool_b = mgmt.tm.ltm.pools.pool.load(name='horsepool', partition='Common')
    pool_b.delete()
