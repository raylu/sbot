def command(description, *options):
	def wrapped(f):
		f.description = description
		f.options = options
		return f
	return wrapped

# https://discord.com/developers/docs/interactions/slash-commands#application-command-object-application-command-option-type
class OPTION_TYPE:
	SUB_COMMAND       = 1
	SUB_COMMAND_GROUP = 2
	STRING            = 3
	INTEGER           = 4
	BOOLEAN           = 5
	USER              = 6
	CHANNEL           = 7
	ROLE              = 8
	MENTIONABLE       = 9
	NUMBER            = 10
