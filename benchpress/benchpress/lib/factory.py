#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.


class BaseFactory(object):
    """Factory to construct instances of classes based on name.

    Attributes:
        base_class (class): base class that registered classes must subclass
    """

    def __init__(self, base_class):
        """Create a BaseFactory with base_class as the supertype."""
        self.base_class = base_class
        self.classes = {}

    @property
    def registered_names(self):
        """list of str: class names registered with the factory."""
        return list(self.classes.keys())

    def create(self, name):
        """Find the subclass with the correct name and instantiates it.

        Args:
            name (str): name of the item
        """
        if name not in self.classes:
            raise KeyError('No type "{}". '
                           'Did you forget to register() it?'.format(name))
        return self.classes[name]()

    def register(self, name, subclass):
        """Registers a class with the factory.

        Args:
            name (str): name of the class
            subclass (class): concrete subclass of base_class
        """
        assert issubclass(subclass, self.base_class)
        self.classes[name] = subclass
