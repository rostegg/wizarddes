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
        return tokenName != TokensType.BINARY_OPERATOR and tokenType is None


def filter_all(arr):
    print("Filter `ALL` values")
    return arr

def is_window_id_valid(id):
    reg = r"0x[0-9A-Fa-f]{8}"
    return False if re.fullmatch(reg,id) is None else True

def all_token_execute(result):
    print("Execute `ALL` selector")
    return result

def filter_first(arr):
    print("Filter `FIRST` values")
    return [ arr[0] ]

def single_token_execute(result):
    print("Execute `SINGLE` selector")
    return result

def id_token_execute(result):
    if (not is_window_id_valid(result['value'])): 
        raise WrongQueryParameterException("Not valid window id %s in `BY ID() filter`"%id)
    print("Execute `BY ID` filter")
    return result

def contains_token_execute(result):
    print("Execute `BY CONTAINS` filter")
    return result

def full_token_execute(result):
    print("Execute `BY FULL` filter")
    return result

def regex_token_execute(result):
    try:
        re.match(result['value'], "Test string")
    except re.error:
        raise WrongQueryParameterException("Invalid regex")
    print("Execute `BY REGEX` filter")
    return result


def mvto_token_execute(result):
    print("Execute `MV_TO` command")
    return result
def mvseparate_token_execute(result):
    print("Execute `MV_SEPARATE` command")
    return result

def close_token_execute(result):
    print("Execute `CLOSE` command")
    return result

def check_filter_results(result_list):
    if len(result_list) == 0:
        raise EmptyQueryResult("Zero result finded for query..")

def switch_token_execute(id):
    reg = r"[0-9]{1,3}"
    if (re.fullmatch(reg,id) is None):
        raise WrongQueryParameterException("Not valid desktop id %s in `SWITCH`"%id)
    print("Execute `SWITCH` command")

def active_token_execute(id):
    if (not is_window_id_valid(id)):
        raise WrongQueryParameterException("Not valid window id %s in `ACTIVE`"%id)
    print("Execute `ACTIVE` command")

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


import argparse



parser = argparse.ArgumentParser()
parser.add_argument('query', type=str, action="store")

args = parser.parse_args()

TokenParser(args.query)