CHOMPT
======

Chainable Object Methods for Python Testing is a package for constructing tests by chaining HTTP requests,
and storing/referencing the results.

----

Example Usage::

  from chompt import Chompt

  class ExampleClient(object):
      def __init__(self):
          self.prefix = 'correct'


      def fetch(self):
          return self.prefix + ' result'


  class ExampleTest(Chompt):
      def __init__(self):
          super(ExampleTest, self).__init__()
          self.incorporate(ExampleClient(), 'example_client')


  def test_example():
      test = ExampleTest().example_client.fetch().equals('correct result')
      return test


  if __name__ == "__main__":
      print("About to run test...")
      test_object = test_example()
      print("The test passed! the test_object looks like:")
      test_object.debug()
