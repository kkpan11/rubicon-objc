from .types import NSUInteger, NSNotFound, NSRange, unichar
from .runtime import (
    NSArray, NSDictionary, NSMutableArray, NSMutableDictionary, NSString, ObjCInstance, for_objcclass, ns_from_py, objc_id,
    send_message
)


@for_objcclass(NSString)
class ObjCStrInstance(ObjCInstance):
    """Provides Pythonic operations on NSString objects that mimic those of Python's str.

    Note that str objects consist of Unicode code points, whereas NSString objects consist of UTF-16 code units.
    These are not equivalent for code points greater than U+FFFF. For performance and simplicity, ObjCStrInstance
    objects behave as sequences of UTF-16 code units, like NSString. (Individual UTF-16 code units are represented as
    Python str objects of length 1.) If you need to access or iterate over code points instead of UTF-16 code units,
    use str(nsstring) to convert the NSString to a Python str first.
    """

    def __str__(self):
        return self.UTF8String.decode('utf-8')

    def __eq__(self, other):
        if isinstance(other, str):
            return self.isEqualToString(ns_from_py(other))
        elif isinstance(other, NSString):
            return self.isEqualToString(other)
        else:
            return super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    # Note: We cannot define a __hash__ for NSString objects; doing so would violate the Python convention that
    # mutable objects should not be hashable. Although we could disallow hashing for NSMutableString objects, this
    # would make some immutable strings unhashable as well, because immutable strings can have a runtime class that
    # is a subclass of NSMutableString. This is not just a theoretical possibility - for example, on OS X 10.11,
    # isinstance(NSString.string(), NSMutableString) is true.

    def __len__(self):
        return self.length

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))

            if step == 1:
                return self.substringWithRange(NSRange(start, stop-start))
            else:
                rng = range(start, stop, step)
                chars = (unichar * len(rng))()
                for chars_i, self_i in enumerate(rng):
                    chars[chars_i] = ord(self[self_i])
                return NSString.stringWithCharacters(chars, length=len(chars))
        else:
            if key < 0:
                index = len(self) + key
            else:
                index = key

            if index not in range(len(self)):
                raise IndexError('{cls.__name__} index out of range'.format(cls=type(self)))

            return chr(self.characterAtIndex(index))


@for_objcclass(NSArray)
class ObjCListInstance(ObjCInstance):
    def __getitem__(self, item):
        if isinstance(item, slice):
            start, stop, step = item.indices(len(self))
            if step == 1:
                return self.subarrayWithRange(NSRange(start, stop-start))
            else:
                return ns_from_py([self.objectAtIndex(x) for x in range(start, stop, step)])
        else:
            if item < 0:
                index = len(self) + item
            else:
                index = item

            if index not in range(len(self)):
                raise IndexError('{cls.__name__} index out of range'.format(cls=type(self)))

            return self.objectAtIndex(index)

    def __len__(self):
        return send_message(self.ptr, 'count', restype=NSUInteger)

    def __iter__(self):
        for i in range(len(self)):
            yield self.objectAtIndex(i)

    def __contains__(self, item):
        return self.containsObject_(item)

    def __eq__(self, other):
        return list(self) == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def index(self, value):
        idx = self.indexOfObject_(value)
        if idx == NSNotFound:
            raise ValueError('%r is not in list' % value)
        return idx

    def count(self, value):
        return len([x for x in self if x == value])

    def copy(self):
        return ObjCInstance(send_message(self, 'copy', restype=objc_id))


@for_objcclass(NSMutableArray)
class ObjCMutableListInstance(ObjCListInstance):
    def __setitem__(self, item, value):
        if isinstance(item, slice):
            arr = ns_from_py(value)
            if not isinstance(arr, NSArray):
                raise TypeError(
                    '{cls.__module__}.{cls.__qualname__} is not convertible to NSArray'
                    .format(cls=type(value))
                )

            start, stop, step = item.indices(len(self))
            if step == 1:
                self.replaceObjectsInRange(NSRange(start, stop-start), withObjectsFromArray=arr)
            else:
                indices = range(start, stop, step)
                if len(arr) != len(indices):
                    raise ValueError(
                        'attempt to assign sequence of size {} to extended slice of size {}'
                        .format(len(value), len(indices))
                    )

                for idx, obj in zip(indices, arr):
                    self.replaceObjectAtIndex(idx, withObject=obj)
        else:
            if item < 0:
                index = len(self) + item
            else:
                index = item

            if index not in range(len(self)):
                raise IndexError('{cls.__name__} assignment index out of range'.format(cls=type(self)))

            self.replaceObjectAtIndex(index, withObject=value)

    def __delitem__(self, item):
        if isinstance(item, slice):
            start, stop, step = item.indices(len(self))
            if step == 1:
                self.removeObjectsInRange(NSRange(start, stop-start))
            else:
                for idx in sorted(range(start, stop, step), reverse=True):
                    self.removeObjectAtIndex(idx)
        else:
            if item < 0:
                index = len(self) + item
            else:
                index = item

            if index not in range(len(self)):
                raise IndexError('{cls.__name__} assignment index out of range'.format(cls=type(self)))

            self.removeObjectAtIndex_(index)

    def copy(self):
        return self.mutableCopy()

    def append(self, value):
        self.addObject_(value)

    def extend(self, values):
        for value in values:
            self.addObject_(value)

    def clear(self):
        self.removeAllObjects()

    def pop(self, item=-1):
        value = self[item]
        del self[item]
        return value

    def remove(self, value):
        del self[self.index(value)]

    def reverse(self):
        self.setArray(self.reverseObjectEnumerator().allObjects())

    def insert(self, idx, value):
        self.insertObject_atIndex_(value, idx)


@for_objcclass(NSDictionary)
class ObjCDictInstance(ObjCInstance):
    def __getitem__(self, item):
        v = self.objectForKey_(item)
        if v is None:
            raise KeyError(item)
        return v

    def __len__(self):
        return self.count

    def __iter__(self):
        for key in self.allKeys():
            yield key

    def __contains__(self, item):
        return self.objectForKey_(item) is not None

    def __eq__(self, other):
        return dict(self) == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def get(self, item, default=None):
        v = self.objectForKey_(item)
        if v is None:
            return default
        return v

    def keys(self):
        return self.allKeys()

    def values(self):
        return self.allValues()

    def items(self):
        for key in self.allKeys():
            yield key, self.objectForKey_(key)

    def copy(self):
        return ObjCInstance(send_message(self, 'copy', restype=objc_id))


@for_objcclass(NSMutableDictionary)
class ObjCMutableDictInstance(ObjCDictInstance):
    no_pop_default = object()

    def __setitem__(self, item, value):
        self.setObject_forKey_(value, item)

    def __delitem__(self, item):
        if item not in self:
            raise KeyError(item)

        self.removeObjectForKey_(item)

    def copy(self):
        return self.mutableCopy()

    def clear(self):
        self.removeAllObjects()

    def pop(self, item, default=no_pop_default):
        if item not in self:
            if default is not self.no_pop_default:
                return default
            else:
                raise KeyError(item)

        value = self.objectForKey_(item)
        self.removeObjectForKey_(item)
        return value

    def popitem(self):
        if len(self) == 0:
            raise KeyError("popitem(): {cls.__name__} is empty".format(cls=type(self)))

        key = self.allKeys().firstObject()
        value = self.objectForKey_(key)
        self.removeObjectForKey_(key)
        return (key, value)

    def setdefault(self, key, default=None):
        value = self.objectForKey_(key)
        if value is None:
            value = default
        if value is not None:
            self.setObject_forKey_(default, key)
        return value

    def update(self, new=None, **kwargs):
        if new is not None:
            kwargs.update(new)

        for k, v in kwargs.items():
            self.setObject_forKey_(v, k)
