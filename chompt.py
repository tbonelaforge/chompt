class Chompt(object):
    def __init__(self):
        self.dynamic_attributes = {}
        self.value = None
        self.storage = Storage()


    def __getattr__(self, item):
        value = self.__dict__.get(item, self.dynamic_attributes.get(item))
        return value


    def incorporate(self, client_object, field_name):
        self.dynamic_attributes[field_name] = Endpoint(client_object, self)


    def json(self, *path):
        json_value = self.value.json()
        json_value = Storage.follow_path(json_value, path)
        self.value = json_value
        return self


    def debug(self):
        printable_value = {
            "value": self.value,
        }
        PP.pprint(printable_value)
        return self

    def contains(self, expr, path=None, value=None):
        if path is None:
            path = []
        if value is None:
            value = self.value
        if Storage.is_leaf(expr):
            expected = self.storage.resolve_leaf(expr)
            try:
                actual = Storage.follow_path(value, path)
            except KeyError:
                raise AssertionError("Test value does not contain path: {}".format(path))
            assert equal_with_tolerance(actual, expected),\
                "Expected: {} at {}, got: {}".format(str(expected), str(path), str(actual))
            return self
        if isinstance(expr, dict):
            for key in expr:
                self.contains(expr[key], path + [key], value)
            return self
        if isinstance(expr, list):
            for i, x in enumerate(expr):
                self.contains(x, path + [i], value)
            return self
        raise AssertionError("Expression given to contains was not JSON")
