import functools
import operator

import numpy as np
import scipy.misc as spm


def prod(collection):
    """Product of all elements in the collection"""
    return functools.reduce(operator.mul, collection)


def game_size(n, s, exact=True):
    """Number of profiles in a symmetric game with n players and s strategies
    """
    if exact:
        return spm.comb(n+s-1, n, exact=True)
    else:
        return np.rint(spm.comb(n+s-1, n, exact=False)).astype(int)


def only(iterable):
    """Return the only element of an iterable

    Throws a value error if the iterable doesn't contain only one element
    """
    try:
        it = iter(iterable)
        value = next(it)
        try:
            next(it)
        except StopIteration:
            return value
        raise ValueError('Iterable had more than one element')
    except TypeError:
        raise ValueError('Input was not iterable')
    except StopIteration:
        raise ValueError('Input was empty')


def one_line(string, line_width=80):
    """If string s is longer than line width, cut it off and append "..."
    """
    string = string.replace('\n', ' ')
    if len(string) > line_width:
        return string[:3*line_width//4] + "..." + string[-line_width//4+3:]
    return string


# def weighted_least_squares(x, y, weights):
#     """appends the ones for you; puts 1D weights into a diagonal matrix"""
#     try:
#         A = np.append(x, np.ones([x.shape[0],1]), axis=1)
#         W = np.zeros([x.shape[0]]*2)
#         np.fill_diagonal(W, weights)
#         return y.T.dot(W).dot(A).dot(np.linalg.inv(A.T.dot(W).dot(A)))
#     except np.linalg.linalg.LinAlgError:
#         z = A.T.dot(W).dot(A)
#         for i in range(z.shape[0]):
#             for j in range(z.shape[1]):
#                 z[i,j] += np.random.uniform(-tiny,tiny)
#         return y.T.dot(W).dot(A).dot(np.linalg.inv(z))


def _reverse(seq, start, end):
    """Helper function needed for ordered_permutations"""
    end -= 1
    if end <= start:
        return
    while True:
        seq[start], seq[end] = seq[end], seq[start]
        if start == end or start+1 == end:
            return
        start += 1
        end -= 1


def compare_by_key(key):
    def decorator(cls):
        setattr(cls, '__eq__', lambda self, other: key(self) == key(other))
        setattr(cls, '__ne__', lambda self, other: key(self) != key(other))
        setattr(cls, '__le__', lambda self, other: key(self) <= key(other))
        setattr(cls, '__gw__', lambda self, other: key(self) >= key(other))
        setattr(cls, '__gt__', lambda self, other: key(self) > key(other))
        setattr(cls, '__lt__', lambda self, other: key(self) < key(other))
        return cls
    return decorator


def ordered_permutations(seq):
    """Return an iterable over all of the permutations in seq

    The elements of seq must be orderable. The permutations are taken relative
    to the value of the items in seq, not just their index. Thus:

    >>> list(ordered_permutations([1, 2, 1]))
    [(1, 1, 2), (1, 2, 1), (2, 1, 1)]

    This function is taken from this blog post:
    http://blog.bjrn.se/2008/04/lexicographic-permutations-using.html
    And this stack overflow post:
    https://stackoverflow.com/questions/6534430/why-does-pythons-itertools-permutations-contain-duplicates-when-the-original
    """
    seq = sorted(seq)
    if not seq:
        return
    first = 0
    last = len(seq)
    yield tuple(seq)
    if last == 1:
        return
    while True:
        next = last - 1
        while True:
            next1 = next
            next -= 1
            if seq[next] < seq[next1]:
                mid = last - 1
                while seq[next] >= seq[mid]:
                    mid -= 1
                seq[next], seq[mid] = seq[mid], seq[next]
                _reverse(seq, next1, last)
                yield tuple(seq)
                break
            if next == first:
                return


def acomb(n, k):
    """Compute an array of all n choose k options with repeats

    The result will be an array shape (m, n) where m is n choose k with
    repetitions. Each row is a unique way to allocate k ones to m bins.
    """
    # This uses dynamic programming to compute everything
    num = spm.comb(n, k, repetition=True, exact=True)
    grid = np.zeros((num, n), dtype=int)

    memoized = np.empty((n - 1, k), dtype=object)

    # TODO this recusrion breaks if asking for numbers that are too large, but
    # the order to fill n and k is predictable, it may be better to to use a
    # for loop.
    def fill_region(n, k, region):
        if n == 1:
            region[0, 0] = k
            return
        elif k == 0:
            region.fill(0)
            return
        saved = memoized[n - 2, k - 1]
        if saved is not None:
            np.copyto(region, saved)
            return
        memoized[n - 2, k - 1] = region
        o = 0
        for ki in range(k, -1, -1):
            n_ = n - 1
            k_ = k - ki
            m = spm.comb(n_, k_, repetition=True, exact=True)
            region[o:o+m, 0] = ki
            fill_region(n_, k_, region[o:o+m, 1:])
            o += m

    fill_region(n, k, grid)
    return grid


def acartesian2(*arrays):
    """Array cartesian product in 2d

    Produces a new ndarray that has the cartesian product of every row in the
    input arrays. The number of columns is the sum of the number of columns in
    each input. The number of rows is the product of the number of rows in each
    input.

    Arguments
    ---------
    *arrays : [ndarray (xi, s)]
    """
    rows = prod(a.shape[0] for a in arrays)
    columns = sum(a.shape[1] for a in arrays)
    dtype = arrays[0].dtype  # should always have at least one role
    assert all(a.dtype == dtype for a in arrays), \
        "all arrays must have the same dtype"

    result = np.zeros((rows, columns), dtype)
    pre_row = 1
    post_row = rows
    pre_column = 0
    for array in arrays:
        length, width = array.shape
        post_row /= length
        post_column = pre_column + width
        view = result[:, pre_column:post_column]
        view.shape = (pre_row, -1, post_row, width)
        np.copyto(view, array[:, None])
        pre_row *= length
        pre_column = post_column

    return result


def simplex_project(array):
    """Return the projection onto the simplex"""
    sort = -np.sort(-array)
    rho = (1 - sort.cumsum()) / np.arange(1, sort.size + 1)
    lam = rho[np.nonzero(rho + sort > 0)[0][-1]]
    return np.maximum(array + lam, 0)
