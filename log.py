from datetime import datetime

logfile = open('sbot.log', 'a', encoding='utf-8')

def write(text):
	line = '%s %s' % (datetime.now(), text)
	if 0 <= line.rfind('\n') < len(line)-1:
		line += '\n\n'
	else:
		line += '\n'

	print(line, end='')
	logfile.write(line)

def flush():
	logfile.flush()

def close():
	logfile.close()
