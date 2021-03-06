#!/usr/bin/python

# resultSet.py - A Result Set for use the the Python DB API 2
# Copyright 2004 Jack Neely
# Written by Jack Neely <jjneely@pams.ncsu.edu>
#
# SDG
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# A fancy zip() replacement that's way cool.  Stolen from Andrae Muys
# This is good for large memory rows

# We now require python 2.3, lets not be silly here.

def xzip(*args):
    iters = [iter(a) for a in args]
    while True:
        yield tuple([i.next() for i in iters])


class resultSet(dict):

    def __init__(self, cursor):
        # cursor is a Python DB API 2.0 compilant cursor
        # Do setup to map dicts and lists from fetch* to an object API

        self.cursor = cursor
        self._desc = self.cursor.description
        
        # Inital fetch and row population
        self.nextRow()

        # For the iterator, we need to know if this is the inital
        # creation/data row.  
        self._flag = 1


    def __iter__(self):
        # This is so we can directly interate over resultSet
        # Example: for row in resultSet(cursor):
        
        return self


    def __getitem__(self, key):
        if self._row == None:
            # We are out of rows...bail
            raise IndexError("Result set empty.")

        return dict.__getitem__(self, key)


    def __setitem__(self, key, value):
        raise TypeError


    def __delitem__(self, key):
        raise TypeError


    def nextRow(self):
        # For manual interation, this method will cause resultSet to
        # parse the next row.

        self._row = self.cursor.fetchone()

        if self._row == None:
            self.clear()
        else:
            # Load data from new row into dict
            for desc, element in xzip(self._desc, self._row):
                # Make sure desc is NOT of form 'table.field'
                field = desc[0].split(".")[-1]
                dict.__setitem__(self, field, element)


    def next(self):
        # There's a little trickery here because on creation we
        # suck in the first row of data so the user can do normal access
        
        if self._flag:
            # We are still dealing with the inital first row that's
            # already loaded.  Don't load new data, return self
            self._flag = 0
        else:
            # Get new data then return
            self.nextRow()

        if self._row == None:
            # Result set is now empty
            raise StopIteration
        
        return self
        

    def rowcount(self):
        return self.cursor.rowcount


    def dump(self):
        """Deep copy.  Return a list of dicts instead of a resultset.
           This has the side effect of sucking everything in to python's
           memory that was returned in this result set."""

        ret = []
        for row in self:
            ret.append(row.copy())

        return ret

