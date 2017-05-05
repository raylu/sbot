from os import path
import subprocess

chroot_dir = path.join(path.dirname(path.abspath(__file__)), 'chroot')
MB = 1024 * 1024

def nodejs(cmd):
	args = ['../nsjail/nsjail', '-Mo', '--rlimit_as', '700', '--chroot', chroot_dir,
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--quiet', '--',
			'/usr/bin/nodejs', '--print', prep_input(cmd.args)]
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate()
	if proc.returncode == 0:
		output = stdout
	elif proc.returncode == 109:
		output = 'timed out'
	else:
		split = stderr.split('\n', 5)
		try:
			output = split[4]
		except IndexError:
			if split[0].startswith('FATAL ERROR:'):
				output = split[0]
			else:
				output = 'unknown error'
	reply(cmd, output)

def irb(cmd):
	args = ['../nsjail/nsjail', '-Mo', '--chroot', '',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--quiet', '--',
			'/usr/bin/irb', '-f', '--simple-prompt']
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
	stdout, _ = proc.communicate(prep_input(cmd.args))
	if proc.returncode == 109:
		output = 'timed out or memory limit exceeded'
	else:
		lines = stdout.split('\n')
		output = ''
		for line in lines[1:]:
			if not line.startswith('>> ') and not line.startswith('?>'):
				output += line + '\n'
	reply(cmd, output)

def python2(cmd):
	args = ['../nsjail/nsjail', '-Mo', '--chroot', chroot_dir, '-E', 'LANG=en_US.UTF-8',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--quiet', '--',
			'/usr/bin/python2', '-ESsi']
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate(prep_input(cmd.args) + '\n')
	if proc.returncode == 0:
		if stdout == '':
			try:
				output = stderr.split('\n')[-3]
			except IndexError:
				output = ''
		else:
			output = stdout
	elif proc.returncode == 109:
		output = 'timed out or memory limit exceeded'
	else:
		output = 'unknown error'
	reply(cmd, output)

def python3(cmd):
	args = ['../nsjail/nsjail', '-Mo', '--chroot', chroot_dir, '-E', 'LANG=en_US.UTF-8',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--quiet', '--',
			'/usr/bin/python3', '-ISqi']
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate(prep_input(cmd.args) + '\n')
	if proc.returncode == 0:
		if stdout == '':
			try:
				output = stderr.split('\n')[-3]
			except IndexError:
				output = ''
		else:
			output = stdout
	elif proc.returncode == 109:
		output = 'timed out or memory limit exceeded'
	else:
		output = 'unknown error'
	reply(cmd, output)

def prep_input(args):
	return args.strip('`').strip()

def reply(cmd, output):
	split = output.split('\n', 10)
	output = '\n'.join(split[:10])
	output = output[:500]
	if len(split) == 11:
		output += '\n(too many output lines)'
	message = '%s:\n```\n%s\n```' % (cmd.sender['username'], output)
	cmd.reply(message)
