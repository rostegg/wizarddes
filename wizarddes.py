#!/usr/bin/env python3

from subprocess import Popen, PIPE, check_output
import re, os, argparse
from argparse import RawTextHelpFormatter
from time import sleep
import datetime

# exceptions
class ParseTokenException(Exception):
    pass

class ExecuteQueryException(Exception):
    pass

class WrongQueryParameterException(Exception):
    pass

class WmctrlExeption(Exception):
    pass

class EmptyQueryResult(Exception):
    pass

class EwmhException(Exception):
    pass

class NotAvailableOperation(Exception):
    pass

# main script utils

# well, wmctrl sometimes don't execute immediatly tasks range, so we need give it a little bit of time...
def wait():
    sleep(0.05)

#local_storage_path = '/etc/wizzardes'
local_storage_path = ''

class PrintUtil:
    class Colors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'

    indent_symbol = ' '

    @staticmethod
    def log_error(msg):
        print(f"{PrintUtil.Colors.FAIL}[!] {msg}{PrintUtil.Colors.ENDC}")
    
    @staticmethod
    def log_warn(msg):
        print(f"{PrintUtil.Colors.WARNING}[!] {msg}{PrintUtil.Colors.ENDC}")

    @staticmethod
    def log_info(msg):
        print(f"{PrintUtil.Colors.OKBLUE}[-] {msg}{PrintUtil.Colors.ENDC}")

    @staticmethod
    def log_success(msg):
        print(f"{PrintUtil.Colors.OKGREEN}[+] {msg}{PrintUtil.Colors.ENDC}")

    @staticmethod
    def log_debug(msg):
        options.debug_mode and print(f"{PrintUtil.Colors.BOLD}[DEBUG][{datetime.datetime.now()}] {msg}{PrintUtil.Colors.ENDC}")

    @staticmethod
    def log_debug_object(msg):
        def color_print(text, color = PrintUtil.Colors.BOLD, end = '\n'):
            print(f"{color}{text}{PrintUtil.Colors.ENDC}", end=end)

        def pr_dict(d, indent=0):
            for key, value in d.items():
                color_print(f"{PrintUtil.indent_symbol * indent}{key}:", end='')
                if isinstance(value, dict):
                    print()
                    pr_dict(value, indent+1)
                elif isinstance(value, list):
                    print()
                    pr_list(value, indent+1)
                else:
                    color_print(f"{PrintUtil.indent_symbol}{value}")

        def pr_list(l, indent=0):
            for value in l:
                if isinstance(value, dict):
                    pr_dict(value, indent+1)
                elif isinstance(value, list):
                    pr_list(value, indent+1)
                else:
                    color_print(f"{PrintUtil.indent_symbol*(indent+1)}{value}")

        def pr_print(obj):
            if isinstance(obj, dict):
                pr_dict(obj,0)
            elif isinstance(obj, list):
                pr_list(obj,0)
            else:
                PrintUtil.log_debug(obj)
        options.debug_mode and pr_print(msg)
        #options.debug_mode and print(f"{PrintUtil.Colors.BOLD}[DEBUG] {msg}{PrintUtil.Colors.ENDC}")

epilog_msg = """
Unary operators:
    Query: SWITCH(desktopId)
        SWITCH: 
            Switch active desktop
                <desktopId> - id of target desktop, starting from 0 (int, >= 0)

Binary opeators:
    Grab opened windows and process results.
        | - one of token
        [...] - optional token
        -> - operator, which split data selecting and processing parts
        (...) - required parameter
    Query: ALL|FIRST [BY ID|REGEX|CONTAINS|FULL|DESK (pattern)] -> CLOSE|MV_TO(desktopId)|MV_SEPARATE(interval|*)|ACTIVE
        Selectors:
            ALL:
                Select all opened windows
            FIRST:
                Select FIRST opened window
        Filters:
            BY ID:
                Match window with selected id
                Example: BY ID(0xFFFFFFFF)
            BY REGEX:
                Match window by python regex string
                Example: BY REGEX(\s+Test\s+)
            BY CONTAINS:
                Match window if title contains string:
                Example: BY CONTAINS(Music)
            BY FULL:
                Match window if title match string:
                Example: BY FULL(Desktop)
            BY DESK:
                Match window in selected dekstop:
                Example: BY DESK(2)
        Processors:
            CLOSE:
                Close windows
            MV_TO:
                Move selected windows to desktop
                    <desktopId> - id of target desktop, starting from 0 (int, >= 0)
            MV_SEPARATE:
                Split selected windows between desktops
                When you create dekstops range, make sure the number of windows matches the range
                Remember desktop count starting with 0
                    <*> - foreach window new dekstop (it's mean, if you select 3 windows, each window would have own desktop)
                    <interval> - specify range of target desktops
                         Available intervals syntax:
                            |1|1-       - FROM
                            -3          - TO
                            1-3         - RANGE
                            1,3,5       - SEQUENCE

Queries examples:  
    Get all 'Firefox' instance and move them to third desktop:
        ALL BY CONTAINS(Firefox) -> MV_TO(3)
    Place all windows of 'Visual Code' one by one on the desktops:
        ALL BY CONTAINS(Visual Code) -> MV_SEPARATE(*)
    Switch to second desktop:
        SWITCH(2)
    Close window, with name 'Music':
        FIRST BY FULL(Music) -> CLOSE
    Make active window, which title match a regex:
        FIRST BY REGEX(\s+Pict\s+) -> ACTIVE
    Move all 'Chrome' windows (3) to 1-3 desktop:
        ALL BY CONTAINS (Chrome) -> MV_SEPARATE(1-3)
"""

def get_params():
    parser = argparse.ArgumentParser(description="Automatize your desktop management", epilog=epilog_msg, formatter_class=RawTextHelpFormatter)
    parser.add_argument("--single-query", help="Execute single query",
                    action="store")
    parser.add_argument("--query-file", help="Path to query file",
                    action="store")
    parser.add_argument("--debug-mode", help="Execute in debug mode",
                    action="store_true")

    options = parser.parse_args()
    return options

options = get_params()

# query parser logic
class Tokens:
    ALL, FIRST, LAST, BY, ID, REGEX, CONTAINS, FULL, CLOSE, MV_SEPARATE, MV_TO, SWITCH, ACTIVE, DESK, CREATE, WAIT = range(16)

    CONVERSION_OPERATOR = '->' 
    DEFAULT_SCENARIO_TOKEN = '*'
    AND_OPERATOR = '&'

    UNARY_OPERATORS = [SWITCH, WAIT]

    EXECUTABLE = [ALL, FIRST, LAST, ID, REGEX, CONTAINS, FULL, MV_TO, MV_SEPARATE, CLOSE, ACTIVE, SWITCH, DESK, CONVERSION_OPERATOR, CREATE, WAIT] 
    RANGE_FILTERS = [ALL, FIRST, LAST]
    DATA_FILTERS = [ID, REGEX, CONTAINS, FULL, DESK]
    SPECIAL_OPERATOR = [CONVERSION_OPERATOR, AND_OPERATOR]
    TOKENS_WITH_VALUES = [ID, REGEX, CONTAINS, FULL, MV_TO, MV_SEPARATE, DESK, CREATE]

    @staticmethod
    def get(tokenName):
        try:
            if tokenName in Tokens.SPECIAL_OPERATOR:
                return tokenName
            return getattr(Tokens, tokenName)
        except AttributeError:
            return None

    @staticmethod
    def contains_value(tokenName):
        tokenType = Tokens.get(tokenName)
        return tokenType in Tokens.TOKENS_WITH_VALUES

    @staticmethod
    def is_executable(tokenName):
        tokenType = Tokens.get(tokenName)
        return tokenType in Tokens.EXECUTABLE
    
    @staticmethod
    def is_unary(tokenName):
        tokenType = Tokens.get(tokenName)
        return tokenType in Tokens.UNARY_OPERATORS

    @staticmethod
    def is_value_token(tokenName):
        tokenType = Tokens.get(tokenName)
        return tokenName != Tokens.CONVERSION_OPERATOR and tokenType == None

class Utils:
    @staticmethod
    def dict_from_regex(target, reg):
        return [m.groupdict() for m in reg.finditer(target)]

class WindowsManager(object):
    def get_windows_list(self):
        raise NotAvailableOperation("Not implemented in manager impl")

    def get_desktop_list(self):
        raise NotAvailableOperation("Not implemented in manager impl")
        
    def mv_to(self, windows_id, desktop_id):
        raise NotAvailableOperation("Not implemented in manager impl")

    def close(self, windows_id):
        raise NotAvailableOperation("Not implemented in manager impl")
    
    def switch(self, desktop_id):
        raise NotAvailableOperation("Not implemented in manager impl")
    
    def active(self, window_id):
        raise NotAvailableOperation("Not implemented in manager impl")

class EwmhUtils(WindowsManager):
    def get_windows_list(self):
        raise NotAvailableOperation("Not implemented in manager impl")

    def get_desktop_list(self):
        raise NotAvailableOperation("Not implemented in manager impl")
        
    def mv_to(self, windows_id, desktop_id):
        raise NotAvailableOperation("Not implemented in manager impl")

    def close(self, windows_id):
        raise NotAvailableOperation("Not implemented in manager impl")
    
    def switch(self, desktop_id):
        raise NotAvailableOperation("Not implemented in manager impl")
    
    def active(self, window_id):
        raise NotAvailableOperation("Not implemented in manager impl")

class WmctrlUtils:
    # <windowId> <desktopId> <pid> <client> <windowTitle>
    def get_windows_list(self):
        output_str = self.execute_task(['-lp'])
        regex_window_list = re.compile(r'(?P<windowId>0x[0-9A-Fa-f]{8})\s+(?P<desktopId>[0-9]+)\s+(?P<pid>[0-9]+)\s+(?P<client>[A-Za-z0-9]+)\s+(?P<windowTitle>.+)', re.MULTILINE)
        return Utils.dict_from_regex(output_str, regex_window_list)

    # <desktopId> <active> <geometry> <viewport> <workAreaGeometry> <workAreaResolution> <title>
    def get_desktop_list(self):
        output_str = self.execute_task(['-d'])  
        regex_desktop_list = re.compile(r'(?P<desktopId>[0-9]+)\s+(?P<active>[-*]{1})\s+DG:\s+(?P<geometry>[0-9]{1,5}x[0-9]{1,5})\s+VP:\s+(?P<viewPort>N/A|(?:[0-9]{1,5}\,[0-9]{1,5}))\s+WA:\s+(?P<workAreaGeometry>[0-9]{1,5}\,[0-9]{1,5})\s+(?P<workAreaResolution>[0-9]{1,5}x[0-9]{1,5})\s+(?P<title>[\s\w/]+\n)', re.MULTILINE)
        return Utils.dict_from_regex(output_str, regex_desktop_list)
    
    def execute_task(self, task):
        task = ['wmctrl'] + task
        PrintUtil.log_debug(f"Executing wmctrl task: {task}")
        p = Popen(task, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        rc = p.returncode
        if rc == 1:
            raise WmctrlExeption(f"Can't execute `wmctrl` command {' '.join(task)}, exit code: `1`, error: {err.decode()}")
        return output.decode("utf-8")

wmctrl_utils = WmctrlUtils()

class RangeFilters:
    filter_all = lambda arr: arr
    filter_first = lambda arr : [ arr[0] ]
    filter_last = lambda arr : [ arr[-1] ]

class DataFilters:
    filter_by_id = lambda windows_list, filter_value: [ window for window in windows_list if filter_value == window['windowId'] ]
    filter_by_contains = lambda windows_list, filter_value: [ window for window in windows_list if filter_value in window['windowTitle'] ]
    filter_by_regex = lambda windows_list, filter_value: [ window for window in windows_list if re.match(filter_value, window['windowTitle']) ] 
    filter_by_full = lambda windows_list, filter_value: [ window for window in windows_list if filter_value ==  window['windowTitle'] ]
    filter_by_desk =lambda windows_list, filter_value: lambda windows_list, filter_value: [ window for window in windows_list if filter_value == window['desktopId'] ]

class FilterObject:
    def __init__(self, filter_func, filter_value):
        self.filter_func = filter_func
        self.filter_value = filter_value

    def filter(self, target_list):
        result = self.filter_func(target_list, self.filter_value)
        if len(result) == 0:
            raise EmptyQueryResult("Zero result finded for query..") 
        return result

class Validators:
    @staticmethod
    def is_window_id_valid(id):
        reg = r"0x[0-9A-Fa-f]{8}"
        return False if re.fullmatch(reg,id) is None else True
    
    @staticmethod
    def is_desktop_is_valid(id):
        try:
            desktop_list = wmctrl_utils.get_desktop_list()
            reg = r"[0-9]{1,5}"
            return False if re.fullmatch(reg,id) is None else int(id) < len(desktop_list)
        except ValueError:
            raise WrongQueryParameterException(f"Can't convert {id} to integer...")

class AppRunnersLoader:

    def __init__(self):
        self.app_runners_path = os.path.join(local_storage_path, "app_runners") 
        PrintUtil.log_debug(f"App runners path: {self.app_runners_path}")
        self.delimeter = "::"
        self.__loaders = {}
        self.__load()

    def __load(self):
        try:
            lines = open(self.app_runners_path).read().splitlines()
            for index, line in enumerate(lines):
                splited = line.split(self.delimeter)
                self.__loaders[splited[0]] = splited[1]
                PrintUtil.log_debug(f"At line '{index}'; alias: {splited[0]}; runner: {splited[1]}")        
        except FileNotFoundError:
            PrintUtil.log_warn(f"'app_runners' file not found, you better create one...") 

    def get_runner(self, name):
        try:
            return self.__loaders[name]
        except KeyError:
            raise WrongQueryParameterException(f"Can't find '{name}' runner in {self.app_runners_path}")

app_runners = AppRunnersLoader() 

def all_token_execute(state):
    state['range_filter_processor'] = RangeFilters.filter_all
    PrintUtil.log_debug(f"Executing 'ALL' token, append range_filter_processor as {state['range_filter_processor']}")
    return state

def first_token_execute(state):
    state['range_filter_processor'] = RangeFilters.filter_first
    PrintUtil.log_debug(f"Executing 'FIRST' token, append range_filter_processor as {state['range_filter_processor']}")
    return state

def last_token_execute(state):
    state['range_filter_processor'] = RangeFilters.filter_last
    PrintUtil.log_debug(f"Executing 'LAST' token, append range_filter_processor as {state['range_filter_processor']}")
    return state

def id_token_execute(state):
    if (not Validators.is_window_id_valid(state['value'])): 
        raise WrongQueryParameterException(f"Not valid window id `{state['value']}` in `BY ID() filter`")
    state['data_filter_processor'] = FilterObject(DataFilters.filter_by_id, state['value'])
    PrintUtil.log_debug(f"Executing 'ID' token, append data_filter_processor as {state['data_filter_processor']}")
    return state

def contains_token_execute(state):
    state['data_filter_processor'] = FilterObject(DataFilters.filter_by_contains, state['value'])
    PrintUtil.log_debug(f"Executing 'CONTAINS' token, append data_filter_processor as {state['data_filter_processor']}")
    return state

def desk_token_execute(state):
    if (not Validators.is_desktop_is_valid(state['value'])):
        raise WrongQueryParameterException(f"Not valid desktop id `{state['value']}` in `BY DESK() filter`")
    state['data_filter_processor'] = FilterObject(DataFilters.filter_by_desk, state['value'])
    PrintUtil.log_debug(f"Executing 'DESK' token, append data_filter_processor as {state['data_filter_processor']}")
    return state

def full_token_execute(state):
    state['data_filter_processor'] = FilterObject(DataFilters.filter_by_full, state['value'])
    PrintUtil.log_debug(f"Executing 'FULL' token, append data_filter_processor as {state['data_filter_processor']}")
    return state

def regex_token_execute(state):
    state['data_filter_processor'] = FilterObject(DataFilters.filter_by_regex, state['value'])
    PrintUtil.log_debug(f"Executing 'REGEX' token, append data_filter_processor as {state['data_filter_processor']}")
    return state

def mvto_token_execute(state):
    PrintUtil.log_debug(f"Executing 'MV_TO' token, target list:")
    PrintUtil.log_debug_object(state['target_list'])
    for window in state['target_list']:
        command = ['-ir', window['windowId'], '-t', state['value']]
        wmctrl_utils.execute_task(command)
        wait()
    return state

def mvseparate_token_execute(state):
    PrintUtil.log_debug(f"Executing 'MV_SEPARATE' token")
    state['desktopManager'].distributeWindows(state['target_list'], state['value'])
    return state

def close_token_execute(state):
    PrintUtil.log_debug(f"Executing 'CLOSE' token, target list:")
    PrintUtil.log_debug_object(state['target_list'])
    command = ['-ic', 'windowId']
    for window in state['target_list']:
        command = ['-ic', window['windowId']]
        wmctrl_utils.execute_task(command)
        wait()
    return state

def switch_token_execute(desktop_id):
    PrintUtil.log_debug(f"Executing 'SWITCH' token on desktop '{desktop_id}'")
    if (not Validators.is_desktop_is_valid(desktop_id)):
        raise WrongQueryParameterException(f"Not valid desktop id '{desktop_id}' in `SWITCH`, maybe desktop not yet created")
    command = ['-s' ,desktop_id]
    wmctrl_utils.execute_task(command)

def wait_token_execute(seconds):
    PrintUtil.log_debug(f"Executing 'WAIT' token for '{seconds}' seconds")

def active_token_execute(state):
    target = state['target_list']
    if len(target) != 1:
        raise ExecuteQueryException(f"Can't set `ACTIVE` for {len(target)} windows, only single target...")
    target = target[0]['windowId']
    PrintUtil.log_debug(f"Executing 'ACTIVE' token, on <{target}> window")
    if (not Validators.is_window_id_valid(target)):
        raise WrongQueryParameterException(f"Not valid window id {target} for `ACTIVE`")
    command = ['-ia', target]
    wmctrl_utils.execute_task(command)
    return state

def conversion_token_execute(state):
    PrintUtil.log_debug(f"Executing '->' token")
    target_list = state['target_list'] if 'target_list' in state else wmctrl_utils.get_windows_list()
    PrintUtil.log_debug(f"Decided target list :")
    PrintUtil.log_debug_object(target_list)
    if 'data_filter_processor' in state:
        PrintUtil.log_debug(f"Detected data filter: {state['data_filter_processor']}")
        target_list = state['data_filter_processor'].filter(target_list)
        PrintUtil.log_debug(f"After data filter target list is:")
        PrintUtil.log_debug_object(target_list)
    if 'range_filter_processor' in state:
        PrintUtil.log_debug(f"Detected range filter: {state['range_filter_processor']}")
        target_list = state['range_filter_processor'](target_list)
        PrintUtil.log_debug(f"After range filter target list is:")
        PrintUtil.log_debug_object(target_list)
    state['target_list'] = target_list
    return state

def create_token_execute(state):
    def app_pids(app):
        ps_cux_output = check_output(["ps", "cux"]).decode().split('\n')
        target_procs = [proc for proc in ps_cux_output if app in proc]
        if len(target_procs) == 0:
            return []
        pid_regex = re.compile(r'[A-Za-z\.\_\-]+\s+(?P<pid>[0-9]{1,7})\s+', re.MULTILINE)
        pids = [ m['pid'] for m in pid_regex.finditer("\n".join(target_procs)) ]
        return pids

    app_runner = app_runners.get_runner(state['value'])
    PrintUtil.log_debug(f"Executing 'CREATE' token, for '{app_runner}' runner")
    
    # take last proc pid in list
    windows_snapshot = wmctrl_utils.get_windows_list()
    windows_snapshot_count = len(windows_snapshot)
    PrintUtil.log_debug(f"Taking windows snapshot, founded '{windows_snapshot_count}' windows")
    PrintUtil.log_debug_object(windows_snapshot)
    
    '''
        Method above would create background process with pid not like the parent process
        So, for now using p.wait() for wait of ending of ui loading
        os.system(f"{app_runner} &")
    '''
    p = Popen([app_runner], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.wait()
    rc = p.returncode
    if rc == 1:
        raise ExecuteQueryException(f"Can't execute runner '{app_runner}', exit code: `1`")

    current_windows = wmctrl_utils.get_windows_list()
    wait_lock = True
    
    pids = app_pids(app_runner)
    if (len(pids) == 0):
        raise ExecuteQueryException(f"Can't find PID for '{app_runner}, maybe process freezed and don't started'")
    PrintUtil.log_debug(f"Finded {len(pids)} processes for '{app_runner}' runner")
    PrintUtil.log_debug_object(pids)
    pid = pids[-1]
    PrintUtil.log_debug(f"Starting monitoring for the formation of '{app_runner}' window")
    while wait_lock:
        # wait for new windows opening
        while windows_snapshot_count == len(current_windows):
            current_windows = wmctrl_utils.get_windows_list()
            wait()
        # check for target window   
        intersect = [ window for window in current_windows if (window not in windows_snapshot) ]
        for window in intersect:
            if window['pid'] == pid:
                state['target_list'] = [ window ]
                wait_lock = False
                break
        windows_snapshot = current_windows
        windows_snapshot_count = len(windows_snapshot)
    PrintUtil.log_debug(f"Finded target window for '{app_runner}'")
    PrintUtil.log_debug_object(state['target_list'])
    return state

EXECUTOR_FUNCS = {
    Tokens.ALL : all_token_execute,
    Tokens.FIRST : first_token_execute,
    Tokens.LAST : last_token_execute,
    Tokens.ID : id_token_execute,
    Tokens.CONTAINS: contains_token_execute,
    Tokens.FULL: full_token_execute,
    Tokens.REGEX: regex_token_execute,
    Tokens.SWITCH: switch_token_execute,
    Tokens.ACTIVE: active_token_execute,
    Tokens.MV_SEPARATE: mvseparate_token_execute,
    Tokens.MV_TO: mvto_token_execute,
    Tokens.CLOSE: close_token_execute,
    Tokens.DESK: desk_token_execute,
    Tokens.CONVERSION_OPERATOR: conversion_token_execute,
    Tokens.CREATE: create_token_execute,
    Tokens.WAIT: wait_token_execute
}

class DesktopManager:
    def __init__(self, desktop_list):
        self.desktop_list = desktop_list
    
    def distributeWindows(self, targets_list, interval):
        PrintUtil.log_debug(f"Trying to distribute {len(targets_list)} windows for range {interval}")
        interval_arr = [ i for i in range(0, len(targets_list))] if interval is Tokens.DEFAULT_SCENARIO_TOKEN else self.__parse_interval(interval, len(targets_list))
        PrintUtil.log_debug(f"Result interval list: {interval_arr}")
        self.distributeWindowsByRange(targets_list, interval_arr)

    def distributeWindowsByRange(self, targets_list, ids_list):
        for index, desktop_id in enumerate(ids_list):
            command = ['-ir', targets_list[index]['windowId'], '-t', desktop_id]
            PrintUtil.log_debug(f"Moving window <{targets_list[index]['windowId']}> to {desktop_id}")
            wmctrl_utils.execute_task(command)
            wait()

    '''
        Available intervals syntax:
            1,|1|1-     - FROM
            ,3|-3       - TO
            1-3         - RANGE
            1,3,5       - SEQUENCE
    '''
    def __parse_interval(self, interval, default_to):
        PrintUtil.log_debug(f"Not default scenario, parsing given interval")
        cleared_interval = "".join(interval.split())
        PrintUtil.log_debug(f"Cleared interval: {cleared_interval}")
        sequnce_regex = r"(?:[0-9]{1,3},){2,}[0-9]{1,3}$"
        primal_regex = re.compile(r"(?P<fromId>[0-9]{1,3})?\-?(?P<toId>[0-9]{1,3})?")
        if (re.fullmatch(sequnce_regex, cleared_interval) is not None):
            PrintUtil.log_debug(f"Detected sequence interval type")
            return list(map(int, cleared_interval.split(',')))
        else:
            # maybe change primal regex later, to avoide excess data (false positive triggering, beacuse all <?>)
            PrintUtil.log_debug(f"Detected primal interval type, trying to obtain range")
            interval_dict = Utils.dict_from_regex(cleared_interval, primal_regex)
            from_id = interval_dict[0].fromId if interval_dict[0].fromId is not None else 0
            PrintUtil.log_debug(f"Decided from_id='{from_id}'")
            to_id = interval_dict[0].toId if interval_dict[0].toId is not None else default_to
            PrintUtil.log_debug(f"Decided to_id='{to_id}'")
            return [i for i in range(from_id, to_id)]

class QueryExecutor:
    state = {}

    def __init__(self, tokens, query):
        self.query = query
        self.tokens = tokens
        desktop_list = wmctrl_utils.get_desktop_list()
        PrintUtil.log_debug(f"Desktop list on moment, when query executor was created :")
        PrintUtil.log_debug_object(desktop_list)
        self.state['desktopManager'] = DesktopManager(desktop_list)
    
    def execute(self):
        try:
            if (Tokens.is_unary(self.tokens[0])):
                PrintUtil.log_debug(f"Detected unary token '{self.tokens[0]}' at postion '0'")
                tokenType = Tokens.get(self.tokens[0])
                self.__execute_unary_operator(tokenType)
            else:
                PrintUtil.log_debug(f"Strarting to process {len(self.tokens)} tokens")
                iterator = range(0, len(self.tokens)).__iter__()
                for i in iterator:
                    token = self.tokens[i]
                    if (Tokens.is_executable(token)):
                        PrintUtil.log_debug(f"Processing executable token '{token}'")
                        tokenType = Tokens.get(token)
                        executor = EXECUTOR_FUNCS[tokenType]
                        if (Tokens.contains_value(token)):
                            PrintUtil.log_debug(f"'{token}' require parameter, checking...")
                            try:
                                self.state['value'] = self.tokens[i+1]
                                PrintUtil.log_debug(f"Validating '{self.state['value']}' parameter")
                                self.__is_valid_value(token, self.state['value'])
                                iterator.__next__()
                            except IndexError:
                                raise WrongQueryParameterException(f"{token} token require value...")
                        self.state = executor(self.state)
                        PrintUtil.log_debug(f"After executing '{token}', executor state is:")
                        PrintUtil.log_debug_object(self.state)
        except KeyError: 
            raise ExecuteQueryException(f"Can't execute query {self.query}, it seems that the query is not composed correctly")

    def __is_valid_value(self, token, value):
        if not Tokens.is_value_token(value):
            raise WrongQueryParameterException(f"Seems, like after `{token}` expected value, but it's `{value}`")

    def __execute_unary_operator(self, tokenType):
        PrintUtil.log_debug(f"Executing unary opearotor '{tokenType}'")
        if (len(self.tokens) != 2):
            raise WrongQueryParameterException("Unary operator requires only value and nothing more")
        executor = EXECUTOR_FUNCS[tokenType]
        executor(self.tokens[1])
    
class TokenParser:

    def __init__(self, expression):
        try:
            self.expression = expression
            self.tokens = self.tokens_list()
            self.simplified_tokens = self.simplify_tokens()
            self.query_executor = QueryExecutor(self.simplified_tokens, self.expression)
        except (ParseTokenException, WrongQueryParameterException, WmctrlExeption, EmptyQueryResult) as ex:
            PrintUtil.log_error(f"Error occuring, while parsing tokens for `{self.expression}`:")
            PrintUtil.log_error(str(ex))

    def execute(self):
        try:
            self.query_executor.execute()
        except (WrongQueryParameterException, ExecuteQueryException, WmctrlExeption, EmptyQueryResult) as ex:
            PrintUtil.log_error(f"Error occuring, while executing `{self.expression}`:")
            PrintUtil.log_error(str(ex))

    def simplify_tokens(self):
        tokens_list = list()
        PrintUtil.log_debug("Simplifying tokens")
        for position, token in enumerate(self.tokens):
            # skip empty tokens (like space at the end of line)
            if not token:
                PrintUtil.log_debug(f"Detected empty token at position '{position}'")
                continue 
            if token == Tokens.CONVERSION_OPERATOR:
                tokens_list.append(token)
                PrintUtil.log_debug(f"Detected conversion operator at position '{position}'")
                continue
            tokenType = Tokens.get(token)
            if (tokenType is None):
                PrintUtil.log_debug(f"Detected special token '{token}', trying to parse...")
                result = self.is_value(token)
                if (result is not None):
                    PrintUtil.log_debug(f"Detected value token '{result}' at position '{position}'")
                    tokens_list.append(result)
                else:
                    result = self.is_token_with_value(token)
                    PrintUtil.log_debug(f"Detected parametrized token '{result}' at position '{position}'")
                    tokens_list.extend(result)
            else:
                PrintUtil.log_debug(f"Detected token '{token}' at position '{position}'")
                tokens_list.append(token)
        PrintUtil.log_debug(f"Simplified tokens list : {tokens_list}")
        return tokens_list

    def is_value(self, token):
        reg = r"\(\W?(?P<value>[\w\s/\\,.-]+)\W?\)"
        result = re.match(reg,token)
        return None if result is None else result['value']

    def tokens_list(self):
        delimeter = r"\s+(?![^\(\)]*\))"
        return list(re.split(delimeter, self.expression))    

    def is_token_with_value(self, token):
        # closing ? from {1}
        # old regex:
        # reg = r"(?P<token>[\S]+)\(\W?(?P<tokenValue>[\w\s\S]+)\W?\)"
        reg = r"(?P<token>[\S]+)\((?P<tokenValue>[\w\s\S]+)\)"
        result = re.search(reg,token)
        if result is None:
            raise ParseTokenException("Bad token: %s"%(token))
        return [ result['token'], result['tokenValue'] ]

# main script

def wmctrl_status():
    try:
        with open(os.devnull, 'w') as null:
            proc = Popen("wmctrl", stdout=null, stderr=null)
            proc.communicate()
        return True
    except OSError:
        return False

if (not wmctrl_status()):
    PrintUtil.log_error("Seems, like `wmctrl` is not installed...")
    exit(1)

def execute_single_query(query):
    PrintUtil.log_info("Execute single query: %s"%query)
    tokenizer = TokenParser(query)
    tokenizer.execute()

def parse_query_file(file_path):
    return open(file_path).read().splitlines()

def execute_rules_from_frile(file_path):
    try:
        queries = parse_query_file(file_path)
        for query in queries:
            execute_single_query(query)
    except FileNotFoundError:
        PrintUtil.log_error("Can't read %s query file, check if it exist or have righ permissions")
        exit(1)

def execute_default_query_file():
    execute_rules_from_frile(f"{local_storage_path}/rules.txt")


def main():
    PrintUtil.log_debug("`debug mode` is enabled")
    execute_single_query(options.single_query)

if __name__ == "__main__":
    main()