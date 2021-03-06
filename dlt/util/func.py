
def applier(f):
    """Returns a function that applies `f` to a collection of inputs (or just one).

       Useful to use in conjuction with :func:`dlt.util.compose`
       
       Args:
            f (function): Function to be applied.

       Returns:
            callable: A function that applies 'f' to collections

       Example:
            >>> pow2 = dlt.util.applier(lambda x: x**2)
            >>> pow2(42)
            1764
            >>> pow2([1, 2, 3])
            [1, 4, 9]
            >>> pow2({'a': 1, 'b': 2, 'c': 3})
            {'a': 1, 'b': 4, 'c': 9}

    """
    def apply(objs):
        if isinstance(objs, dict):
            return {key: f(val)  for key, val in objs.items()}
        elif isinstance(objs, tuple):
            return tuple( f(x) for x in objs )
        elif isinstance(objs, list):
            return [f(x) for x in objs]
        else:
            return f(objs)
    return apply
