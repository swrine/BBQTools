from enum import Enum

from collections import namedtuple

class QueryType(Enum):
    DB_HLC = 'DB_HLC'
    DB_TDS = 'DB_TDS'
    ES = 'ES'
    REST_HLC = 'REST_HLC'
    UNKNOWN = 'UNKNOWN'

QueryContent = namedtuple('QueryContent', 'query_type, static_connection_index, base_phrase, time_form, location_form, columns, modifiers, custom_conditions, appendix_phrase')

QuerierThread = namedtuple('QuerierThread', 'querier, thread, querylaunched')

UnitStateBit = namedtuple('UnitStateBit', 'name, state_bit, negative_bit')

ConnectionParameter = namedtuple('ConnectionParameter', 'address, address_alt, username, password, sid')