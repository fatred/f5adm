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


def format_name(template, name, objtype):
    # take a name and make it conform to the defaults
    if (objtype == 'Pools') or (objtype == 'VirtualServers'):
        # prefix first
        # check if its already prefixed with the text in the mangle rule
        if template['NameMangleRules'][objtype]['Name']['Prefix']:
            chkidx = len(template['NameMangleRules'][objtype]['Name']['Prefix'])
            if name[0:chkidx] == template['NameMangleRules'][objtype]['Name']['Prefix']:
                pfx = ''
            else:
                pfx = template['NameMangleRules'][objtype]['Name']['Prefix']
        else:
            pfx = ''
        # suffix second
        # check if its already suffixed with the text in the mangle rule
        if template['NameMangleRules'][objtype]['Name']['Suffix']:
            chkidx = len(template['NameMangleRules'][objtype]['Name']['Suffix'])
            if name[0:chkidx] == template['NameMangleRules'][objtype]['Name']['Suffix']:
                sfx = ''
            else:
                sfx = template['NameMangleRules'][objtype]['Name']['Suffix']
        else:
            sfx = ''
        # done
        return str(pfx + name + sfx).lower()
    else:
        # Nothing to do here
        return name.lower()


def apply_template_node(vip_request):
    # merge the request with the template and create a definitive request
    node_defaults = load_defaults('Node')
    
    # gather ye rosebuds 
    # create a list for the nodes to live in
    nodelist = []
    for node in vip_request['VIP']['Pool']['Members']:
        # setup a dict
        nodedef = {}

        # pull in the defaults
        nodedef.update(node_defaults)

        # overload with request settings
        nodedef.update(node)

        # add to the list
        nodelist.append(nodedef)
    
    return nodelist


def apply_template_pool(template, vip_request):
    # merge the request with the template and create a definitive request
    pool_defaults = load_defaults('Pool')

    # gather ye rosebuds 
    # setup canaries
    pga_required = False

    # setup dicts
    pooldef = {}
    membersdef = []

    # pull in defaults
    pooldef.update(pool_defaults)

    # give it a sensible name and desc
    pooldef['name'] = format_name(template=template, name=vip_request['VIP']['Hostname'], objtype='Pools')
    pooldef['description'] = vip_request['VIP']['ServiceName']

    # setup member list
    for vip_member in vip_request['VIP']['Pool']['Members']:
        # new dict item for iteration
        memberdef = {}

        # give it a name
        memberdef['name'] = vip_member

        # switchout the endpint notation for "address"
        endpoint = vip_request['VIP']['Pool']['Members'][vip_member]['Endpoint']
        memberdef['address'] = endpoint

        # yank out the now redundant yaml label
        memberdef.pop('Endpoint')

        # set canary for PGA and copy the gropu number into the clean dict
        if vip_member.__contains__('PriorityGroup'):
            pga_required = True
            memberdef['PriorityGroup'] = vip_request['VIP']['Pool']['Members'][vip_member]['PriorityGroup']

        # add the dict to the list of members
        membersdef.append(memberdef)

    # setup PGA if required
    if pga_required:
        total = len(vip_request['VIP']['Pool']['Members'].keys())
        if total/4 < 1:
            pga = 1
        else:
            pga = total/4
        pooldef['MinActiveMembers'] = pga

    # set the balancing mode
    if vip_request['VIP']['Pool'].has_key('LoadBalancingMode'):
        pooldef['LoadBalancingMode'] = vip_request['VIP']['Pool']['LoadBalancingMode']

    # set the monitor
    if vip_request['VIP']['Pool'].has_key('Monitor'):
        pooldef['Monitor'] = vip_request['VIP']['Pool']['Monitor']

    # stuff it into the pool definition
    pooldef['Members'] = membersdef
    
    return pooldef


def apply_template_vip(template, vip_request, ssl):
    # merge the request with the template and create a definitive request
    vip_defaults = load_defaults('VirtualServer')

    # gather ye rosebuds in reverse order (build upwards)
    # vip
    vipdef = {}

    # pull in the generic defaults
    vipdef.update(vip_defaults['all'])
    vipdef.update(vip_defaults[443])
    vipdef.update(vip_defaults[80])

    # give it a sensible name and desc
    vipdef['name'] = format_name(template=template, name=vip_request['VIP']['Hostname'], objtype='VirtualServers')
    vipdef['description'] = vip_request['VIP']['ServiceName']

    # cleanup nested dicts for profiles
    for profile in template['ProfileTemplates']:
        profname = vipdef.pop(profile)
        vipdef[profile] = template['ProfileTemplates'][profile]
        vipdef[profile]['name'] = profname

    if ssl:
        # setup the HTTPS stuff if required
        # remove the HTTPS_Redirection stuff (its an SSL VIP we are working on)
        vipdef.pop('HTTPS_Redirect')

        # set the SSL profile accordingly
        vipdef['SSLProfile']['name'] = vip_request['VIP']['SSL']
    else:
        # setup the HTTP stuff if required
        vipdef.update(vip_defaults[80])

        # this is an HTTP VIP, so no SSL profile please...
        vipdef.pop('SSLProfile')

        # check to see if the 80 VIP should "work" or redirect to SSL VIP
        redirect = vipdef.pop('HTTPS_Redirect')
        if redirect:
            # TODO: add the redirect iRule
            pass
        else:
            # do nothing, we dont want a redirect...
            pass

    # send it all back
    return vipdef


def create_node(conn, node):
    # Create a new pool on the BIG-IP
    for member in vip_request['VIP']['Members']:
        if not conn.tm.ltm.nodes.node.exists(name=node['name']):
            try:
                resp = conn.tm.ltm.nodes.node.create(**node)
            except:
                raise ValueError("F5 didn't like your request")
        else:
            raise ValueError('Node Already Exists!')


def delete_node(conn, node):
    # Delete a pool if it exists
    if conn.tm.ltm.nodes.node.exists(name=node['name']):
        nodedef = conn.tm.ltm.nodes.node.load(name=node['name'])
        nodedef.delete()


def create_pool(conn, pool):
    # Create a new pool on the BIG-IP
    if not conn.tm.ltm.pools.pool.exists(name=pool['name']):
        try:
            resp = conn.tm.ltm.pools.pool.create(**pool)
        except:
            raise ValueError("F5 didn't like your request")
    else:
        raise ValueError('Pool Already Exists!')


def update_pool(conn, pool):
    # Load an existing pool and update its stuff
    pooldef = conn.tm.ltm.pools.pool.load(name=pool['name'])
    pooldef.update(**pool)


def delete_pool(conn, pool):
    # Delete a pool if it exists
    if conn.tm.ltm.pools.pool.exists(name=pool['name']):
        pooldef = conn.tm.ltm.pools.pool.load(name=pool['name'])
        pooldef.delete()

def create_vip(conn, vip):
    # Create a new vip on the BIG-IP
    if not conn.tm.ltm.virtuals.virtual.exists(name=vip['name']):
        try:
            resp = conn.tm.ltm.virtuals.virtual.create(**vip)
        except:
            raise
    else:
        raise ValueError('VIP Already Exists!')


def update_vip(conn, vip):
    # Load an existing vip and update its stuff
    vipdef = conn.tm.ltm.virtuals.virtual.load(name=vip['name'])
    vipdef.update(**vip)


def delete_vip(conn, vip):
    # Delete a vip if it exists
    if conn.tm.ltm.virtuals.virtual.exists(name=vip['name']):
        vipdef = conn.tm.ltm.virtuals.virtual.load(name=vip['name'])
        vipdef.delete()
