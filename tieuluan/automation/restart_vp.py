"""Reload the local modelling plugin in its isolated VP workspace."""
import sys,time,subprocess
from pywinauto import Desktop
from pywinauto.timings import TimeoutError
import pyautogui as p,pyperclip
pid=int(sys.argv[1])
windows=[w for w in Desktop(backend='win32').windows() if w.process_id()==pid and 'Community Edition' in w.window_text()]
if windows:
    try:windows[0].close()
    except TimeoutError:
        modals=[w for w in Desktop(backend='win32').windows() if w.process_id()==pid and w.window_text()=='Visual Paradigm CE' and w.rectangle().width()>0]
        if modals:
            modals[0].set_focus();p.press('enter');time.sleep(2)
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
proc=subprocess.Popen([r'D:\Visual Paradigm\Visual Paradigm CE 18.0\bin\Visual Paradigm.exe'],startupinfo=startup)
print('Launched PID',proc.pid,flush=True)
for _ in range(20):
    time.sleep(1)
    ws=[w for w in Desktop(backend='win32').windows() if w.process_id()==proc.pid and w.rectangle().width()>0]
    errors=[w for w in ws if w.window_text()=='Visual Paradigm CE']
    if errors:errors[0].set_focus();p.press('enter');time.sleep(.4)
    launchers=[w for w in ws if w.window_text()=='Workspace Launcher']
    if launchers:
        d=launchers[0];d.set_focus();r=d.rectangle()
        p.click(r.left+240,r.top+138);p.hotkey('ctrl','a')
        pyperclip.copy(r'D:\PROJECTS\ISA-D\tieuluan\automation\vp-workspace');p.hotkey('ctrl','v');time.sleep(.3)
        p.click(r.left+282,r.top+243);time.sleep(3)
        break
print('Plugin reload requested',flush=True)
