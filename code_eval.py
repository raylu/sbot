import subprocess
from os import path

chroot_dir = path.join(path.dirname(path.abspath(__file__)), 'chroot')
MB = 1024 * 1024

def nodejs(cmd):
	args = ['../nsjail/nsjail', '--use_cgroupv2', '--cgroupv2_mount', '/sys/fs/cgroup/NSJAIL', '-Mo',
			'--rlimit_as', '700', '--chroot', chroot_dir,
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--cgroup_pids_max', '10', '--quiet', '--',
			'/usr/bin/nodejs', '--print', prep_input(cmd.args)]
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate()
	if proc.returncode == 0:
		output = stdout
	elif proc.returncode == 137:
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

def ruby(cmd):
	args = ['../nsjail/nsjail', '--use_cgroupv2', '--cgroupv2_mount', '/sys/fs/cgroup/NSJAIL', '-Mo',
			'--chroot', chroot_dir, '-R/usr', '-R/lib', '-R/lib64',
			'--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--cgroup_pids_max', '2', '--quiet', '--',
			'/usr/bin/ruby', '-Ue', 'puts begin %s end' % prep_input(cmd.args)]
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate()
	if proc.returncode == 109:
		output = 'timed out or memory limit exceeded'
	else:
		output = stdout
		if stderr:
			output += '\n' + stderr
	reply(cmd, output)

def python2(cmd):
	args = ['../nsjail/nsjail', '--use_cgroupv2', '--cgroupv2_mount', '/sys/fs/cgroup/NSJAIL', '-Mo',
			'--chroot', chroot_dir, '-E', 'LANG=en_US.UTF-8',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--cgroup_pids_max', '1', '--quiet', '--',
			'/usr/bin/python2', '-ESs', '/run.py']
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate(prep_input(cmd.args))
	if proc.returncode == 0:
		output = stdout
	elif proc.returncode == 1:
		try:
			output = stderr.split('\n')[-2]
		except IndexError:
			output = ''
	elif proc.returncode == 109:
		output = 'timed out or memory limit exceeded'
	else:
		output = 'unknown error'
	reply(cmd, output)

def python3(cmd):
	args = ['../nsjail/nsjail', '--use_cgroupv2', '--cgroupv2_mount', '/sys/fs/cgroup/NSJAIL', '-Mo',
			'--chroot', chroot_dir, '-E', 'LANG=en_US.UTF-8',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--cgroup_pids_max', '1', '--quiet', '--',
			'/usr/bin/python3', '-ISq', '/run.py']
	proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate(prep_input(cmd.args))
	if proc.returncode == 0:
		output = stdout
	elif proc.returncode == 1:
		try:
			output = stderr.split('\n')[-2]
		except IndexError:
			output = ''
	elif proc.returncode == 109:
		output = 'timed out or memory limit exceeded'
	else:
		output = 'unknown error'
	reply(cmd, output)

def prep_input(args):
	args = args.lstrip()
	if not args.startswith('```'):
		return args.strip('`').strip()

	split = args[3:].split('\n', 1)
	if len(split) == 2:
		language, other_lines = args[3:].split('\n', 1)
		if language.rstrip() in ['python', 'py', 'javascript', 'js', 'ruby', 'rb']:
			return other_lines.split('```')[0].strip()

	# no newline characters or no language
	return args[3:].split('```')[0].strip()

def reply(cmd, output):
	split = output.split('\n', 10)
	output = '\n'.join(split[:10])
	output = output[:500]
	if len(split) == 11:
		output += '\n(too many output lines)'
	message = cmd.sender['pretty_name'] + ':'
	output = '```\n%s```' % output
	embed = {'description': output}
	cmd.reply(message, embed)
