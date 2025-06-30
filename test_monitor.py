from psychopy import visual, monitors, core

print(monitors.getAllMonitors())
for idx, mon in enumerate(monitors.getAllMonitors()):
    print(idx, mon)
# Then try creating a window on each screen:
for idx in range(len(monitors.getAllMonitors())):
    print("Trying screen", idx)
    win = visual.Window(screen=idx, fullscr=True)
    core.wait(5.0)
    win.close()