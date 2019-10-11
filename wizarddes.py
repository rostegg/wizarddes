#!/usr/bin/env python3

from __future__ import print_function

from subprocess import Popen, PIPE
import re

class ParseTokenException(Exception):
    pass

class ExecuteTaskException(Exception):
    pass

class WrongQueryParameterException(Exception):
    pass

class WmctrlExeption(Exception):
    pass

class EmptyQueryResult(Exception):
    pass

class TokensType:
    ALL, SINGLE, BY, ID, REGEX, CONTAINS, FULL, CLOSE, MV_SEPARATE, MV_TO, SWITCH, ACTIVE = range(12)

    UNARY_OPERATORS = [SWITCH, ACTIVE]
    BINARY_OPERATORS = [ALL, SINGLE]

    EXECUTABLE = [ALL, SINGLE, ID, REGEX, CONTAINS, FULL, MV_TO, MV_SEPARATE, CLOSE, ACTIVE, SWITCH] 

    BINARY_OPERATOR = '->' 

    TOKENS_WITH_VALUES = [ID, REGEX, CONTAINS, FULL, MV_TO, MV_SEPARATE]

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
        raise WmctrlExeption("Can't execute `wmctrl`, exit code: `1`, error: %s"%err)
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

def all_token_execute(result):
    result['return_processor'] = filter_all
    result['result_list'] = filter_all(windows_list)
    print("get all windows")
    return result

def filter_first(arr):
    return [ arr[0] ]

def single_token_execute(result):
    result['return_processor'] = filter_first
    result['result_list'] = filter_first(windows_list)
    print("get first window")
    return result

def id_token_execute(result):
    if (not is_window_id_valid(result['value'])): 
        raise WrongQueryParameterException("Not valid window id %s in `BY ID() filter`"%id)

    result_list = [window for window in windows_list if result['value'] == window['windowId'] ]
    check_filter_results(result_list)
    result['result_list'] = result_list
    print("Id filter execute")
    print(result_list)
    return result

def contains_token_execute(result):
    result_list = [window for window in windows_list if result['value'] in window['windowTitle'] ]
    check_filter_results(result_list)
    result_list = result['return_processor'](result_list)
    result['result_list'] = result_list
    print("Contains execute")
    print(result_list)
    return result

def full_token_execute(result):
    result_list = [window for window in windows_list if result['value'] ==  window['windowTitle'] ]
    check_filter_results(result_list)
    result_list = result['return_processor'](result_list)
    result['result_list'] = result_list
    print("Full execute")
    print(result_list)
    return result

def regex_token_execute(result):
    try:
        print(result['value'])
        result_list = [window for window in windows_list if re.match(result['value'], window['windowTitle']) ]
    except re.error:
        raise WrongQueryParameterException("Invalid regex")
    check_filter_results(result_list)
    result_list = result['return_processor'](result_list)
    result['result_list'] = result_list
    print("Regex execute")
    print(result_list)
    return result

'''
unary operators:
SWITCH(desktopId)|ACTIVE(windowId)

data_proc operators:
ALL|SINGLE BY ID|REGEX|CONTAINS|FULL(value) -> CLOSE|MV_SEPARATE(desktopRange)|MV_TO(desktopId)
'''
# result['value']
# MV_TO, MV_SEPARATE, CLOSE

def mvto_token_execute(result):
    print("MVTO")
    return result
def mvseparate_token_execute(result):
    print("MV_SEPARATE")
    return result

def close_token_execute(result):
    print("CLOSE THEM")
    return result

def check_filter_results(result_list):
    if len(result_list) == 0:
        raise EmptyQueryResult("Zero result finded for query..")

def switch_token_execute(id):
    reg = r"[0-9]{1,3}"
    if (re.fullmatch(reg,id) is None):
        raise WrongQueryParameterException("Not valid desktop id %s in `SWITCH`"%id)
    print("execute switch")
    # run

def active_token_execute(id):
    if (not is_window_id_valid(id)):
        raise WrongQueryParameterException("Not valid window id %s in `ACTIVE`"%id)
    print("execute active")
    # run

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
    TokensType.CLOSE: close_token_execute
}

class QueryExecutor:

    result = {}

    def __init__(self, tokens, query):
        self.query = query
        self.tokens = tokens
    
    def execute(self):
        try:
            if (TokensType.is_unary(self.tokens[0])):
                tokenType = TokensType.get(self.tokens[0])
                self.executeUnaryOperator(tokenType)
            else:
                iterator = range(0, len(self.tokens)).__iter__()
                for i in iterator:
                    token = self.tokens[i]
                    print("Process %s"%token)
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
                    print("After execute %s now result look like"%token)
                    print(self.result)
           
        except KeyError: 
            raise ExecuteTaskException("Can't execute query %s, there is no implementation of one of the tokens"%self.query)

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
        reg = r"(?P<token>[\S]+)\(\W?(?P<tokenValue>[\w\s\S]+)\W{1}\)"
        result = re.search(reg,token)

        if result is None:
            raise ParseTokenException("Bad token: %s"%(token))
        return [ result['token'], result['tokenValue'] ]


#query = "ACTIVE('0x32454354')"
query = "ALL BY CONTAINS ('Firefox') -> MV_TO (0x43243)"

parser = TokenParser(query)

'''
OPTIONAL OPERATIONS:
RESIZE(...,mvarg)|STATE(...,starg)|RENAME(...,name)
VIEWPORT(x,y)

def wmctrl_status():
    try:
        with open(os.devnull, 'w') as null:
            proc = subprocess.Popen("wmctrl", stdout=null, stderr=null)
            proc.communicate()
        return True
    except OSError:
        return False

if (not wmctrl_status()):
    print("Error, lol")
    exit(1)

'''