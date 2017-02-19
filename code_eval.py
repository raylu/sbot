import subprocess

def nodejs(cmd):
	args = ['../nsjail/nsjail', '-Mo', '--rlimit_as', '700', '--chroot', 'chroot',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo', '--',
			'/usr/bin/nodejs', '--print', cmd.args.strip('`')]
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate()
	if proc.returncode == 0:
		output = stdout.split('\n', 1)[0]
	elif proc.returncode == 109:
		output = 'timed out after 2 seconds'
	else:
		try:
			output = stderr.split('\n', 5)[4]
		except IndexError:
			output = 'unknown error'
	reply(cmd, output)

def irb(cmd):
	args = ['../nsjail/nsjail', '-Mo', '--chroot', '',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo', '--',
			'/usr/bin/irb', '-f', '--noprompt']
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
	stdout, _ = proc.communicate(cmd.args.strip('`'))
	if proc.returncode == 109:
		output = 'timed out after 2 seconds'
	else:
		try:
			output = stdout.split('\n', 2)[2].lstrip('\n')
			output = output.split('\n', 1)[0]
		except IndexError:
			output = 'unknown error'
	reply(cmd, output)

def python3(cmd):
	args = ['../nsjail/nsjail', '-Mo', '--chroot', 'chroot', '-E', 'LANG=en_US.UTF-8',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo', '--',
			'/usr/bin/python3', '-ISqi']
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate(cmd.args.strip('`') + '\n')
	if proc.returncode == 0:
		if stderr != '>>> >>> \n':
			try:
				output = stderr.split('\n')[-3]
			except IndexError:
				output = ''
		else:
			output = stdout.split('\n', 1)[0]
	elif proc.returncode == 109:
		output = 'timed out after 2 seconds'
	else:
		output = 'unknown error'
	reply(cmd, output)

def reply(cmd, output):
	message = '%s:\n```\n%s\n```' % (cmd.sender['username'], output[:500])
	cmd.reply(message)
