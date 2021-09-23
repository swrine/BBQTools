import re, struct, json, csv, pytz
from datetime import datetime

def convert_time_utc_to_local(utcTime, localTimezone, timezoneSuffix = 'Z'):
    return datetime.strptime(utcTime, f'%Y-%m-%dT%H:%M:%S.%f{timezoneSuffix}').replace(tzinfo=pytz.utc).astimezone(localTimezone).strftime('%Y-%m-%d %H:%M:%S')

def write_json_file(filePath, content):
    with open(filePath, 'w') as writeFile:
        json.dump(content, writeFile)

def write_csv_file(filePath, content):
    csvWriter = csv.writer(open(filePath, 'w', newline=''))
    csvWriter.writerows(content)

def listize_json(dictJson):
    retColumns = [key for key in dictJson.keys()]
    retData = [json.dumps(val) for val in dictJson.values()]
    return (retColumns, retData)

def tablize_special_rest_data(basePhrase, routingData, localTimezone):
    if ('routing/standard/tables' in basePhrase or 'routing/current/tables' in basePhrase) and 'tableRoutingRows' in routingData:
        dataBody = routingData['tableRoutingRows']
    elif ('routing/standard' in basePhrase or 'routing/current' in basePhrase) and 'path' in routingData:
        dataBody = routingData['path']
    else:
        return (['1'], [['Result cannot be formatted.']])

    retColumns = [key for key in dataBody[0].keys()]
    retData = []
    for dataRow in dataBody:
        retData.append([val for val in dataRow.values()])
    return (retColumns, retData)


def decode_binary_routing_table_content(messagePayload):
    telegramData = re.search(r'\[(.*)\]', messagePayload)
    ret = []
    if telegramData:
        telegramDataBytes = str.encode(telegramData.group(1))
#                    bodyBytes = bytes(ttt.decode('utf-8').encode('latin_1'), 'latin_1')            
        tableDataBytes = telegramDataBytes[-(500*4):]
        for n, i in enumerate(range(0, len(tableDataBytes), 4), 1):
            (destMode, destDir1, destDir2, destRatio) = struct.unpack('>4B', tableDataBytes[i:i+4])
            ret.append(f'{n}:\tMode: {destMode},\tDir1: {destDir1},\tDir2: {destDir2},\tRatio: {destRatio}')
    return ret


def match_cfunit_state(stateValue, transitionMatrix):
    primaryState = None
    hiddenStates = []
    for stateBit in transitionMatrix:
        if stateBit.negative_bit ^ bool(stateValue & (1 << stateBit.state_bit)):
            if not primaryState:
                primaryState = stateBit.name
            elif not stateBit.negative_bit:
                hiddenStates.append(stateBit.name)
    return (primaryState, ';'.join(hiddenStates))


#def _add_npdp_tooltip(dataTable, columns, columnNamePattern, tooltipMap, hiddenContentFields):
#    colIndice = []
#    for colNr, col in enumerate(columns):
#        if (columnNamePattern in col.lower()):
#            colIndice.append(colNr)
#    if colIndice:
#        for rowOfItems in dataTable:
#            for colIndex in colIndice:
#                mapKey = rowOfItems[colIndex].text()
#                if mapKey in tooltipMap:
#                    toopTipContentList = []
#                    for key, val in tooltipMap[mapKey].items():
#                        if not key in hiddenContentFields:
#                            toopTipContentList.append(key+': '+val)
#                    rowOfItems[colIndex].setToolTip("\n".join(toopTipContentList))