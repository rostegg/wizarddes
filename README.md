# Automate your desktop windows management with single script.

Wizarddes - it's 'single-file' script without dependcies (well, almost), which allow automate windows management, like close window or move it to another virtual desktop.   
  
<!-- TOC depthFrom:1 depthTo:3 withLinks:1 updateOnSave:1 orderedList:0 -->
* [Features](#features)
* [Install](#install)
* [Usage](#usage)
* [Query language](#query-language)
* [Examples](#examples)
<!-- /TOC -->
  
## Features

* Windows filter (by id, title match, etc)  
* Distribute windows between desktops range  
* Close, move windows  
* Simple query langauge to describe tasks  
* Single and multiple tasks execution 
* Execution queries from file

```
TODO: Support for remaining commands:  
    RESIZE(mvarg)|STATE(starg)|RENAME(name)
    VIEWPORT(x,y)
```

## Install

You just need to install [wmctrl](https://linux.die.net/man/1/wmctrl)  

#### Ubuntu:  
```
$ sudo apt install wmctrl
```
  
Now, just clone repository and run `install.sh`

Or use oneliner for install only script and do not drag anything superfluous: 

* curl
```
$ curl https://raw.githubusercontent.com/rostegg/wizarddes/master/wizarddes.py --output wizarddes && chmod +x wizardess && sudo mv wizarddes /usr/bin/wizarddes
```
* wget
```
$ wget -O wizarddes https://raw.githubusercontent.com/rostegg/wizarddes/master/wizarddes.py&& chmod +x wizardess && sudo mv wizarddes /usr/bin/wizarddes
```
Execute `wizzardes --help` to check if it installed right   

Before usage check [usage](#usage) section

## Usage
Before usage you can create `/etc/rules.txt` [file](https://github.com/rostegg/wizarddes/blob/master/rules.txt), which would contains rules, executable by default, if don't specified any of options parameters:  

```
$ echo "ALL BY FULL(Music) -> CLOSE" >> rules.txt
$ sudo cp rules.txt /etc/rules.txt
$ wizarddes # will execute /etc/rules.txt commands
```
Queries in files must be separated by newline  

If you don't provide default rules file or no specified one of the option, then, you know, it will not work  

Options:  
```
  --single-query SINGLE_QUERY
                        Execute single query and nothing more
  --query-file QUERY_FILE
                        Path to custom query file
```

Also, you can create really usefull linux aliases, something like this:  
```
$ echo "clear_desk() { wizarddes --single-query \"ALL BY DESK(\"\$1\") -> CLOSE\" ; }" >> ~/.bash_aliases
$ source ~/.bash_aliases
```
This snippet will close all windows on the specified virtual desktop, for example `clear_desk 0` would close all windows at first desktop  

:warning: Remember, desktops count starting with 0

How create queries and available command check [query language](#query-language) section or just jump to [examples](#examples) section  

## Query language

:warning: Token parser split tokens by space(or any non word delimeters, like tabs, etc), so don't forget to put spaces between tokens (expect tokens with value, in them you can choose whether to set delimiters or not)    

```
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
                    <desktopId> - id of target desktops, starting from 0 (int, >= 0)
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
```
## Examples

* Get all 'Firefox' instance and move them to third desktop:  
    `ALL BY CONTAINS(Firefox) -> MV_TO(3)`  
    
* Place all windows of 'Visual Code' one by one on the desktops:  
     `ALL BY CONTAINS(Visual Code) -> MV_SEPARATE(*)`  
     
* Switch to second desktop:   
    `SWITCH(2)`  
    
* Close window, with name 'Music':  
    `SINGLE BY FULL(Music) -> CLOSE`  
    
* Make active window, which title match a regex:  
    `SINGLE BY REGEX(\s+Pict\s+) -> ACTIVE`  
    
* Move all 'Chrome' windows (3) to 1-3 desktop:  
    `ALL BY CONTAINS (Chrome) -> MV_SEPARATE(1-3)`  
    
* Get all windows at second desktop and close them:  
    `ALL BY DESK(1) -> CLOSE`  
    
