#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from abc import ABCMeta, abstractmethod
import unittest

from benchpress.lib.factory import BaseFactory


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

    def setUp(self):
        self.factory = BaseFactory(Superclass)

    def test_register_nonsubclass(self):
        """Can't register a non-subclass"""
        # Dummy is not a subclass, so registering it should fail
        with self.assertRaises(AssertionError):
            class Dummy:
                pass
            self.factory.register('dummy', Dummy)

    def test_register(self):
        """Can register subclasses"""
        self.factory.register('subclass', Subclass1)
        self.factory.register('registered', RegisteredClass)

    def test_create_unregistered(self):
        """Can't create unregistered type"""
        with self.assertRaises(KeyError):
            self.factory.create('dummy')

    def test_create_registered(self):
        """Can create registered type"""
        self.factory.register('subclass', Subclass1)
        self.assertTrue(isinstance(self.factory.create('subclass'), Subclass1))

    def test_registered_names(self):
        """Can get list of registered classes"""
        self.assertListEqual([], self.factory.registered_names)
        self.factory.register('default', Subclass1)
        self.assertCountEqual(['default'], self.factory.registered_names)
        self.factory.register('subclass', Subclass1)
        self.assertCountEqual(['default', 'subclass'], self.factory.registered_names)


if __name__ == '__main__':
    unittest.main()
