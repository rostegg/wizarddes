#!/usr/bin/env python3
from ewmh import EWMH
from Xlib import display, X, protocol

#dsp = display.Display()
ewmh = EWMH()

def zpad_hex(s):
    return '0x' + s[2:].zfill(8)
wins = ewmh.getClientList()
print(wins[-1].get_full_property(ewmh.display.get_atom("_NET_WM_PID"), X.AnyPropertyType).value)
print(wins[-1].get_full_property(ewmh.display.get_atom("WM_CLIENT_MACHINE"), X.AnyPropertyType).value)
print(wins[-1].get_full_property(ewmh.display.get_atom("_NET_WM_DESKTOP"), X.AnyPropertyType).value)
print(wins[-1].get_full_property(ewmh.display.get_atom("_WIN_WORKSPACE"), X.AnyPropertyType))
print(wins[-1].get_full_property(ewmh.display.get_atom("WM_NAME"), X.AnyPropertyType))
print(wins[-1].get_full_property(ewmh.display.get_atom("_NET_WM_NAME"), X.AnyPropertyType).value)

print(zpad_hex(hex(wins[-1].id)))
'''
 /* desktop ID */
if ((desktop = (unsigned long *)get_property(disp, client_list[i],
XA_CARDINAL, "_NET_WM_DESKTOP", NULL)) == NULL) {
desktop = (unsigned long *)get_property(disp, client_list[i],
        XA_CARDINAL, "_WIN_WORKSPACE", NULL);
}

/* client machine */
client_machine = get_property(disp, client_list[i],
XA_STRING, "WM_CLIENT_MACHINE", NULL);

/* pid */
pid = (unsigned long *)get_property(disp, client_list[i],
XA_CARDINAL, "_NET_WM_PID", NULL);

'''