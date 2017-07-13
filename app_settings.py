import json

arduino_input_tags = ['DI_0', 'DI_1', 'DI_2', 'DI_3', 'DI_4', 'DI_5', 'DI_IGNITION']
arduino_output_tags = ['DO_0', 'DO_1', 'DO_2', 'DO_3', 'DO_4', 'DO_5']
sys_var_tags = ['SYS_LOGGED_IN', 'SYS_PASSCODE_PROMPT', 'SYS_REVERSE_CAM_ON']
sys_save_var_tags = ['SYS_SCREEN_BRIGHTNESS', 'SYS_DIM_BACKLIGHT', 'SYS_SCREEN_OFF_DELAY', 'SYS_SHUTDOWN_DELAY']
auto_var_tags = ['AUTOVAR_OPERATOR_1','AUTOVAR_OPERATOR_2_1', 'AUTOVAR_GET_VAR_1','AUTOVAR_GET_VAR_2_1', 'AUTOVAR_SET_VAR_1', 'AUTOVAR_OPERATOR_2', 'AUTOVAR_OPERATOR_2_2', 'AUTOVAR_GET_VAR_2', 'AUTOVAR_GET_VAR_2_2', 'AUTOVAR_SET_VAR_2', 'AUTOVAR_OPERATOR_3', 'AUTOVAR_OPERATOR_2_3', 'AUTOVAR_GET_VAR_3', 'AUTOVAR_GET_VAR_2_3', 'AUTOVAR_SET_VAR_3', 'AUTOVAR_OPERATOR_4', 'AUTOVAR_OPERATOR_2_4', 'AUTOVAR_GET_VAR_4', 'AUTOVAR_GET_VAR_2_4', 'AUTOVAR_SET_VAR_4']


settings_json = json.dumps([
    {'type': 'numeric',
     'title': 'Screen Dim Brightness',
     'desc': 'Screen brightness setting when "Dim Backlight" is active".',
     'section': 'Settings',
     'key': 'SYS_SCREEN_BRIGHTNESS'},
    {'type': 'numeric',
     'title': 'Screen Off Delay',
     'desc': 'When ignition is turned off, this is the delay in seconds before the screen turns off.',
     'section': 'Settings',
     'key': 'SYS_SCREEN_OFF_DELAY'},
    {'type': 'numeric',
     'title': 'Shutdown Delay',
     'desc': 'When ignition is turned off, this is the delay in minutes before the system shuts down',
     'section': 'Settings',
     'key': 'SYS_SHUTdoWN_DELAY'}])

autovars_json = json.dumps([
    {'type': 'string',
     'title': 'Get Var 1',
     'desc': '',
     'section': 'AutoVars',
     'key': 'AUTOVAR_GET_VAR_1'},
    {'type': 'string',
     'title': 'Operator 1',
     'desc': '',
     'section': 'AutoVars',
     'key': 'AUTOVAR_OPERATOR_1'},
    {'type': 'string',
     'title': 'Set Var 1',
     'desc': '',
     'section': 'AutoVars',
     'key': 'AUTOVAR_SET_VAR_1'}])

aliases_json = json.dumps([
    {'type': 'alias',
     'title': 'DI_0',
     'desc': '',
     'section': 'InputAliases',
     'key': 'DI_0'},
    {'type': 'alias',
     'title': 'DI_1',
     'desc': '',
     'section': 'InputAliases',
     'key': 'DI_1'},
    {'type': 'alias',
     'title': 'DI_2',
     'desc': '',
     'section': 'InputAliases',
     'key': 'DI_2'},
    {'type': 'alias',
     'title': 'DI_3',
     'desc': '',
     'section': 'InputAliases',
     'key': 'DI_3'},
    {'type': 'alias',
     'title': 'DI_4',
     'desc': '',
     'section': 'InputAliases',
     'key': 'DI_4'},
    {'type': 'alias',
     'title': 'DI_5',
     'desc': '',
     'section': 'InputAliases',
     'key': 'DI_5'},
    {'type': 'alias',
     'title': 'DI_IGNITION',
     'desc': '',
     'section': 'InputAliases',
     'key': 'DI_IGNITION'},


    {'type': 'alias',
     'title': 'DO_0',
     'desc': '',
     'section': 'OutputAliases',
     'key': 'DO_0'},
    {'type': 'alias',
     'title': 'DO_1',
     'desc': '',
     'section': 'OutputAliases',
     'key': 'DO_1'},
    {'type': 'alias',
     'title': 'DO_2',
     'desc': '',
     'section': 'OutputAliases',
     'key': 'DO_2'},
    {'type': 'alias',
     'title': 'DO_3',
     'desc': '',
     'section': 'OutputAliases',
     'key': 'DO_3'},
    {'type': 'alias',
     'title': 'DO_4',
     'desc': '',
     'section': 'OutputAliases',
     'key': 'DO_4'},
    {'type': 'alias',
     'title': 'DO_5',
     'desc': '',
     'section': 'OutputAliases',
     'key': 'DO_5'}])