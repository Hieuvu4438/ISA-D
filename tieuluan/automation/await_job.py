from pathlib import Path
import sys,time
key=sys.argv[1]
started=time.time()
done=Path('automation/done.txt');error=Path('automation/error.txt')
for _ in range(50):
 if done.exists() and done.stat().st_mtime>started-3 and done.read_text().startswith(key):
  print(done.read_text().strip());break
 if error.exists() and error.stat().st_mtime>started-3:
  print(error.read_text());sys.exit(1)
 time.sleep(.5)
else:print('Observation timeout; inspect existing live Visual Paradigm process/job before retry.');sys.exit(2)
