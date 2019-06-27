import logging
import requests
import simplejson as json
from six.moves import urllib
import sys
import uuid


logging.basicConfig(level=logging.DEBUG)
logging.getLogger('requests').setLevel(logging.DEBUG)
logging.getLogger('urllib').setLevel(logging.DEBUG)
logging.getLogger('json').setLevel(logging.DEBUG)


records = []
cip_data = json.load(sys.stdin)


def get_entity_key(entity):
    '''
    Returns the entity key that contains the entity ID value (according to CMDB schema)

    :entity: entity type (one of provider|service|tenant|image|flavor)
    '''
    return {
        'provider': 'id',
        'service': 'endpoint',
        'tenant': 'tenant_id',
        'image': 'image_id',
        'flavor': 'flavor_id'}[entity]


def get_parent_key(entity):
    '''
    Returns the parent's entity key that contains the entity ID value (according to CMDB schema)

    :entity: entity type (one of provider|service|tenant|image|flavor)
    '''
    return {
        'provider': None,
        'service': 'provider_id',
        'tenant': 'service',
        'image': 'tenant_id',
        'flavor': 'tenant_id'}[entity]


def get_children_entity(entity):
    '''
    Returns the list of entities that are related with the given entity.

    :entity: entity type (one of provider|service|tenant|image|flavor)
    '''
    return {
        'provider': ['service'],
        'service': ['tenant'],
        'tenant': ['image', 'flavor'],
        'image': [],
        'flavor': []}[entity]


def get_from_cip(entity, parent=None, data=None):
    '''
    Retrieves the records from CIP that match the entity type. If parent is given, it 
    filters CIP records according to the entity's parent value.

    :entity: entity type (one of provider|service|tenant|image|flavor)
    :parent: parent's entity CIP id value
    :data: optional data (default: global 'cip_data' variable)
    '''
    l = []
    parent_key = get_parent_key(entity)
    _cip_data = cip_data
    if data:
        _cip_data = data
    for record in _cip_data:
        if record['type'] == entity:
            if parent:
                record_parent = record['data'][parent_key]
                if record_parent == parent:
                    l.append(record)
            else:
                l.append(record)
    return l


def get_from_cmdb(entity, cip_id=None, parent=None):
    '''
    Obtains, if exists, a matching CMDB record based on the entity type
    and its CIP id. If parent is given, it filters CMDB records according
    to the entity's parent value.

    :entity: entity type (one of provider|service|tenant|image|flavor)
    :cip_id: entity CIP id value to match
    :parent: parent's entity CMDB id value
    '''
    parent_key = get_parent_key(entity)
    with open('CMDB_IFCA.json') as json_file:
        cmdb_data = json.load(json_file)
    # filtering
    filtered_data = []
    for record in cmdb_data:
        if record['type'] == entity:
            if parent:
                logging.debug('record[data][parent_key]: %s == parent: %s' % (record['data'][parent_key], parent))
                if record['data'][parent_key] == parent:
                    filtered_data.append(record)
            else:
                # workaround for provider case
                record['data']['id'] = record['_id']
                filtered_data.append(record)
    # matching
    if cip_id:
        entity_key = get_entity_key(entity)
        for record in filtered_data:
            if cip_id == record['data'][entity_key]:
                return record
    else:
        return filtered_data


def generate_records(entity, parent=None, parent_cmdb=None):
    '''
    Recursively generates the records, obtained from CIP, that will be pushed to CMDB.

    The function follows a top-down approach, starting with the first entity
    in the hierarchy (i.e. provider), iterating downwards until the last entity
    has been processed. At each entity level, the function iterates over the entire
    set of input (CIP) records, trying to match them with current CMDB data. If no match
    is found, it will add a new entry in CMDB.

    :entity: entity type (one of provider|service|tenant|image|flavor)
    :parent: parent's entity CIP id value
    :parent_cmdb: parent's entity CMDB id value
    '''
    logging.debug('Recursive call (locals: %s)' % locals())

    cip = get_from_cip(entity,
                       parent=parent)
    logging.debug(('Got records from CIP based on entity <%s> and parent '
                   '<%s>: %s' % (entity, parent, cip)))

    entity_children = get_children_entity(entity)
    entity_key = get_entity_key(entity)
    logging.debug('Entity key is <%s>' % entity_key)
    parent_key = get_parent_key(entity)
    logging.debug('Parent key is <%s>' % parent_key)

    for item in cip:
        cip_id_value = item['data'][entity_key]
        cmdb_match = get_from_cmdb(entity,
                                   cip_id=cip_id_value,
                                   parent=parent_cmdb)
        cmdb_id_value = None
        if cmdb_match:
            logging.debug(('Found record in CMDB matching entity <%s> and CIP '
                'id <%s> [action: update]' % (entity, cip_id_value)))
            cmdb_id_value = cmdb_match['_id']
            item['_rev'] = cmdb_match['_rev']
        else:
            logging.debug('Record not in CMDB [action: create]')
            # generate UUID __only__ when there are children entities
            if entity_children:
                logging.debug(('Generating CMDB id (UUID-based) as entity '
                               '<%s> has children entities' % entity))
                cmdb_id_value = str(uuid.uuid4())
        if cmdb_id_value:
            item['_id'] = cmdb_id_value
        item['data'][parent_key] = parent_cmdb
        records.append(item)

        logging.debug('Resultant record: %s' % json.dumps(item, indent=4))
        for child in entity_children:
            generate_records(child,
                             parent=cip_id_value,
                             parent_cmdb=cmdb_id_value)


def generate_deleted_records(entity, parent=None):
    '''
    Iterate over CMDB records, which are related (parent-child relations) to the already
    generated ones (global records), to find the ones that are not present in the latter.

    Note that broken CMDB records (e.g. no existing parent) are not detected, and thus they
    won't be removed.

    :entity: entity type (one of provider|service|tenant|image|flavor)
    :parent: parent's entity id value (same for both global records and CMBD)
    '''
    logging.debug('Recursive call (locals: %s)' % locals())
    
    cmdb = get_from_cmdb(entity,
                         parent=parent)
    logging.debug('CMDB data for entity <%s>: %s' % (entity, cmdb))
    
    entity_children = get_children_entity(entity)
    entity_key = get_entity_key(entity)
    records_entity_data = [item['data'][entity_key] for item in get_from_cip(entity, parent=parent, data=records)]

    for cmdb_item in cmdb:
        if cmdb_item['data'][entity_key] not in records_entity_data:
            logging.debug('Record from CMDB not found in CIP data (parent: %s): %s [action: delete]' % (parent, cmdb_item))
            cmdb_item['_deleted'] = True
            records.append(cmdb_item)
        for child in entity_children:
            generate_deleted_records(child,
                                     parent=cmdb_item['_id'])
    

def main():
    generate_records('provider')
    # delete __only__ starting from tenants
    services = get_from_cip('service', data=records)
    for service in services:
        generate_deleted_records('tenant', parent=service['_id'])
    logging.debug(json.dumps(records, indent=4))
