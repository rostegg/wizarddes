#!/usr/bin/env python3

import re, os, argparse, datetime
from subprocess import Popen, PIPE, check_output, TimeoutExpired
from argparse import RawTextHelpFormatter
from time import sleep
from array import array
from pathlib import Path

local_storage_path = os.path.join(Path.home(),'.wizarddes')
rules_storage_path = os.path.join(local_storage_path, 'rules')

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

class NotAvailableOperatioException(Exception):
    pass

class TableFormaterException(Exception):
    pass

# main script utils

# well, wmctrl sometimes don't execute immediately tasks range, so we need give it a little bit of time...
def wait():
    sleep(0.05)

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

    class TableFormater():
        TOP_LEFT = '╭─'
        TOP_RIGHT = '─╮'
        BOTTOM_LEFT = '╰─'
        BOTTOM_RIGTH = '─╯'
        HORIZONTAL = '─'
        VERTICAL = '│'
        TRANSITION_LEFT = '├─'
        TRANSITION_RIGHT = '─┤'
        SPACE = ' '

        def __init__(self, data):
            if len(data) <= 0:
                raise TableFormaterException("Table data size must be > 0")
            self.data = data
            self.headers = self.data[0].keys()
            self.rows, self.columns = self.__table_size()
            self.columns_width = self.__count_columns_width()
            
        def __table_size(self):
            def assert_struct(objs, required_fields_number):
                for obj in objs:
                    if len(obj.keys()) != required_fields_number:
                        raise TableFormaterException("Different objects structures, can't print this")
            rows = len(self.data)
            columns = len(self.headers)
            if len(self.data) > 1:
                assert_struct(self.data[1:], columns)
            return (rows, columns)

        def __count_columns_width(self):
            def find_max(header, width = 0):
                for value in self.data:
                    str_value = str(value[header])
                    width = len(str_value) if len(str_value) > width else width
                return width

            widths = list()
            for header in self.headers:
                # +2 for spaces
                width = find_max(header) + 2
                diff = width - len(header)
                # bigger indent, if header size > any value
                width = width + abs(diff) + 2 if diff <= 1 else width
                widths.append(width)
            return widths


        def print_table(self):
            def format_line(values, left_separator, right_separator, middle_separator, space_char = self.SPACE):
                line = ""
                for index, value in enumerate(values):
                    diff = self.columns_width[index] - len(str(value))
                    indent_before = int(diff/2)
                    indent_after = diff - int(diff/2)
                    
                    if index == 0:
                        indent_before += 1
                        chunck = f"{left_separator}{space_char*indent_before}{value}{space_char*indent_after}"
                    elif index == (len(values) - 1):
                        indent_after += 1
                        chunck = f"{middle_separator}{space_char*indent_before}{value}{space_char*indent_after}{right_separator}"
                    else:
                        chunck = f"{middle_separator}{space_char*indent_before}{value}{space_char*indent_after}"
                    
                    line += chunck
                return line        
            
            headers_line = format_line(self.headers, self.VERTICAL, self.VERTICAL, self.VERTICAL)

            full_width = sum(self.columns_width)

            width_with_indents = full_width + (self.columns*2 - self.columns - 1)
            # top line
            print(f"{self.TOP_LEFT}{self.HORIZONTAL*width_with_indents}{self.TOP_RIGHT}")
            # headers
            print(headers_line)
            delimiter = f"{self.TRANSITION_LEFT}{self.HORIZONTAL*width_with_indents}{self.TRANSITION_RIGHT}"
            print(delimiter)
            for index, obj in enumerate(self.data):
                line = format_line(obj.values(), self.VERTICAL, self.VERTICAL, self.VERTICAL)
                print(line)
                index < (len(self.data) - 1) and print(delimiter)
            # bottom line
            print(f"{self.BOTTOM_LEFT}{self.HORIZONTAL*width_with_indents}{self.BOTTOM_RIGTH}")

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
    def log_indent(msg, indent = indent_symbol):
        print(f"{indent}{msg}")

    @staticmethod
    def log_debug_object(msg):
        def color_print(text, color = PrintUtil.Colors.BOLD, end = '\n'):
            print(f"{color}{text}{PrintUtil.Colors.ENDC}", end=end)

        def pretty_dict(d, indent=0):
            for key, value in d.items():
                color_print(f"{PrintUtil.indent_symbol * indent}{key}:", end='')
                if isinstance(value, dict):
                    print()
                    pretty_dict(value, indent+1)
                elif isinstance(value, list):
                    print()
                    pretty_list(value, indent+1)
                else:
                    color_print(f"{PrintUtil.indent_symbol}{value}")

        def pretty_list(l, indent=0):
            for value in l:
                if isinstance(value, dict):
                    pretty_dict(value, indent+1)
                elif isinstance(value, list):
                    pretty_list(value, indent+1)
                else:
                    color_print(f"{PrintUtil.indent_symbol*(indent+1)}{value}")

        def pretty_print(obj):
            if isinstance(obj, dict):
                pretty_dict(obj)
            elif isinstance(obj, list):
                pretty_list(obj)
            else:
                PrintUtil.log_debug(obj)

        options.debug_mode and pretty_print(msg)

# query parser logic
class Tokens:
    ALL, FIRST, LAST, BY, ID, REGEX, CONTAINS, FULL, CLOSE, MV_SEPARATE, MV_TO, SWITCH, ACTIVE, DESK, CREATE, WAIT, RANGE, FORCE_CREATE, PRINT = range(19)

    CONVERSION_OPERATOR = '->' 
    DEFAULT_SCENARIO_TOKEN = '*'
    AND_OPERATOR = '&'

    UNARY_OPERATORS = [SWITCH]

    EXECUTABLE = [ALL, FIRST, LAST, ID, REGEX, CONTAINS, FULL, MV_TO, MV_SEPARATE, CLOSE, ACTIVE, SWITCH, DESK, CONVERSION_OPERATOR, CREATE, WAIT, RANGE, FORCE_CREATE, BY, PRINT] 
    RANGE_FILTERS = [ALL, FIRST, LAST, RANGE]
    DATA_FILTERS = [ID, REGEX, CONTAINS, FULL, DESK]
    SPECIAL_OPERATOR = [CONVERSION_OPERATOR, AND_OPERATOR]
    TOKENS_WITH_VALUES = [ID, REGEX, CONTAINS, FULL, MV_TO, MV_SEPARATE, DESK, CREATE, FORCE_CREATE, WAIT]

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

    @staticmethod
    def assert_filters_list(state):
        if 'data_filter_processor' not in state:
            state['data_filter_processor'] = list() 
        return state

    @staticmethod
    def to_hex(s):
        def zpad_hex(s):
            return '0x' + s[2:].zfill(8)
        return zpad_hex(str(hex(s)))
    
    @staticmethod
    def wmctrl_status():
        try:
            with open(os.devnull, 'w') as null:
                proc = Popen("wmctrl", stdout=null, stderr=null)
                proc.communicate()
            return True
        except OSError:
            return False

epilog_msg = r"""
Unary operators:
    Query: SWITCH(desktopId)
        SWITCH: 
            Switch active desktop
                <desktopId> - id of target desktop, starting from 0 (int, >= 0)

Binary operators:
    Grab opened windows and process results.
        | - one of token
        [...] - optional token
        -> - token, which split data selecting and processing parts
        (...) - required parameter
        * - default scenario parameter
        $ - allow multiple tokens
        & - allow multiple tokens, but separeated with '&' symbol
    Query:[CREATE(app_runner)|FORCE_CREATE(app_runner)]|[ALL|FIRST|LAST]|[BY ID(hex_string)|BY REGEX(regex)|BY CONTAINS(string)|BY FULL(sting)|BY DESK(int|*)]$ -> [CLOSE|PRINT|MV_TO(int|*)|MV_SEPARATE(interval|*)|ACTIVE|WAIT(int|*)]&
        Selectors:
            If filters not defined, select from all opened windows
            ALL:
                Select all windows from target list
            FIRST:
                Select first window from target list
            LAST:
                Select last window from target list
        Filters:
            BY ID:
                Match window with selected id (hex string)
                Example: BY ID(0xFFFFFFFF)
            BY REGEX:
                Match window by python regex string
                Example: BY REGEX(\s+Test\s+)
            BY CONTAINS:
                Match window if title contains string
                Example: BY CONTAINS(Music)
            BY FULL:
                Match window if title match string
                Example: BY FULL(Desktop)
            BY DESK:
                Match window in selected desktop:
                <*> - current desktop
                Example: BY DESK(2)
        App runners:   
            CREATE:
                Run executable from 'app_runners' file and wait until window opened
                Use '--wait-process-timeout' for specify waiting time (5 second by default)
                Example: CREATE(firefox)
            FORCE_CREATE:
                Same as 'CREATE', but don't wait until process end, so window can't be processed in query
                Example: FORCE_CREATE(firefox)
        Processors:
            PRINT:
                Display table of target windows
            ACTIVE:
                Set active target window
                If target windows more then one, raise exception, so use filters right
            WAIT:
                Sleeps the set number of seconds
                <*> - 5 seconds
                <int> - seconds
                Example: WAIT(1)
            CLOSE:
                Close target windows
            MV_TO:
                Move selected windows to target desktop
                <*> - last desktop
                <int> - id of target desktop, >= 0
                Example: -> MV_TO(0) 
            MV_SEPARATE:
                Split selected windows between desktops
                When you create desktops range, make sure the number of windows matches the range
                Remember, desktop count starting with 0
                    <*> - foreach window new desktop (it's mean, if you select 3 windows, each window would have own desktop)
                    <interval> - specify range of target desktops
                         Available intervals syntax:
                            |1|1-       - FROM
                            -3          - TO
                            1-3         - RANGE
                            1,3,5       - SEQUENCE
                        
For more info: https://github.com/rostegg/wizarddes
"""

def get_params():
    parser = argparse.ArgumentParser(description="Automatize your desktop management", epilog=epilog_msg, formatter_class=RawTextHelpFormatter)
    parser.add_argument('scenario_name', type=str, help=f"Name of rules file in '{rules_storage_path}' folder",
                    nargs='?', default='default')
    parser.add_argument("--wait-process-timeout", type=int, help="Timeout for wait 'CREATE' process in seconds (5 by default)",
                    action="store", default=5)
    parser.add_argument("--queries", help="Execute queries, separated by `;;`",
                    action="store")
    parser.add_argument("--single-query", help="Execute single query",
                    action="store")
    parser.add_argument("--query-file", help="Full path to query file",
                    action="store")
    parser.add_argument("--debug-mode", help="Execute in debug mode",
                    action="store_true")
    parser.add_argument("--rules-list", help=f"Display available rules files in '{rules_storage_path}' folder",
                    action="store_true")
    parser.add_argument("--use-wmctrl", help="Use `wmctrl` util instead of xlib",
                    action="store_true")
    options = parser.parse_args()
    return options

options = get_params()

if (options.use_wmctrl):
    if (not Utils.wmctrl_status()):
        PrintUtil.log_error("Seems, like `wmctrl` is not installed...")
        exit(1)
else:
    from Xlib import display, X, protocol

class WindowsManager(object):
    def get_windows_list(self):
        raise NotAvailableOperatioException("Not implemented 'get_windows_list'")

    def get_desktops_list(self):
        raise NotAvailableOperatioException("Not implemented 'get_desktops_list'")
        
    def mv_to(self, window_id, desktop_id):
        raise NotAvailableOperatioException("Not implemented 'mv_to'")

    def close(self, window_id):
        raise NotAvailableOperatioException("Not implemented 'close'")
    
    def switch(self, desktop_id):
        raise NotAvailableOperatioException("Not implemented 'switch'")
    
    def active(self, window_id):
        raise NotAvailableOperatioException("Not implemented 'active'")

# later should change data formats for windows info
# https://specifications.freedesktop.org/wm-spec/wm-spec-latest.html
class XlibUtils(WindowsManager):
    def __init__(self, target_display = None, root = None):
        self.display = target_display or display.Display()
        self.root = self.display.screen().root
        self.required_windows_fields = {
            'desktopId' : '_NET_WM_DESKTOP',
            'pid' : '_NET_WM_PID',
            'client' : 'WM_CLIENT_MACHINE',
            'windowTitle' : '_NET_WM_NAME' 
        }
    
    # <windowId> <desktopId> <pid> <client> <windowTitle>
    def get_windows_list(self):
        target_windows = [ self.__create_window(w) for w in self.__get_property('_NET_CLIENT_LIST', False) ]
        windows_list = list() 
        for window in target_windows:
            window_data_object = {}
            window_data_object['windowId'] = Utils.to_hex(window.id)
            for key, value in self.required_windows_fields.items():  
                value = self.__get_property(value, target=window)
                window_data_object[key] = value
            windows_list.append(window_data_object)
        return windows_list
    
    # <desktopId> <active> <geometry> <viewport> <workAreaGeometry> <workAreaResolution> <title>
    def get_desktops_list(self):
        desktops_list = list()
        desktops_work_area_geometry = self.__get_property('_NET_WORKAREA', False)
        desktops_geometry = self.__get_property('_NET_DESKTOP_GEOMETRY',False)
        current_desktop = int(self.__get_property('_NET_CURRENT_DESKTOP'))
        desktops_count = int(self.__get_property('_NET_NUMBER_OF_DESKTOPS'))
        view_port = self.__get_property('_NET_DESKTOP_VIEWPORT', False)
        for desktop_id in range(0,desktops_count):
            desktop_data_object = {}
            desktop_data_object['desktopId'] = desktop_id
            desktop_data_object['active'] = '*' if desktop_id == current_desktop else '-'
            work_area_data = desktops_work_area_geometry[desktop_id*4:desktop_id*4+4]
            PrintUtil.log_debug(f"Recieved '_NET_DESKTOP_GEOMETRY' respons from X Server for '{desktop_id}':")
            PrintUtil.log_debug_object(work_area_data)
            desktop_data_object['workAreaGeometry'] = f"{work_area_data[0]}.{work_area_data[1]}"
            desktop_data_object['workAreaResolution'] = f"{work_area_data[2]}x{work_area_data[3]}"
            desktop_data_object['geometry'] = f"{desktops_geometry[0]}x{desktops_geometry[1]}"
            desktop_data_object['viewport'] = f"{view_port[0]},{view_port[1]}" if desktop_id == current_desktop else 'N/A'
            # add desktops name later
            desktops_list.append(desktop_data_object)
        return desktops_list

    def mv_to(self, window_id, desktop_id):
        window = self.__create_window(int(window_id, 16))
        self.__set_property('_NET_WM_DESKTOP', [int(desktop_id), 1], target=window)
        self.__flush()

    def close(self, window_id):
        window = self.__create_window(int(window_id, 16))
        self.__set_property('_NET_CLOSE_WINDOW', [X.CurrentTime, 1], target=window)
        self.__flush()

    def active(self, window_id):
        window_id = int(window_id, 16)
        window = self.__create_window(window_id)
        target_desktop = self.__get_property('_NET_WM_DESKTOP', target = window)
        self.switch(target_desktop)
        self.__set_property('_NET_ACTIVE_WINDOW', [1, X.CurrentTime, window_id], target=window)
        self.__flush()

    def switch(self, desktop_id):
        desktop_id = int(desktop_id)
        self.__set_property('_NET_CURRENT_DESKTOP', [desktop_id, X.CurrentTime])
        self.__flush()

    def __parse_value(self, value, single):
        value = value.decode() if isinstance(value, (bytes, bytearray)) else value
        value = (str(value[0]) if single else value) if isinstance(value, (array)) else value
        return value

    def __set_property(self, atom_type, data, target = None):
        target = self.root if target is None else target
        
        data = (data+[0]*(5-len(data)))[:5]
        dataSize = 32

        ev = protocol.event.ClientMessage(
            window=target,
            client_type=self.display.get_atom(atom_type), data=(dataSize,data))
    
        mask = (X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            
        self.display.send_event(self.root, ev, event_mask=mask)

    def __flush(self):
        self.display.flush()

    def __get_property(self, atom_type, single = True,target = None):
        target = self.root if target is None else target
        atom = target.get_full_property(self.display.get_atom(atom_type), X.AnyPropertyType)
        return self.__parse_value(atom.value, single) if hasattr(atom, 'value') else None

    def __create_window(self, window_id):
        return self.display.create_resource_object('window', window_id) if window_id is not None else None

class WmctrlUtils(WindowsManager):
    # <windowId> <desktopId> <pid> <client> <windowTitle>
    def get_windows_list(self):
        output_str = self.__execute_wmctrl(['-lp'])
        regex_window_list = re.compile(r'(?P<windowId>0x[0-9A-Fa-f]{8})\s+(?P<desktopId>[0-9]+)\s+(?P<pid>[0-9]+)\s+(?P<client>[A-Za-z0-9]+)\s+(?P<windowTitle>.+)', re.MULTILINE)
        return Utils.dict_from_regex(output_str, regex_window_list)

    # <desktopId> <active> <geometry> <viewport> <workAreaGeometry> <workAreaResolution> <title>
    def get_desktops_list(self):
        output_str = self.__execute_wmctrl(['-d'])  
        regex_desktop_list = re.compile(r'(?P<desktopId>[0-9]+)\s+(?P<active>[-*]{1})\s+DG:\s+(?P<geometry>[0-9]{1,5}x[0-9]{1,5})\s+VP:\s+(?P<viewPort>N/A|(?:[0-9]{1,5}\,[0-9]{1,5}))\s+WA:\s+(?P<workAreaGeometry>[0-9]{1,5}\,[0-9]{1,5})\s+(?P<workAreaResolution>[0-9]{1,5}x[0-9]{1,5})\s+(?P<title>[\s\w/]+\n)', re.MULTILINE)
        return Utils.dict_from_regex(output_str, regex_desktop_list)
    
    def __execute_wmctrl(self, task):
        task = ['wmctrl'] + task
        PrintUtil.log_debug(f"Executing wmctrl task: {task}")
        p = Popen(task, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        rc = p.returncode
        if rc == 1:
            raise WmctrlExeption(f"Can't execute `wmctrl` command '{' '.join(task)}', exit code: `1`, error: {err.decode()}")
        return output.decode("utf-8")
    
    def mv_to(self, window_id, desktop_id):
        command = ['-ir', window_id, '-t', desktop_id]
        self.__execute_wmctrl(command)

    def close(self, window_id):
        command = ['-ic', window_id]
        self.__execute_wmctrl(command)
    
    def switch(self, desktop_id):
        command = ['-s' ,desktop_id]
        self.__execute_wmctrl(command)
    
    def active(self, window_id):
        command = ['-ia', window_id]
        self.__execute_wmctrl(command)

windows_manager = WmctrlUtils() if options.use_wmctrl else XlibUtils()
PrintUtil.log_debug(f"Selected windows manger: {windows_manager}")

class RangeFilters:
    filter_all = lambda arr: arr
    filter_first = lambda arr : [ arr[0] ]
    filter_last = lambda arr : [ arr[-1] ]

class DataFilters:
    filter_by_id = lambda windows_list, filter_value: [ window for window in windows_list if filter_value == window['windowId'] ]
    filter_by_contains = lambda windows_list, filter_value: [ window for window in windows_list if filter_value in window['windowTitle'] ]
    filter_by_regex = lambda windows_list, filter_value: [ window for window in windows_list if re.match(filter_value, window['windowTitle']) ] 
    filter_by_full = lambda windows_list, filter_value: [ window for window in windows_list if filter_value ==  window['windowTitle'] ]
    filter_by_desk =lambda windows_list, filter_value: [ window for window in windows_list if filter_value == window['desktopId'] ]

class FilterObject:
    def __init__(self, filter_func, filter_value):
        self.filter_func = filter_func
        self.filter_value = filter_value

    def filter(self, target_list):
        result = self.filter_func(target_list, self.filter_value)
        if len(result) == 0:
            raise EmptyQueryResult("Zero result found for query..") 
        return result

class Validators:
    @staticmethod
    def is_window_id_valid(id):
        reg = r"0x[0-9A-Fa-f]{8}"
        return False if re.fullmatch(reg,id) is None else True
    
    @staticmethod
    def is_desktop_is_valid(id):
        try:
            desktop_list = windows_manager.get_desktops_list()
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
        except IndexError:
            PrintUtil.log_warn(f"Can't parse 'app_runners' line, maybe wrong delimeter")

    def get_runner(self, name):
        try:
            return self.__loaders[name]
        except KeyError:
            raise WrongQueryParameterException(f"Can't find '{name}' runner in {self.app_runners_path}")

app_runners = AppRunnersLoader() 

class TokenExecutors:
    # range filters
    @staticmethod    
    def all_token_execute(state):
        state['range_filter_processor'] = RangeFilters.filter_all
        PrintUtil.log_debug(f"Executing 'ALL' token, append range_filter_processor as {state['range_filter_processor']}")
        return state

    @staticmethod
    def first_token_execute(state):
        state['range_filter_processor'] = RangeFilters.filter_first
        PrintUtil.log_debug(f"Executing 'FIRST' token, append range_filter_processor as {state['range_filter_processor']}")
        return state

    @staticmethod
    def last_token_execute(state):
        state['range_filter_processor'] = RangeFilters.filter_last
        PrintUtil.log_debug(f"Executing 'LAST' token, append range_filter_processor as {state['range_filter_processor']}")
        return state

    # data filters
    @staticmethod
    def by_token_execute(state):
        return Utils.assert_filters_list(state)

    @staticmethod
    def id_token_execute(state):
        if (not Validators.is_window_id_valid(state['value'])): 
            raise WrongQueryParameterException(f"Not valid window id `{state['value']}` in `BY ID() filter`")
        filter_object = FilterObject(DataFilters.filter_by_id, state['value'])
        state['data_filter_processor'] += [ filter_object ]
        PrintUtil.log_debug(f"Executing 'ID' token, append data_filter_processor as {state['data_filter_processor']}")
        return state

    @staticmethod
    def contains_token_execute(state):
        filter_object = FilterObject(DataFilters.filter_by_contains, state['value'])
        state['data_filter_processor'] += [ filter_object ]
        PrintUtil.log_debug(f"Executing 'CONTAINS' token, append data_filter_processor as {state['data_filter_processor']}")
        return state

    @staticmethod
    def desk_token_execute(state):
        def current_desktop_id():
            return str(next(desktop['desktopId'] for desktop in state['desktopManager'].desktop_list if desktop['active'] == "*"))

        state['value'] = current_desktop_id() if state['value'] == Tokens.DEFAULT_SCENARIO_TOKEN else state['value']
        if (not Validators.is_desktop_is_valid(state['value'])):
            raise WrongQueryParameterException(f"Not valid desktop id `{state['value']}` in `BY DESK() filter`")
        filter_object = FilterObject(DataFilters.filter_by_desk, state['value'])
        state['data_filter_processor'] += [ filter_object ]
        PrintUtil.log_debug(f"Executing 'DESK' token, append data_filter_processor as {state['data_filter_processor']}")
        return state

    @staticmethod
    def full_token_execute(state):
        filter_object = FilterObject(DataFilters.filter_by_full, state['value'])
        state['data_filter_processor'] += [ filter_object ]
        PrintUtil.log_debug(f"Executing 'FULL' token, append data_filter_processor as {state['data_filter_processor']}")
        return state

    @staticmethod
    def regex_token_execute(state):
        filter_object = FilterObject(DataFilters.filter_by_regex, state['value'])
        state = Utils.assert_filters_list(state)
        state['data_filter_processor'] += [ filter_object ]
        PrintUtil.log_debug(f"Executing 'REGEX' token, append data_filter_processor as {state['data_filter_processor']}")
        return state

    # actions
    @staticmethod
    def mvto_token_execute(state):
        def determine_dekstop_by_context():
            # select last desktop if value is DEFAULT_SCENARIO_TOKEN  and context is None
            current_last_desktop = str(len(state['desktopManager'].desktop_list)-1) 
            if 'context' not in state:
                return current_last_desktop
            else:
                if 'mv_to_dekstop' not in state['context']:
                    state['context']['mv_to_dekstop'] = current_last_desktop
                return state['context']['mv_to_dekstop']

        PrintUtil.log_debug(f"Executing 'MV_TO' token, target list:")
        PrintUtil.log_debug_object(state['target_list'])
        # use context if multiple queries
        target_desktop = state['value'] if state['value'] != Tokens.DEFAULT_SCENARIO_TOKEN else determine_dekstop_by_context()
        for window in state['target_list']:
            windows_manager.mv_to(window['windowId'], target_desktop)
            wait()
        return state

    @staticmethod
    def mvseparate_token_execute(state):
        PrintUtil.log_debug(f"Executing 'MV_SEPARATE' token")
        state['desktopManager'].distributeWindows(state['target_list'], state['value'])
        return state

    @staticmethod
    def close_token_execute(state):
        PrintUtil.log_debug(f"Executing 'CLOSE' token, target list:")
        PrintUtil.log_debug_object(state['target_list'])
        for window in state['target_list']:
            windows_manager.close(window['windowId'])
            wait()
        return state

    @staticmethod
    def switch_token_execute(desktop_id):
        PrintUtil.log_debug(f"Executing 'SWITCH' token on desktop '{desktop_id}'")
        if (not Validators.is_desktop_is_valid(desktop_id)):
            raise WrongQueryParameterException(f"Not valid desktop id '{desktop_id}' in `SWITCH`, maybe desktop not yet created")
        windows_manager.switch(desktop_id)

    @staticmethod
    def wait_token_execute(state):
        try:
            default_seconds = 5
            seconds = default_seconds if state['value'] == Tokens.DEFAULT_SCENARIO_TOKEN or int(state['value']) < 0 else int(state['value'])
            PrintUtil.log_debug(f"Executing 'WAIT' token for '{seconds}' seconds")
            sleep(seconds)
        except ValueError:
            raise ExecuteQueryException(f"Can't convert 'WAIT' value to int")
        finally:
            return state

    @staticmethod
    def active_token_execute(state):
        target = state['target_list']
        if len(target) != 1:
            raise ExecuteQueryException(f"Can't set `ACTIVE` for {len(target)} windows, only single target...")
        target = target[0]['windowId']
        PrintUtil.log_debug(f"Executing 'ACTIVE' token, on <{target}> window")
        if (not Validators.is_window_id_valid(target)):
            raise WrongQueryParameterException(f"Not valid window id {target} for `ACTIVE`")
        windows_manager.active(target)
        return state
    
    @staticmethod
    def print_token_execute(state):
        target = state['target_list']
        table_formater = PrintUtil.TableFormater(target)
        table_formater.print_table()
        return state

    @staticmethod
    def conversion_token_execute(state):
        PrintUtil.log_debug(f"Executing '->' token")
        target_list = state['target_list'] if 'target_list' in state else windows_manager.get_windows_list()
        PrintUtil.log_debug(f"Decided target list :")
        PrintUtil.log_debug_object(target_list)
        if 'data_filter_processor' in state:
            PrintUtil.log_debug(f"Detected data filter: {state['data_filter_processor']}")
            for filter_object in state['data_filter_processor']:
                target_list = filter_object.filter(target_list)
            PrintUtil.log_debug(f"After data filter target list is:")
            PrintUtil.log_debug_object(target_list)
        if 'range_filter_processor' in state:
            PrintUtil.log_debug(f"Detected range filter: {state['range_filter_processor']}")
            target_list = state['range_filter_processor'](target_list)
            PrintUtil.log_debug(f"After range filter target list is:")
            PrintUtil.log_debug_object(target_list)
        state['target_list'] = target_list
        return state
    
    @staticmethod
    def force_create_token_execute(state):
        app_runner = app_runners.get_runner(state['value'])
        PrintUtil.log_debug(f"Executing 'FORCE_CREATE' token, for '{app_runner}' runner")
        Popen(app_runner.split(' '), stdin=PIPE, stdout=PIPE, stderr=PIPE)
        return state

    @staticmethod
    def create_token_execute(state):
        # timeout for long running processes
        def app_pids(app):
            # need check for fullpath executable, like /usr/bin/script-name and grep by last part (script-name)
            ps_cux_output = check_output(["ps", "aux"]).decode().split('\n')
            # determine, if app runners is complex and contains global path 
            target_app = app.split(' ')[0]
            target_app = target_app.split('/')[-1]
            target_procs = [proc for proc in ps_cux_output if target_app in proc]
            if len(target_procs) == 0:
                return []
            pid_regex = re.compile(r'[A-Za-z\.\_\-]+\s+(?P<pid>[0-9]{1,7})\s+', re.MULTILINE)
            pids = [ m['pid'] for m in pid_regex.finditer("\n".join(target_procs)) ]
            return pids

        app_runner = app_runners.get_runner(state['value'])
        PrintUtil.log_debug(f"Executing 'CREATE' token, for '{app_runner}' runner")
        
        # take last proc pid in list
        windows_snapshot = windows_manager.get_windows_list()
        windows_snapshot_count = len(windows_snapshot)
        PrintUtil.log_debug(f"Taking windows snapshot, '{windows_snapshot_count}' windows found")
        PrintUtil.log_debug_object(windows_snapshot)
        
        '''
            Method above would create background process with pid not like the parent process
            So, for now using p.wait() for wait of ending of ui loading
            os.system(f"{app_runner} &")
        '''
        p = Popen(app_runner.split(' '), stdin=PIPE, stdout=PIPE, stderr=PIPE)
        try:
            PrintUtil.log_debug(f"Wait timeout set to {options.wait_process_timeout}")
            p.wait(timeout=options.wait_process_timeout)
        except TimeoutExpired:
            PrintUtil.log_warn(f"Process {app_runner} is still alive, well, lets try to catch him (or use 'FORCE_CREATE -> WAIT' query for singlethread processes)")
        rc = p.returncode
        if rc == 1:
            raise ExecuteQueryException(f"Can't execute runner '{app_runner}', exit code: `1`")

        current_windows = windows_manager.get_windows_list()
        wait_lock = True
        
        pids = app_pids(app_runner)
        if (len(pids) == 0):
            raise ExecuteQueryException(f"Can't find PID for '{app_runner}, maybe process freezed and don't started'")
        PrintUtil.log_debug(f"{len(pids)} processes for '{app_runner}' runner found")
        PrintUtil.log_debug_object(pids)
        # not sure about child pid. but for now it's work fine, maybe should try to obtain more info?
        #pid = pids[0]
        PrintUtil.log_debug(f"Starting monitoring for the formation of '{app_runner}' window")
        while wait_lock:
            # wait for new windows opening
            while windows_snapshot_count == len(current_windows):
                current_windows = windows_manager.get_windows_list()
                wait()
            # check for target window   
            intersect = [ window for window in current_windows if (window not in windows_snapshot) ]
            for window in intersect:
                if window['pid'] in pids:
                    state['target_list'] = [ window ]
                    wait_lock = False
                    break
            windows_snapshot = current_windows
            windows_snapshot_count = len(windows_snapshot)
        PrintUtil.log_debug(f"Target window for '{app_runner}' found")
        PrintUtil.log_debug_object(state['target_list'])
        return state

EXECUTOR_FUNCS = {
    Tokens.ALL : TokenExecutors.all_token_execute,
    Tokens.FIRST : TokenExecutors.first_token_execute,
    Tokens.LAST : TokenExecutors.last_token_execute,
    Tokens.ID : TokenExecutors.id_token_execute,
    Tokens.CONTAINS: TokenExecutors.contains_token_execute,
    Tokens.FULL: TokenExecutors.full_token_execute,
    Tokens.REGEX: TokenExecutors.regex_token_execute,
    Tokens.SWITCH: TokenExecutors.switch_token_execute,
    Tokens.ACTIVE: TokenExecutors.active_token_execute,
    Tokens.MV_SEPARATE: TokenExecutors.mvseparate_token_execute,
    Tokens.MV_TO: TokenExecutors.mvto_token_execute,
    Tokens.CLOSE: TokenExecutors.close_token_execute,
    Tokens.DESK: TokenExecutors.desk_token_execute,
    Tokens.CONVERSION_OPERATOR: TokenExecutors.conversion_token_execute,
    Tokens.CREATE: TokenExecutors.create_token_execute,
    Tokens.WAIT: TokenExecutors.wait_token_execute,
    Tokens.FORCE_CREATE: TokenExecutors.force_create_token_execute,
    Tokens.BY: TokenExecutors.by_token_execute,
    Tokens.PRINT: TokenExecutors.print_token_execute
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
            PrintUtil.log_debug(f"Moving window <{targets_list[index]['windowId']}> to {desktop_id}")
            windows_manager.mv_to(targets_list[index]['windowId'], str(desktop_id))
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
        # not sure about sequence parser
        #sequence_regex = r"(?:[0-9]{1,3},){2,}[0-9]{1,3}$"
        sequence_regex = r"(?:[0-9]+\,*)+"
        primal_regex = re.compile(r"(?P<fromId>[0-9]{1,3})?\-?(?P<toId>[0-9]{1,3})?")
        if (re.fullmatch(sequence_regex, cleared_interval) is not None):
            PrintUtil.log_debug(f"Detected sequence interval type")
            return list(map(int, cleared_interval.split(',')))
        else:
            # maybe change primal regex later, to avoide excess data (false positive triggering, because all <?>)
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
        desktop_list = windows_manager.get_desktops_list()
        PrintUtil.log_debug(f"Desktop list on moment, when query executor was created :")
        PrintUtil.log_debug_object(desktop_list)
        self.state['desktopManager'] = DesktopManager(desktop_list)
    
    def execute(self, context = None):
        try:
            if context:
                self.state['context'] = context

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
            return self.state['context'] if 'context' in self.state else None
        except KeyError: 
            raise ExecuteQueryException(f"Can't execute query {self.query}, it seems that the query is not composed correctly (or no executor implemented)")

    def __is_valid_value(self, token, value):
        if not Tokens.is_value_token(value):
            raise WrongQueryParameterException(f"Seems, like after `{token}` expected value, but it's `{value}`")

    def __execute_unary_operator(self, tokenType):
        PrintUtil.log_debug(f"Executing unary operator '{tokenType}'")
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
            PrintUtil.log_error(f"Error occurring, while parsing tokens for `{self.expression}`:")
            PrintUtil.log_error(str(ex))

    def execute(self, context = None):
        try:
            context = self.query_executor.execute(context)
            PrintUtil.log_success(f"Successfully executed '{self.expression}' query")
            return context
        except (WrongQueryParameterException, ExecuteQueryException, WmctrlExeption, EmptyQueryResult, NotAvailableOperatioException, TableFormaterException) as ex:
            PrintUtil.log_error(f"Error occurring, while executing `{self.expression}`:")
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
            raise ParseTokenException(f"Bad token: {token}")
        return [ result['token'], result['tokenValue'] ]

# main script

def execute_single_query(query, context = None):
    PrintUtil.log_info(f"Execute single query: {query}")
    context and PrintUtil.log_debug("Passed context: ")
    context and PrintUtil.log_debug_object(context)
    tokenizer = TokenParser(query)
    return tokenizer.execute(context)

def execute_queries(queries):
    # add later
    context = {'general_context' : True}
    queries_arr = queries.split(';;')
    for query in queries_arr:
        context = execute_single_query(query, context)

def parse_query_file(file_path):
    return open(file_path).read().splitlines()

def execute_rules_from_file(file_path):
    try:
        context = {'general_context' : True}
        PrintUtil.log_debug(f"Trying to parse {file_path} file")
        queries = parse_query_file(file_path)
        for query in queries:
            context = execute_single_query(query, context)
    except FileNotFoundError:
        PrintUtil.log_error(f"Can't read '{file_path}' query file, check if it exist or have right permissions")
        exit(1)

def print_rules_list():
    try:
        rules_files = [f for f in os.listdir(rules_storage_path) if os.path.isfile(os.path.join(rules_storage_path, f))]
        PrintUtil.log_success(f"Available rules files ({len(rules_files)}):")
        for rule in rules_files:
            PrintUtil.log_indent(rule)
    except:
        PrintUtil.log_error(f"Can't list '{rules_storage_path}' directory, check if it exist or have right permissions")
        exit(1)

def main():
    if options.rules_list:
        print_rules_list()
    elif options.single_query:
        execute_single_query(options.single_query)
    elif options.queries:
        execute_queries(options.queries)
    elif options.query_file:
        execute_rules_from_file(options.query_file)
    else:
        execute_rules_from_file(os.path.join(rules_storage_path, options.scenario_name))

if __name__ == "__main__":
    main()