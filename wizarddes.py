#!/usr/bin/env python3

from __future__ import print_function

from subprocess import Popen, PIPE
import re, os, argparse
from argparse import RawTextHelpFormatter
from time import sleep

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

# well, wmctrl sometimes don't execute immediatly tasks range, so we need give it a little bit of time...
def wait():
    sleep(0.03)

class TokensType:
    ALL, SINGLE, BY, ID, REGEX, CONTAINS, FULL, CLOSE, MV_SEPARATE, MV_TO, SWITCH, ACTIVE, DESK = range(13)

    UNARY_OPERATORS = [SWITCH]
    BINARY_OPERATORS = [ALL, SINGLE]

    EXECUTABLE = [ALL, SINGLE, ID, REGEX, CONTAINS, FULL, MV_TO, MV_SEPARATE, CLOSE, ACTIVE, SWITCH, DESK] 

    BINARY_OPERATOR = '->' 

    AVAILABLE_INTERVAL_TOKEN = '*'

    TOKENS_WITH_VALUES = [ID, REGEX, CONTAINS, FULL, MV_TO, MV_SEPARATE, DESK]

    @staticmethod
    def get(tokenName):
        try:
            return getattr(TokensType, tokenName)
        except AttributeError:
            return None

    @staticmethod
    def contain_value(tokenName):
        tokenType = TokensType.get(tokenName)
        return tokenType in TokensType.TOKENS_WITH_VALUES

    @staticmethod
    def is_executable(tokenName):
        tokenType = TokensType.get(tokenName)
        return tokenType in TokensType.EXECUTABLE
    
    @staticmethod
    def is_unary(tokenName):
        tokenType = TokensType.get(tokenName)
        return tokenType in TokensType.UNARY_OPERATORS

    @staticmethod
    def is_value_token(tokenName):
        tokenType = TokensType.get(tokenName)
        return tokenName != TokensType.BINARY_OPERATOR and tokenType == None

def execute_subprocess(task):
    p = Popen(task, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()
    rc = p.returncode
    if rc == 1:
        raise WmctrlExeption("Can't execute `wmctrl`, exit code: `1`, error: %s"%str(err))
    return output.decode("utf-8")

def dict_from_regex(target, reg):
    return [m.groupdict() for m in reg.finditer(target)]

# <windowId> <desktopId> <client> <windowTitle>
def get_windows_list():
    output_str = execute_subprocess(['wmctrl', '-l'])
    regex_window_list = re.compile(r'(?P<windowId>0x[0-9A-Fa-f]{8})\s+(?P<desktopId>[0-9]{0,5})\s+(?P<client>[A-Za-z0-9]+)\s+(?P<windowTitle>.+)\n')
    return dict_from_regex(output_str, regex_window_list)

# <desktopId> <active> <geometry> <viewport> <workAreaGeometry> <workAreaResolution> <title>
def get_desktop_list():
    output_str = execute_subprocess(['wmctrl', '-d'])
    regex_desktop_list = re.compile(r'(?P<desktopId>[0-9]{1,3})\s+(?P<active>[-*]{1})\s+DG:\s+(?P<geometry>[0-9]{1,4}x[0-9]{1,4})\s+VP:\s+(?P<viewPort>N/A|(?:[0-9]{1,5}\,[0-9]{1,5}))\s+WA:\s+(?P<workAreaGeometry>[0-9]{1,5}\,[0-9]{1,5})\s+(?P<workAreaResolution>[0-9]{1,4}x[0-9]{1,4})\s+(?P<title>[\s\w/]+)\n')
    return dict_from_regex(output_str, regex_desktop_list)
    
windows_list = get_windows_list()
desktop_list = get_desktop_list()

def filter_all(arr):
    return arr

def is_window_id_valid(id):
    reg = r"0x[0-9A-Fa-f]{8}"
    return False if re.fullmatch(reg,id) is None else True

def is_desktop_is_valid(id):
    try:
        reg = r"[0-9]{1,5}"
        return False if re.fullmatch(reg,id) is None else int(id) < len(desktop_list)
    except ValueError:
        raise WrongQueryParameterException("Can't convert %s to integer..."%id)

def all_token_execute(result):
    result['return_processor'] = filter_all
    result['result_list'] = filter_all(windows_list)
    return result

def filter_first(arr):
    return [ arr[0] ]

def single_token_execute(result):
    result['return_processor'] = filter_first
    result['result_list'] = filter_first(windows_list)
    return result

def id_token_execute(result):
    if (not is_window_id_valid(result['value'])): 
        raise WrongQueryParameterException("Not valid window id `%s` in `BY ID() filter`"%result['value'])

    result_list = [window for window in windows_list if result['value'] == window['windowId'] ]
    check_filter_results(result_list)
    result_list = result['return_processor'](result_list)
    result['result_list'] = result_list
    return result

def contains_token_execute(result):
    result_list = [window for window in windows_list if result['value'] in window['windowTitle'] ]
    check_filter_results(result_list)
    result_list = result['return_processor'](result_list)
    result['result_list'] = result_list
    return result

def desk_token_execute(result):
    if (not is_desktop_is_valid(result['value'])):
        raise WrongQueryParameterException("Not valid desktop id `%s` in `BY DESK() filter`"%result['value'])
    
    result_list = [window for window in windows_list if result['value'] == window['desktopId'] ]
    check_filter_results(result_list)
    result_list = result['return_processor'](result_list)
    result['result_list'] = result_list
    return result

def full_token_execute(result):
    result_list = [window for window in windows_list if result['value'] ==  window['windowTitle'] ]
    check_filter_results(result_list)
    result_list = result['return_processor'](result_list)
    result['result_list'] = result_list
    return result

def regex_token_execute(result):
    try:
        result_list = [window for window in windows_list if re.match(result['value'], window['windowTitle']) ]
    except re.error:
        raise WrongQueryParameterException("Invalid regex")
    check_filter_results(result_list)
    result_list = result['return_processor'](result_list)
    result['result_list'] = result_list
    return result

class DesktopManager:

    def __init__(self, desktop_list):
        self.desktop_list = desktop_list
    
    def distributeWindows(self, targets_list, interval):
        interval_arr = [ i for i in range(0, len(targets_list))] if interval is TokensType.AVAILABLE_INTERVAL_TOKEN else self.__parse_interval(interval, len(targets_list))
        PrintUtil.log_info(interval)
        PrintUtil.log_info(interval_arr)
        self.distributeWindowsByRange(targets_list, interval_arr)

    def distributeWindowsByRange(self, targets_list, ids_list):
        command = ['wmctrl', '-ir', 'windowId', '-t', 'desktopId']
        for index, desktop_id in enumerate(ids_list):
            command[2] = targets_list[index]['windowId']
            command[4] = str(desktop_id)
            PrintUtil.log_warn(" ".join(command))
            execute_subprocess(command)
            wait()

    '''
        Available intervals syntax:
            1,|1|1-     - FROM
            ,3|-3       - TO
            1-3         - RANGE
            1,3,5       - SEQUENCE
    '''
    def __parse_interval(self,interval, default_to):
        cleared_interval = "".join(interval.split())
        sequnce_regex = r"(?:[0-9]{1,3},){2,}[0-9]{1,3}$"
        primal_regex = re.compile(r"(?P<fromId>[0-9]{1,3})?\-?(?P<toId>[0-9]{1,3})?")
        if (re.fullmatch(sequnce_regex, cleared_interval) is not None):
            return list(map(int, cleared_interval.split(',')))
        else:
            # maybe change primal regex later, to avoide excess data (false positive triggering, beacuse all <?>)
            interval_dict = dict_from_regex(cleared_interval, primal_regex)
            from_id = interval_dict[0].fromId if interval_dict[0].fromId is not None else 0
            to_id = interval_dict[0].toId if interval_dict[0].toId is not None else default_to
            return [i for i in range(from_id, to_id)]

def mvto_token_execute(result):
    command = ['wmctrl', '-ir', 'windowId', '-t', result['value']]
    for window in result['result_list']:
        command[2] =  window['windowId']
        execute_subprocess(command)
        wait()
    return result

def mvseparate_token_execute(result):
    result['desktopManager'].distributeWindows(result['result_list'], result['value'])
    return result

def close_token_execute(result):
    command = ['wmctrl', '-ic', 'windowId']
    for window in result['result_list']:
        command[2] = window['windowId']
        execute_subprocess(command)
    return result

def check_filter_results(result_list):
    if len(result_list) == 0:
        raise EmptyQueryResult("Zero result finded for query..")

def switch_token_execute(id):
    reg = r"[0-9]{1,3}"
    if (re.fullmatch(reg,id) is None):
        raise WrongQueryParameterException("Not valid desktop id %s in `SWITCH`"%id)
    command = ['wmctrl', '-s' ,id]
    execute_subprocess(command)

def active_token_execute(result):
    target = result['result_list']
    if len(target) != 1:
        raise ExecuteQueryException("Can't set active for %s windows, only single target..."%str(len(result['result_list'])))
    target = target[0]
    if (not is_window_id_valid(target['windowId'])):
        raise WrongQueryParameterException("Not valid window id %s for `ACTIVE`"%target['windowId'])
    command = ['wmctrl', '-ia', target['windowId']]
    execute_subprocess(command)

EXECUTOR_FUNCS = {
    TokensType.ALL : all_token_execute,
    TokensType.SINGLE : single_token_execute,
    TokensType.ID : id_token_execute,
    TokensType.CONTAINS: contains_token_execute,
    TokensType.FULL: full_token_execute,
    TokensType.REGEX: regex_token_execute,
    TokensType.SWITCH: switch_token_execute,
    TokensType.ACTIVE: active_token_execute,
    TokensType.MV_SEPARATE: mvseparate_token_execute,
    TokensType.MV_TO: mvto_token_execute,
    TokensType.CLOSE: close_token_execute,
    TokensType.DESK: desk_token_execute
}

class QueryExecutor:

    result = {}

    def __init__(self, tokens, query):
        self.query = query
        self.tokens = tokens
        self.result['desktopManager'] = DesktopManager(desktop_list)
    
    def execute(self):
        try:
            if (TokensType.is_unary(self.tokens[0])):
                tokenType = TokensType.get(self.tokens[0])
                self.executeUnaryOperator(tokenType)
            else:
                iterator = range(0, len(self.tokens)).__iter__()
                for i in iterator:
                    token = self.tokens[i]
                    if (TokensType.is_executable(token)):
                        tokenType = TokensType.get(token)
                        executor = EXECUTOR_FUNCS[tokenType]
                        if (TokensType.contain_value(token)):
                            try:
                                self.result['value'] = self.tokens[i+1]
                                self.is_valid_value(token, self.result['value'])
                                iterator.__next__()
                            except IndexError:
                                raise WrongQueryParameterException("%s token require value..."%token)
                        self.result = executor(self.result)
           
        except KeyError: 
            raise ExecuteQueryException("Can't execute query %s, there is no implementation of one of the tokens"%self.query)

    def is_valid_value(self, token, value):
        if not TokensType.is_value_token(value):
            raise WrongQueryParameterException("Seems, like after `%s` expected value, but it `%s`"%(token, value))

    def executeUnaryOperator(self, tokenType):
        if (len(self.tokens) != 2):
            raise WrongQueryParameterException("Unary operator requires only value and nothing more")
        executor = EXECUTOR_FUNCS[tokenType]
        executor(self.tokens[1])
    
class TokenParser:

    def __init__(self, expression):
        self.expression = expression
        self.tokens = self.tokens_list()
        self.simplified_tokens = self.simplify_tokens()
        self.query_executor = QueryExecutor(self.simplified_tokens, self.expression)

    def execute(self):
        self.query_executor.execute()

    def simplify_tokens(self):
        tokens_list = list()
        for token in self.tokens:
            # skip empty tokens (like space at the end of line)
            if not token:
                continue 
            if token == TokensType.BINARY_OPERATOR:
                tokens_list.append(token)
                continue
            tokenType = TokensType.get(token)
            if (tokenType is None):
                result = self.is_value(token)
                if (result is not None):
                    tokens_list.append(result)
                else:
                    result = self.is_token_with_value(token)
                    tokens_list.extend(result)
            else:
                tokens_list.append(token)
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
        #reg = r"(?P<token>[\S]+)\(\W?(?P<tokenValue>[\w\s\S]+)\W?\)"
        reg = r"(?P<token>[\S]+)\((?P<tokenValue>[\w\s\S]+)\)"
        result = re.search(reg,token)
        if result is None:
            raise ParseTokenException("Bad token: %s"%(token))
        return [ result['token'], result['tokenValue'] ]

# main script

class PrintUtil:
    class Colors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
    
    @staticmethod
    def log_error(msg):
        print("%s[!] %s%s"%(PrintUtil.Colors.FAIL, msg, PrintUtil.Colors.ENDC))
    
    @staticmethod
    def log_warn(msg):
        print("%s[!] %s%s"%(PrintUtil.Colors.WARNING, msg, PrintUtil.Colors.ENDC))

    @staticmethod
    def log_info(msg):
        print("%s[-] %s%s"%(PrintUtil.Colors.OKBLUE, msg, PrintUtil.Colors.ENDC))

    @staticmethod
    def log_success(msg):
        print("%s[+] %s%s"%(PrintUtil.Colors.OKGREEN, msg, PrintUtil.Colors.ENDC))


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

epilog_msg = '''
Unary operators:
    Query: SWITCH(desktopId)
        SWITCH : 
            Switch active desktop
                <desktopId> - id of target desktop, starting from 0 (int, >= 0)

Binary opeators:
    Grab opened windows and process results.
        | - one of token
        [...] - optional token
        -> - operator, which split data selecting and processing parts
        (...) - required parameter
    Query: ALL|SINGLE [BY ID|REGEX|CONTAINS|FULL|DESK (pattern)] -> CLOSE|MV_TO(desktopId)|MV_SEPARATE(interval|*)|ACTIVE
        Selectors:
            ALL:
                Select all opened windows
            SINGLE:
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
        SINGLE BY FULL(Music) -> CLOSE
    Make active window, which title match a regex:
        SINGLE BY REGEX(\s+Pict\s+) -> ACTIVE
    Move all 'Chrome' windows (3) to 1-3 desktop:
        ALL BY CONTAINS (Chrome) -> MV_SEPARATE(1-3)

'''

def get_params():
    parser = argparse.ArgumentParser(description="Automatize your desktop management", epilog=epilog_msg, formatter_class=RawTextHelpFormatter)
    parser.add_argument("--single-query", help="Execute single query",
                    action="store")
    parser.add_argument("--query-file", help="Path to query file",
                    action="store")
    import sys
    if len(sys.argv[1:])==0:
        parser.print_help()
        exit(0)

    options = parser.parse_args()
    return options
    

options = get_params()

def execute_single_query(query):
    PrintUtil.log_info("Execute single query: %s"%query)
    # parse exceptions
    tokenizer = TokenParser(query)
    tokenizer.execute()

def parse_query_file(file_path):
    return []

def execute_custom_query_file(file_path):
    pass

def execute_default_query_file():
    default_path = "/etc/rules.txt"
    queries = parse_query_file(default_path)
    pass

def main():
    if (options.single_query is not None):
        execute_single_query(options.single_query)
        exit(0)
    else:
        if (options.query_file):
            execute_custom_query_file(options.query_file)
            exit(0)
        else:
            execute_default_query_file()

if __name__ == "__main__":
    main()
'''
TODO 
RESIZE(mvarg)|STATE(starg)|RENAME(name)
VIEWPORT(x,y)
'''