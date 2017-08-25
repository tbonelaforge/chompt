import copy

import inspect

import pprint

PP = pprint.PrettyPrinter(indent=4)

class Chompt(object):
    def __init__(self):
        self.dynamic_attributes = {}
        self.value = None
        self.token = None
        self.storage = Storage()


    def __getattr__(self, item):
        value = self.__dict__.get(item, self.dynamic_attributes.get(item))
        return value


    def __deepcopy__(self, memo):
        memo[id(self)] = self
        copied = type(self)()
        copied.value = copy.deepcopy(self.value, memo)
        copied.token = copy.deepcopy(self.token, memo)
        copied.storage = copy.deepcopy(self.storage, memo)
        return copied


    def incorporate(self, client_object, field_name):
        self.dynamic_attributes[field_name] = Endpoint(client_object, self)


    def set_token(self, token_expr=None):
        token_value = self.value
        if token_expr is not None:
            token_value = self.storage.resolve(token_expr)
        self.token = token_value
        return self


    def get_token(self):
        return self.token


    def equals(self, expr):
        expected = self.storage.resolve(expr)
        assert self.value == expected, "Expected: %s, got: %s" % (str(expected), str(self.value))
        return self


    def json(self, *path):
        json_value = None
        if hasattr(self.value, 'json'):
            json_value = self.value.json()
            json_value = Storage.follow_path(json_value, path)
        self.value = json_value
        return self


    def store(self, key, expr=None):
        value = None
        if expr is None:
            value = self.value
        else:
            value = self.storage.resolve(expr)
        self.storage.store(key, value)
        return self

    def retrieve(self, *path):
        json_value = self.storage.retrieve(*path)
        self.value = json_value
        return self


    def debug(self):
        printable_value = {
            "value": self.value,
            "storage": self.storage.namespace,
            "storage": self.storage.namespace
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


    def contains_array(self, expected_array):
        if not isinstance(expected_array, list):
            raise AssertionError("The expected value was not an array")
        actual_array = self.value
        if not isinstance(actual_array, list):
            raise AssertionError("The actual value was not an array")
        for expected_element_expr in expected_array:
            expected_element_found = False
            for actual_element in actual_array:
                if self.contains(expected_element_expr, [], actual_element):
                    expected_element_found = True
                    break
            if not expected_element_found:
                raise AssertionError("Could not find element: " + str(expected_element_expr))
        return self


    def length(self, expr):
        expected = self.storage.resolve(expr)
        assert len(self.value) == expected, "Expected length of: %s, got length of: %s" % (str(expected), len(self.value))
        return self


class Endpoint(object):
    def __init__(self, client_object, context):
        self.context = context
        self.dynamic_attributes = {}
        self.original_client_object = client_object
        for name in dir(self.original_client_object):
            if callable(getattr(self.original_client_object, name)):
                fn = getattr(self.original_client_object, name)
                self.dynamic_attributes[name] = self.create_wrapped_function(name, fn)


    def create_wrapped_function(self, original_name, fn):
        def wrapped_function(*args, **kwargs):
            resolved_args = []
            resolved_kwargs = {}
            expected_status_code = 200
            for arg in args:
                resolved_args.append(self.context.storage.resolve(arg))
            for key, value in kwargs.items():
                if key == 'status_code':
                    expected_status_code = value
                else:
                    resolved_kwargs[key] = self.context.storage.resolve(value)
            self.add_token_if_expected(resolved_kwargs, fn)
            result = fn(*resolved_args, **resolved_kwargs)
            if hasattr(result, 'status_code'):
                assert result.status_code == expected_status_code, "Expected: %s, got: %s" % (
                    expected_status_code,
                    result.status_code
                )
            self.context.value = result
            return self.context
        return wrapped_function


    def add_token_if_expected(self, resolved_kwargs, fn):
        inspection_result = inspect.getargspec(fn)
        if 'token' in inspection_result.args:
            resolved_kwargs['token'] = self.context.get_token()


    def __getattr__(self, item):
        value = self.__dict__.get(item, self.dynamic_attributes.get(item))
        return value


    def __deepcopy__(self, memo):
        memo[id(self)] = self
        copied = Endpoint(self.original_client_object, self.context)
        return copied


class Storage():
    def __init__(self):
        self.namespace = {}


    def __str__(self):
        return pp.pformat(self.namespace)


    def __repr__(self):
        return str(self)


    def store(self, key, value):
        self.namespace[key] = value


    def retrieve(self, *path):
        return Storage.follow_path(self.namespace, path)


    def resolve_leaf(self, value_or_path):
        resolved_value = None
        try:
            path = value_or_path.get_path()
            resolved_value = Storage.follow_path(self.namespace, path)
        except AttributeError:
            resolved_value = value_or_path
        return resolved_value


    def resolve(self, expr):
        if Storage.is_leaf(expr):
            resolved = self.resolve_leaf(expr)
            return resolved
        if isinstance(expr, dict):
            for key in expr:
                resolved = self.resolve(expr[key])
                expr[key] = resolved
            return expr
        if isinstance(expr, list):
            for i, x in enumerate(expr):
                resolved = self.resolve(x)
                expr[i] = resolved
            return expr
        raise AssertionError("Expression to resolve was not JSON")


    @staticmethod
    def follow_path(json_object, path):
            for key in path:
                json_object = json_object[key]
            return copy.deepcopy(json_object)


    @staticmethod
    def is_leaf(expr):
        if isinstance(expr, dict):
            return False
        if isinstance(expr, list):
            return False
        return True


class Retrieve():
    def __init__(self, *path):
        self.path = path

    def get_path(self):
        return self.path


def equal_with_tolerance(actual, expected):
    return actual == expected


def check_status(response, status_code=200):
    assert response.status_code == status_code, "Expected: %s, got: %s" % (str(status_code), str(response.status_code))
    return response
