import pyautogui as p
import win32gui,win32con
import sys,time
def focus():
    w=p.getWindowsWithTitle('Visual Paradigm Community')[0]
    win32gui.ShowWindow(w._hWnd,win32con.SW_MAXIMIZE)
    p.press('alt')
    win32gui.SetForegroundWindow(w._hWnd)
    time.sleep(.5)
focus()
if len(sys.argv)>1 and sys.argv[1]=='save':
    p.hotkey('ctrl','s');time.sleep(1)
elif len(sys.argv)>1 and sys.argv[1]=='close':
    p.hotkey('alt','f4');time.sleep(1)
p.screenshot().save('automation/vp-ui.png')
