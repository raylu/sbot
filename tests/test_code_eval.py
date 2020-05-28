import unittest

import code_eval

unittest.TestCase.assert_equal = unittest.TestCase.assertEqual

class TestCodeEval(unittest.TestCase):
	def test_prep_input(self):
		# basic inputs
		self.assert_equal(code_eval.prep_input('1+2*3/4'), '1+2*3/4')

		# code inputs
		self.assert_equal(code_eval.prep_input('`1+2`'), '1+2')
		self.assert_equal(code_eval.prep_input('```3/4```'), '3/4')
		self.assert_equal(code_eval.prep_input('```\n1+2\n3/4\n```'), '1+2\n3/4')
		self.assert_equal(code_eval.prep_input('```1+2\n3/4\n```'), '1+2\n3/4')
		self.assert_equal(code_eval.prep_input('```py\n1+2\n3/4\n```'), '1+2\n3/4')
		self.assert_equal(code_eval.prep_input('```\n1+2'), '1+2')

		# code inputs with ping
		self.assert_equal(code_eval.prep_input('```3/4``` @name#123'), '3/4')
		self.assert_equal(code_eval.prep_input('```py 3/4``` @name#123'), 'py 3/4')
		self.assert_equal(code_eval.prep_input('```py\n3/4``` @name#123'), '3/4')
		self.assert_equal(code_eval.prep_input('```py\n3/4```\n@name#123'), '3/4')

		# invalid code input
		self.assert_equal(code_eval.prep_input('`1+2` @name#123'), '1+2` @name#123')
		self.assert_equal(code_eval.prep_input('```\n1+2```\n2+3'), '1+2')
		self.assert_equal(code_eval.prep_input('```\n1+2```\n2+3\n``` @name#123'), '1+2')
		self.assert_equal(code_eval.prep_input('```\n1+2```\n```\n@name#123'), '1+2')
