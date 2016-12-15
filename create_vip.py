from f5.bigip import ManagementRoot
import yaml
import os
import pprint

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

with open(os.path.join(__location__, 'template.yaml'), 'r') as stream:
    try:
        template = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        template = None

with open(os.path.join(__location__, "ltm.yaml"), 'r') as stream:
    try:
        ltmhost= yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        ltmhost = None

with open(os.path.join(__location__, "vip_request.yaml"), 'r') as stream:
    try:
        vip_request = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        vip_request = None


def load_defaults(objtype):
    if objtype == 'Node':
        defaults = template['Defaults']['Nodes']
    elif objtype == 'Pool':
        defaults = template['Defaults']['Pools']
    elif objtype == 'VirtualServer':
        defaults = template['Defaults']['VirtualServers']
    else:
        defaults = {}
    return defaults


def connect_ltm(ltm):
    return ManagementRoot(ltm['LTM1']['IP'], ltm['LTM1']['Username'], ltm['LTM1']['Password'])


def dump_obj_dict(thing):
    # takes a thing and pretty prints it to the screen for debugging
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(thing.__dict__)


def format_name(template, name, type):
    # take a name and make it conform to the defaults
    if (type == 'Pool') or (type == 'VirtualServer'):
        # prefix first
        # check if its already prefixed with the text in the mangle rule
        chkidx = len(template['NameMangleRules'][type]['Name']['Prefix'])
        if name[0:chkidx] == template['NameMangleRules'][type]['Name']['Prefix']:
            pfx = ''
        else:
            pfx = template['NameMangleRules'][type]['Name']['Prefix']
        # suffix second
        # check if its already suffixed with the text in the mangle rule
        chkidx = len(template['NameMangleRules'][type]['Name']['Suffix'])
        if name[0:chkidx] == template['NameMangleRules'][type]['Name']['Suffix']:
            sfx = ''
        else:
            sfx = template['NameMangleRules'][type]['Name']['Suffix']
        # done
        return pfx + name + sfx
    else:
        # Nothing to do here
        return name


def merge_request_template(template, vip_request, ssl):
    # merge the request with the template and create a definitive request
    vip_defaults = load_defaults('VirtualServer')
    pool_defaults = load_defaults('Pool')
    node_defaults = load_defaults('Node')

    # gather ye rosebuds
    # vip
    vip = {}
    vip.update(vip_defaults['all'].__dict__)
    if ssl:
        vip.update(vip_defaults['443'].__dict__)
        vip.pop('HTTP_Redirect')
    else:
        vip.update(vip_defaults['80'].__dict__)
        vip.pop('HTTP_Redirect')
        vip.pop('SSLProfile')
    # cleanup nested dicts



    # pool
    pool = {}
    pool.update(pool_defaults.__dict__)

    for member in pool['Members']:
        member['ip'] = member.pop('Endpoint')

    # node
    node = {}
    node.update(node_defaults.__dict__)

    # now merge in the request values
    vip['Members'] = pool
    vip.update(vip_request['VIP'])

def create_node(conn, template, vip_request, partition='Common'):
    # Create a new pool on the BIG-IP
    for member in vip_request['VIP']['Members']:
        if not conn.tm.ltm.nodes.node.exists(name=member, partition=partition):
            try:
                resp = conn.tm.ltm.nodes.node.create(name=member, address=member['IP'], partition=partition)
            except:
                raise ValueError("F5 didn't like your request")
        else:
            raise ValueError('Node Already Exists!')


def delete_node(conn, node, partition='Common'):
    # Delete a pool if it exists
    if conn.tm.ltm.nodes.node.exists(name=node, partition=partition):
        node = conn.tm.ltm.nodes.node.load(name=node, partition=partition)
        node.delete()


def create_pool(conn, template, vip_request, partition='Common'):
    # Create a new pool on the BIG-IP
    name = format_name(defaults=template, name=vip_request['VIP']['Hostname'], type='Pool')
    if not conn.tm.ltm.pools.pool.exists(name=name, partition=partition):
        try:
            resp = conn.tm.ltm.pools.pool.create(name=name, partition=partition)
        except:
            raise ValueError("F5 didn't like your request")
    else:
        raise ValueError('Pool Already Exists!')


def update_pool(conn, request, partition='Common'):
    # Load an existing pool and update its description
    pool = conn.tm.ltm.pools.pool.load(name=name, partition=partition)
    pool.loadBalancingMode = template
    pool.description = "New description"
    pool.update()


def delete_pool(conn, pool, partition='Common'):
    # Delete a pool if it exists
    if conn.tm.ltm.pools.pool.exists(name=pool, partition=partition):
        pool_b = conn.tm.ltm.pools.pool.load(name=pool, partition=partition)
        pool_b.delete()
