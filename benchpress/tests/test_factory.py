#!/usr/bin/env python3

from abc import ABCMeta, abstractmethod
import unittest

from lib.factory import BaseFactory


# Class hierarchy that is used for testing the factory
class Superclass(object, metaclass=ABCMeta):
    @abstractmethod
    def abstract(self):
        pass


class Subclass1(Superclass):
    def abstract(self):
        pass


class RegisteredClass(object):
    def abstract(self):
        pass


Superclass.register(RegisteredClass)
# End test classes


class TestBaseFactory(unittest.TestCase):

    def test_register(self):
        factory = BaseFactory(Superclass)

        # Dummy is not a subclass, so registering it should fail
        with self.assertRaises(AssertionError):
            class Dummy:
                pass
            factory.register('dummy', Dummy)

        # make sure that registering the actual subclass does not fail
        factory.register('subclass', Subclass1)

        # registering a registered abc subclass should also work
        factory.register('registered', RegisteredClass)

    def test_create(self):
        factory = BaseFactory(Superclass)

        # requesting create for a type that hasn't been registered should fail
        with self.assertRaises(KeyError):
            factory.create('dummy')

        # should create an actual instance
        factory.register('subclass', Subclass1)
        self.assertTrue(isinstance(factory.create('subclass'), Subclass1))


if __name__ == '__main__':
    unittest.main()
