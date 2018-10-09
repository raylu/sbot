import ast
import sys

code = sys.stdin.read()
node = ast.parse(code)
last_node = node.body[-1]
if isinstance(last_node, ast.Expr):
	if not isinstance(last_node.value, ast.Call) or last_node.value.func.id != 'print':
		print_expr = ast.Expr(value=ast.Call(func=ast.Name(id='print', ctx=ast.Load()),
			args=[last_node.value], keywords=[ast.keyword(arg='end', value=ast.Str(s=''))]))
		node.body[-1] = print_expr
		ast.fix_missing_locations(node)
exec(compile(node, '<sbot>', 'exec'))
