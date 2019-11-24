# Automate your desktop windows management with single script.

Wizarddes - it's 'single-file' script without dependcies (well, almost), which allow automate windows management, like close window or move it to another virtual desktop.   
  
<!-- TOC depthFrom:1 depthTo:3 withLinks:1 updateOnSave:1 orderedList:0 -->
* [Features](#features)
* [Install](#install)
    - [pip](#pip)
    - [wmctrl](#wmctrl)
* [Usage](#usage)
* [Query language](#query-language)
* [Queries examples](#examples)
<!-- /TOC -->
  
## Features

* Open apps windows
* Filter windows (by id, title match, etc)  
* Distribute windows between desktops range  
* Close, move windows  
* Simple query langauge to describe tasks  
* Single and multiple tasks execution 
* Execution queries from file

## Install

There are two options for interacting with X Server, using [wmctrl](https://linux.die.net/man/1/wmctrl) as middleware or install python dependcies using `pip`  

The dependency option is preferable, because it has more features.

#### pip
```
pip install python-xlib
```
#### wmctrl

* ##### Ubuntu:  
```
$ sudo apt install wmctrl
```

Now, just clone repository and run `install.sh`

You can use oneliner for install only script, but then you have to create folders for additional data yourself  

Script donwloads:  
* curl
```
$ curl https://raw.githubusercontent.com/rostegg/wizarddes/master/wizarddes.py --output wizarddes && chmod +x wizardess && sudo mv wizarddes /usr/bin/wizarddes
```
* wget
```
$ wget -O wizarddes https://raw.githubusercontent.com/rostegg/wizarddes/master/wizarddes.py&& chmod +x wizardess && sudo mv wizarddes /usr/bin/wizarddes
```

Execute `wizzardes --help` to check if it installed right   

Before usage, check [usage](#usage) section

## Usage

Wizarddes app data path: $HOME/.wizarddes

If you download only script with oneliner, then you need to create this folder, to use more advanced features  

:warning:For usage with `wmctrl` don't forget `--use-wmctrl` option, wizarddes uses xlib by default  

App folder contains:  
* rules - [folder](https://github.com/rostegg/wizarddes/tree/master/rules), where store rules snippets for quick access  
  - Queries in files must be separated by newline
  - :warning: Tokens is case sensitive
* app_runer - [file](https://github.com/rostegg/wizarddes/blob/master/app_runners), which store runners for applications
  - Runners must be splited by `::` separator
  - Left part - alias, right part - command, which create window

Options:  
```
positional arguments:
  scenario_name         Name of rules file in wizarddes folder (by default - 'default')

optional arguments:
  --wait-process-timeout WAIT_PROCESS_TIMEOUT
                        Timeout for wait 'CREATE' process in seconds (5 by default)
  --queries QUERIES     Execute queries, separated by `;;`
  --single-query SINGLE_QUERY
                        Execute single query
  --query-file FILE_PATH
                        Execute query from custom file
  --debug-mode          Execute in debug mode
  --rules-list          Display available rules files in wizarddes folder
  --use-wmctrl          Use `wmctrl` util instead of xlib

```

Usage examples:  
* Execute default rules in `$HOME/.wizarddes/rules/default` file:  
```
wizzardes
```
* Execute named rules in `$HOME/.wizarddes/rules/rules_name` file: 
```
wizzardes rules_name
```
* List of rules `$HOME/.wizarddes/rules` folder: 
```
wizzardes --rules-list
```
* Execute single query: 
```
wizzardes --single-query "ALL BY CONTAINS(Firefox) -> CLOSE"
```
* Execute multiple queries: 
```
wizzardes --queries "ALL BY CONTAINS(Firefox) -> CLOSE;;SWITCH(0)"
```
* Execute in debug mode: 
```
wizzardes --single-query "ALL BY CONTAINS(Firefox) -> CLOSE" --debug-mode
```

Also, you can create really usefull linux aliases, something like this:  
```
$ echo "clear_desk() { wizarddes --single-query \"ALL BY DESK(\"\$1\") -> CLOSE\" ; }" >> ~/.bash_aliases
$ source ~/.bash_aliases
```
This snippet will close all windows on the specified virtual desktop, for example `clear_desk 0` would close all windows at first desktop  

How create queries and available command check [query language](#query-language) section or just jump to [examples](#examples) section  

## Query language
:warning: Tokens is case sensitive  
:warning: Token parser split tokens by space(or any non word delimeters, like tabs, etc), so don't forget to put spaces between tokens (expect tokens with value, for them you can choose whether to set delimiters or not)     


Basic rules for queuing:
* Tokens executing by left-to-right
* There are operators such as 'unary', which executed as one function
* Conversion operator (->) split query for two parts:
  - Left (data selecting) - select and filter existing windows and return target windows
    - Allowed multiple filters tokens, but only single selector
    - Selectors are executed as last operators in data selecting part 
    - CREATE also relate to data selecting part, it return created window, so no sense to use filters and selector with this operator
    - FORCE_CREATE don't return created window, it is used in combination with `WAIT`
  - Right (processors) - manipulate selected windows 
    - Allowed multiple processors, but separated with `&`
* Use `FORCE_CREATE` only in special cases, like app does not start well or does not spawn child processes;  
Also use it if you want just run the application and not process it at all;  
`FORCE_CREATE` don't return created window, so it can be used in pair with `WAIT` operator, or like unary operation;
* Use `--wait-process-timeout` to setup wait time for `CREATE` operator (5 seconds by default);  
Some apps don't spawn child process, therefore, the operator after a timeout sends such processes to the background thread and tries to find a new window that opens;  
So if you have apps that do not close the child process, then roughly calculate how long they will open (in my case it is 'IntelliJ', it does not signal the child process, with my settings it starts from 5 to 10 seconds);
* Some tokens accepts DEFAULT_SCENARIO_TOKEN (*) as parameter, here description for this tokens usage:
  - BY DESK(*) - filter by active desktop
  - WAIT(*) - wait for 5 seconds
  - MV_SEPARATE(*) - create range for all available desktops
  - MV_TO(*) - create new desktop and move targets windows there 
* Query executors provide some context between queries in single file (or executed with `--queries` parameter), in particular:
  - If you use multiple MV_TO(*), the context will remember the id of the desktop when it is first called, for example:
    - You have two active desktops
    - You want execute queries like `CREATE(app) -> MV_TO(*);;CREATE(app2) -> MV_TO(*)`
    - Wizarddes will create a third desktop and move 'app' and 'app2' there, because context remember first call of MV_TO
    

Description:  
```
Unary operators:
    Query: SWITCH(desktopId) | PRINT_DESKTOPS
        SWITCH: 
            Switch active desktop
                <desktopId> - id of target desktop, starting from 0 (int, >= 0)
        PRINT_DESKTOPS:
            Print table of active desktops

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
```
## Examples

* Example of query, which create development environment at single desktop (like [this](https://github.com/rostegg/wizarddes/blob/master/rules/java-dev-env))

![](../assets/wizarddes-example.gif)


* Get all 'Firefox' instance and move them to third desktop:  
    `ALL BY CONTAINS(Firefox) -> MV_TO(3)`  
    
* Place all windows of 'Visual Code' one by one on the desktops:  
     `BY CONTAINS(Visual Code) -> MV_SEPARATE(*)`  
     
* Switch to second desktop:   
    `SWITCH(2)`  
    
* Close last window, with name 'Music':  
    `LAST BY FULL(Music) -> CLOSE`  
    
* Make active first window, which title match a regex:  
    `FIRST BY REGEX(\s+Pict\s+) -> ACTIVE`  
    
* Move all 'Chrome' windows (3) to 1-3 desktop:  
    `ALL BY CONTAINS (Chrome) -> MV_SEPARATE(1-3)`  
    
* Get all windows at second desktop and close them:   
    `ALL BY DESK(1) -> CLOSE`   

* Get all windows at current desktop which title contains 'Firefox' and close them:   
    `BY DESK(*) BY CONTAINS(Firefox) -> CLOSE`   

* Create firefox window, move it to 0 desktop and make it active:   
    `CREATE(firefox) -> MV_TO(0) & ACTIVE`   

* Create firefox window and just wait 10 seconds:   
    `FORCE_CREATE(firefox) -> WAIT(10)`

* Print all windows:   
    `ALL -> PRINT`

* Print all desktops:    
    `PRINT_DESKTOPS`