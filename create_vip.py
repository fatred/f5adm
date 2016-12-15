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
    if objtype == 'node':
        defaults = template['defaults']['nodes']
    elif objtype == 'pool':
        defaults = template['defaults']['pools']
    elif objtype == 'virtualserver':
        defaults = template['defaults']['virtualservers']
    else:
        defaults = {}
    return defaults


def connect_ltm(ltm):
    return ManagementRoot(ltm['ltm1']['ip'], ltm['ltm1']['username'], ltm['ltm1']['password'])


def dump_obj_dict(thing):
    # takes a thing and pretty prints it to the screen for debugging
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(thing)


def format_name(template, name, objtype):
    # take a name and make it conform to the defaults
    if (objtype == 'pools') or (objtype == 'virtualservers'):
        # prefix first
        # check if its already prefixed with the text in the mangle rule
        if template['namemanglerules'][objtype]['name']['prefix']:
            chkidx = len(template['namemanglerules'][objtype]['name']['prefix'])
            if name[0:chkidx] == template['namemanglerules'][objtype]['name']['prefix']:
                pfx = ''
            else:
                pfx = template['namemanglerules'][objtype]['name']['prefix']
        else:
            pfx = ''
        # suffix second
        # check if its already suffixed with the text in the mangle rule
        if template['namemanglerules'][objtype]['name']['suffix']:
            chkidx = len(template['namemanglerules'][objtype]['name']['suffix'])
            if name[0:chkidx] == template['namemanglerules'][objtype]['name']['suffix']:
                sfx = ''
            else:
                sfx = template['namemanglerules'][objtype]['name']['suffix']
        else:
            sfx = ''
        # done
        return str(pfx + name + sfx).lower()
    else:
        # Nothing to do here
        return name.lower()


def format_vip_dest(template, dest):
    # take a name and make it conform to the defaults
    # prefix first
    # check if its already prefixed with the text in the mangle rule
    if template['namemanglerules']['virtualservers']['destination']['prefix']:
        chkidx = len(template['namemanglerules']['virtualservers']['destination']['prefix'])
        if dest[0:chkidx] == template['namemanglerules']['virtualservers']['destination']['prefix']:
            pfx = ''
        else:
            pfx = template['namemanglerules']['virtualservers']['destination']['prefix']
    else:
        pfx = ''
    # suffix second
    # check if its already suffixed with the text in the mangle rule
    if template['namemanglerules']['virtualservers']['destination']['suffix']:
        chkidx = len(template['namemanglerules']['virtualservers']['destination']['suffix'])
        if dest[0:chkidx] == template['namemanglerules']['virtualservers']['destination']['suffix']:
            sfx = ''
        else:
            sfx = template['namemanglerules']['virtualservers']['destination']['suffix']
    else:
        sfx = ''
    # done
    return str(pfx + dest + sfx).lower()


def apply_template_node(vip_request):
    # merge the request with the template and create a definitive request
    node_defaults = load_defaults('node')

    # gather ye rosebuds
    # create a list for the nodes to live in
    nodelist = []
    for node in vip_request['vip']['pool']['members']:
        # setup a dict
        nodedef = {}

        # pull in the defaults
        nodedef.update(node_defaults)

        # overload with request settings
        nodedef['name'] = node
        nodedef.update(vip_request['vip']['pool']['members'][node])

        # switchout the endpoint notation for "address" without the port
        endpoint = (vip_request['vip']['pool']['members'][node]['endpoint']).split(':')[0]
        nodedef['address'] = endpoint
        nodedef.pop('endpoint')
        nodedef.pop('port')
        nodedef.pop('prioritygroup')

        # add to the list
        nodelist.append(nodedef)

    return nodelist


def apply_template_pool(template, vip_request):
    # merge the request with the template and create a definitive request
    pool_defaults = load_defaults('pool')

    # gather ye rosebuds
    # setup canaries
    pga_required = False

    # setup dicts
    pooldef = {}
    membersdef = []

    # pull in defaults
    pooldef.update(pool_defaults)

    # give it a sensible name and desc
    pooldef['name'] = format_name(template=template, name=vip_request['vip']['hostname'], objtype='pools')
    pooldef['description'] = vip_request['vip']['servicename']

    # setup member list
    for pool_member in vip_request['vip']['pool']['members']:
        # new dict item for iteration
        memberdef = {}

        # give it a name
        memberdef['name'] = pool_member

        # switchout the endpoint notation from address and pump into name
        endpoint = vip_request['vip']['pool']['members'][pool_member]['endpoint']
        memberdef['name'] += (':' + endpoint.split(':')[1])

        # yank out the now redundant yaml label
        #memberdef.pop('endpoint')

        # set canary for PGA and copy the gropu number into the clean dict
        if vip_request['vip']['pool']['members'][pool_member].has_key('prioritygroup'):
            pga_required = True
            memberdef['prioritygroup'] = vip_request['vip']['pool']['members'][pool_member]['prioritygroup']

        # add the dict to the list of members
        membersdef.append(memberdef)

    # setup PGA if required
    if pga_required:
        total = len(vip_request['vip']['pool']['members'].keys())
        if total/4 < 1:
            pga = 1
        else:
            pga = total/4
        pooldef['minactivemembers'] = pga

    # set the balancing mode
    if vip_request['vip']['pool'].has_key('loadbalancingmode'):
        pooldef['loadbalancingmode'] = vip_request['vip']['pool']['loadbalancingmode']

    # set the monitor
    if vip_request['vip']['pool'].has_key('monitor'):
        pooldef['monitor'] = vip_request['vip']['pool']['monitor']

    # stuff it into the pool definition
    pooldef['members'] = membersdef

    return pooldef


def apply_template_vip(template, vip_request, ssl):
    # merge the request with the template and create a definitive request
    vip_defaults = load_defaults('virtualserver')

    # gather ye rosebuds in reverse order (build upwards)
    # vip
    vipdef = {}

    # pull in the generic defaults
    vipdef.update(vip_defaults['all'])
    vipdef.update(vip_defaults[443])
    vipdef.update(vip_defaults[80])

    # pull over the relevant info from request to clean dict
    vipdef['name'] = format_name(template=template, name=vip_request['vip']['hostname'], objtype='virtualservers')
    vipdef['description'] = vip_request['vip']['servicename']
    vipdef['destination'] = format_vip_dest(template, vip_request['vip']['ip'])

    # cleanup nested dicts for profiles
    for profile in template['profiletemplates']:
        profname = vipdef.pop(profile)
        vipdef[profile] = template['profiletemplates'][profile]
        vipdef[profile]['name'] = profile.replace('profile', '')

    if ssl:
        # setup the HTTPS stuff if required
        vipdef['destination'] += (':' + '443')
        # remove the HTTPS_Redirection stuff (its an SSL VIP we are working on)
        vipdef.pop('https_redirect')

        # set the SSL profile accordingly
        vipdef['sslprofile']['name'] = vip_request['vip']['ssl']
    else:
        # setup the HTTP stuff if required
        vipdef['name'] += '_80'
        vipdef.update(vip_defaults[80])
        vipdef['destination'] += (':' + '80')

        # this is an HTTP VIP, so no SSL profile please...
        vipdef.pop('sslprofile')

        # check to see if the 80 VIP should "work" or redirect to SSL VIP
        redirect = vipdef.pop('https_redirect')
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
    if not conn.tm.ltm.nodes.node.exists(name=node['name']):
        try:
            resp = conn.tm.ltm.nodes.node.create(**node)
        except:
            raise
    else:
        raise UserWarning('Node Already Exists!')


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
            raise
    else:
        raise UserWarning('Pool Already Exists!')


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
        raise UserWarning('VIP Already Exists!')


def update_vip(conn, vip):
    # Load an existing vip and update its stuff
    vipdef = conn.tm.ltm.virtuals.virtual.load(name=vip['name'])
    vipdef.update(**vip)


def delete_vip(conn, vip):
    # Delete a vip if it exists
    if conn.tm.ltm.virtuals.virtual.exists(name=vip['name']):
        vipdef = conn.tm.ltm.virtuals.virtual.load(name=vip['name'])
        vipdef.delete()

node_def = apply_template_node(vip_request)
pool_def = apply_template_pool(template, vip_request)
ssl_vip_def = apply_template_vip(template, vip_request, True)
plain_vip_def = apply_template_vip(template, vip_request, False)
dump_obj_dict(node_def)
dump_obj_dict(pool_def)
dump_obj_dict(ssl_vip_def)
dump_obj_dict(plain_vip_def)

conn = connect_ltm(ltmhost)

for node in node_def:
    create_node(conn, node)
create_pool(conn, pool_def)
create_vip(conn, ssl_vip_def)
create_vip(conn, plain_vip_def)

deldata = raw_input('Delete?: ')
if deldata == 'y':
    delete_vip(conn, plain_vip_def)
    delete_vip(conn, ssl_vip_def)
    delete_pool(conn, pool_def)
    for node in node_def:
        delete_node(conn, node)
else:
    pass
