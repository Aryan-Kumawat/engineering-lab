import unittest
from tasktree import Runner,EXAMPLE
class Tests(unittest.TestCase):
 def test_retry(self):
  events=list(Runner(EXAMPLE).events());self.assertEqual(events[-1]['status'],'SUCCESS');self.assertTrue(any(e['status']=='FAILURE' for e in events));self.assertFalse(events[-1]['blackboard']['grasped'])
 def test_cancel(self):
  r=Runner(EXAMPLE);events=r.events();next(events);r.cancel();self.assertEqual(list(events)[-1]['status'],'CANCELLED')
 def test_fallback(self):
  tree={'type':'Fallback','name':'f','children':[{'type':'Action','name':'bad','fail_first':5},{'type':'Action','name':'good'}]};self.assertEqual(list(Runner(tree).events())[-1]['status'],'SUCCESS')
 def test_reproducible(self):self.assertEqual(list(Runner(EXAMPLE).events()),list(Runner(EXAMPLE).events()))
if __name__=='__main__':unittest.main()
