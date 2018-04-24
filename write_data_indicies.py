import json
variables_file = 'variables.json'

with open(variables_file, 'r') as file:
    variables_json = json.load(file)

for i in range(len(variables_json)):
    variables_json[i]['data_index'] = i

with open(variables_file, 'w') as file:
    json.dump(variables_json, file, sort_keys=True, indent=4)