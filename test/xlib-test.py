#!/usr/bin/env python3
from ewmh import EWMH
from Xlib import display, X, protocol
from array import array

def to_hex(s):
    def zpad_hex(s):
        return '0x' + s[2:].zfill(8)
    return zpad_hex(hex(s))

class XlibManager:
    def __init__(self, target_display = None, root = None):
        self.display = target_display or display.Display()
        self.root = self.display.screen().root
        self.required_windows_fieds = {
            'desktopId' : '_NET_WM_DESKTOP',
            'pid' : '_NET_WM_PID',
            'client' : 'WM_CLIENT_MACHINE',
            'windowTitle' : '_NET_WM_NAME' 
        }
    
    # <windowId> <desktopId> <pid> <client> <windowTitle>
    def get_windows_list(self):
        target_windows = [ self.__create_window(w) for w in self.__get_property('_NET_CLIENT_LIST',False)]
        #for win in target_windows:
        #    print(win)
        windows_list = list() 
        for window in target_windows:
            window_data_object = {}
            window_data_object['windowId'] = to_hex(window.id)
            for key, value in self.required_windows_fieds.items():  
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

    def close(self, window_id):
        window = self.__create_window(int(window_id, 16))
        self.__set_property('_NET_CLOSE_WINDOW', [X.CurrentTime, 1], target=window)

    def active(self, window_id):
        window_id = int(window_id, 16)
        window = self.__create_window(window_id)
        target_desktop = self.__get_property('_NET_WM_DESKTOP', target = window)
        self.switch(target_desktop)
        self.__set_property('_NET_ACTIVE_WINDOW', [1, X.CurrentTime, window_id], target=window)

    def switch(self, desktop_id):
        desktop_id = int(desktop_id)
        self.__set_property('_NET_CURRENT_DESKTOP', [desktop_id, X.CurrentTime])

    def __parse_value(self, value, single):
        value = value.decode() if isinstance(value, (bytes, bytearray)) else value
        value = (str(value[0]) if single else value) if isinstance(value, (array)) else value
        return value

    def __get_property(self, atom_type, single = True, target = None):
        target = self.root if target is None else target
        atom = target.get_full_property(self.display.get_atom(atom_type), X.AnyPropertyType)
        return self.__parse_value(atom.value, single) if hasattr(atom, 'value') else None

    def __set_property(self, atom_type, data, target = None):
        target = self.root if target is None else target
        
        data = (data+[0]*(5-len(data)))[:5]
        dataSize = 32

        ev = protocol.event.ClientMessage(
            window=target,
            client_type=self.display.get_atom(atom_type), data=(dataSize,data))
    
        mask = (X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            
        self.display.send_event(self.root, ev, event_mask=mask)
        self.display.flush()

    def __create_window(self, window_id):
        return self.display.create_resource_object('window', window_id) if window_id is not None else None

manager = XlibManager()
