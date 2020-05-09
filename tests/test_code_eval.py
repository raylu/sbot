import code_eval

import unittest

unittest.TestCase.assert_equal = unittest.TestCase.assertEqual

class TestCodeEval(unittest.TestCase):
	def test_prep_input(self):
		self.assert_equal(code_eval.prep_input('1+2*3/4'), '1+2*3/4')
		self.assert_equal(code_eval.prep_input('`1+2`'), '1+2')
		self.assert_equal(code_eval.prep_input('```3/4```'), '3/4')
		self.assert_equal(code_eval.prep_input('```\n1+2\n3/4\n```'), '1+2\n3/4')
		self.assert_equal(code_eval.prep_input('```1+2\n3/4\n```'), '1+2\n3/4')
		self.assert_equal(code_eval.prep_input('```py\n1+2\n3/4\n```'), '1+2\n3/4\n')
		self.assert_equal(code_eval.prep_input('```\n1+2'), '1+2')
