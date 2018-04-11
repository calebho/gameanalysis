"""Module for generating action graph games"""
import numpy as np

from gameanalysis import aggfn
from gameanalysis import rsgame
from gameanalysis import utils


# FIXME Move this into gamegen?

def _random_inputs(prob, num_strats, num_funcs):
    """Returns a random mask without all true or all false per function"""
    vals = np.random.random((num_strats, num_funcs))
    mask = vals < prob
    inds = np.arange(num_funcs)
    mask[vals.argmin(0), inds] = True
    mask[vals.argmax(0), inds] = False
    return mask


def _random_mask(prob, num_funcs, num_strats):
    """Returns a random mask with at least one true in every row and col"""
    vals = np.random.random((num_funcs, num_strats))
    mask = vals < prob
    mask[np.arange(num_funcs), vals.argmin(1)] = True
    mask[vals.argmin(0), np.arange(num_strats)] = True
    return mask


def _random_weights(prob, num_funcs, num_strats):
    """Returns random action weights"""
    return (_random_mask(prob, num_funcs, num_strats) *
            np.random.normal(0, 1, (num_funcs, num_strats)))


def normal_aggfn(role_players, role_strats, functions, *, input_prob=0.2,
                 weight_prob=0.2):
    """Generate a random normal AgfnGame

    Each function value is an i.i.d Gaussian random walk.

    Parameters
    ----------
    role_players : int or ndarray
        The number of players per role.
    role_strats : int or ndarray
        The number of strategies per role.
    functions : int
        The number of functions to generate.
    input_prob : float, optional
        The probability of a strategy counting towards a function value.
    weight_prob : float, optional
        The probability of a function producing non-zero payoffs to a strategy.
    """
    base = rsgame.emptygame(role_players, role_strats)
    inputs = _random_inputs(input_prob, base.num_strats, functions)
    weights = _random_weights(weight_prob, functions, base.num_strats)

    shape = (functions,) + tuple(base.num_role_players + 1)
    funcs = np.random.normal(0, 1 / np.sqrt(base.num_players + 1), shape)
    for role in range(1, base.num_roles + 1):
        funcs.cumsum(role, out=funcs)
    mean = funcs.mean(tuple(range(1, base.num_roles + 1)))
    mean.shape = (functions,) + (1,) * base.num_roles
    funcs -= mean
    return aggfn.aggfn_replace(base, weights, inputs, funcs)


def _random_aggfn( # pylint: disable=too-many-arguments
        role_players, role_strats, functions, input_prob, weight_prob,
        role_dist):
    """Base form for structured random aggfn generation

    role_dist takes a number of functions and a number of players and returns
    an ndarray of the function values.
    """
    base = rsgame.emptygame(role_players, role_strats)
    inputs = _random_inputs(input_prob, base.num_strats, functions)
    weights = _random_weights(weight_prob, functions, base.num_strats)

    funcs = np.ones((functions,) + tuple(base.num_role_players + 1))
    base_shape = [functions] + [1] * base.num_roles
    for role, play in enumerate(base.num_role_players):
        role_funcs = role_dist(functions, play)
        shape = base_shape.copy()
        shape[role + 1] = play + 1
        role_funcs.shape = shape
        funcs *= role_funcs
    return aggfn.aggfn_replace(base, weights, inputs, funcs)


def poly_aggfn(
        role_players, role_strats, functions, *, input_prob=0.2,
        weight_prob=0.2, degree=4):
    """Generate a random polynomial AgfnGame

    Functions are generated by generating `degree` zeros in [0, num_players] to
    serve as a polynomial functions.

    Parameters
    ----------
    role_players : int or ndarray
        The number of players per role.
    role_strats : int or ndarray
        The number of strategies per role.
    functions : int
        The number of functions to generate.
    input_prob : float, optional
        The probability of a strategy counting towards a function value.
    weight_prob : float, optional
        The probability of a function producing non-zero payoffs to a strategy.
    degree : int or [float], optional
        Either an integer specifying the degree or a list of the probabilities
        of degrees starting from one, e.g. 3 is the same as [0, 0, 1].
    """
    if isinstance(degree, int):
        degree = (0,) * (degree - 1) + (1,)
    max_degree = len(degree)

    def role_dist(functions, play):
        """Role distribution"""
        zeros = (np.random.random((functions, max_degree)) * 1.5 - 0.25) * play
        terms = np.arange(play + 1)[:, None] - zeros[:, None]
        choices = np.random.choice(
            max_degree, (functions, play + 1), True, degree)
        terms[choices[..., None] < np.arange(max_degree)] = 1
        poly = terms.prod(2) / play ** choices

        # The prevents too many small polynomials from making functions
        # effectively constant
        scale = poly.max() - poly.min()
        offset = poly.min() + 1
        return (poly - offset) / (1 if np.isclose(scale, 0) else scale)

    return _random_aggfn(role_players, role_strats, functions, input_prob,
                         weight_prob, role_dist)


def sine_aggfn(role_players, role_strats, functions, *, input_prob=0.2,
               weight_prob=0.2, period=4):
    """Generate a random sinusodial AgfnGame

    Functions are generated by generating sinusoids with uniform random shifts
    and n periods in 0 to num_players, where n is chosen randomle between
    min_period and max_period.

    Parameters
    ----------
    role_players : int or ndarray
        The number of players per role.
    role_strats : int or ndarray
        The number of strategies per role.
    functions : int
        The number of functions to generate.
    input_prob : float, optional
        The probability of a strategy counting towards a function value.
    weight_prob : float, optional
        The probability of a function producing non-zero payoffs to a strategy.
    period : float, optional
        The loose number of periods in the payoff for each function.
    """
    def role_dist(functions, play):
        """Distribution by role"""
        # This setup makes it so that the beat frequencies approach period
        periods = ((np.arange(1, functions + 1) +
                    np.random.random(functions) / 2 - 1 / 4) *
                   period / functions)
        offset = np.random.random((functions, 1))
        return np.sin(
            (np.linspace(0, 1, play + 1) * periods[:, None] + offset) * 2 *
            np.pi)

    return _random_aggfn(role_players, role_strats, functions, input_prob,
                         weight_prob, role_dist)


def _random_monotone_polynomial(functions, players, degree):
    """Generates a random monotone polynomial table"""
    coefs = (np.random.random((functions, degree + 1)) /
             players ** np.arange(degree + 1))
    powers = np.arange(players + 1) ** np.arange(degree + 1)[:, None]
    return coefs.dot(powers)


def congestion(num_players, num_facilities, num_required, *, degree=2):
    """Generate a congestion game

    A congestion game is a symmetric game, where there are a given number of
    facilities, and each player must choose to use some amount of them. The
    payoff for each facility decreases as more players use it, and a players
    utility is the sum of the utilities for every facility.

    In this formulation, facility payoffs are random polynomials of the number
    of people using said facility.

    Parameters
    ----------
    num_players : int > 1
        The number of players.
    num_facilities : int > 1
        The number of facilities.
    num_required : 0 < int < num_facilities
        The number of required facilities.
    degree : int > 0, optional
        Degree of payoff polynomials.
    """
    utils.check(num_players > 1, 'must have more than one player')
    utils.check(num_facilities > 1, 'must have more than one facility')
    utils.check(
        0 < num_required < num_facilities,
        'must require more than zero but less than num_facilities')
    utils.check(degree > 0, 'degree must be greater than zero')

    function_inputs = utils.acomb(num_facilities, num_required)
    functions = -_random_monotone_polynomial(num_facilities, num_players,
                                             degree)

    facs = tuple(utils.prefix_strings('', num_facilities))
    strats = tuple('_'.join(facs[i] for i, m in enumerate(mask) if m)
                   for mask in function_inputs)
    return aggfn.aggfn_names(
        ['all'], num_players, [strats], function_inputs.T, function_inputs,
        functions)


def local_effect(num_players, num_strategies, *, edge_prob=0.2):
    """Generate a local effect game

    In a local effect game, strategies are connected by a graph, and utilities
    are a function of the number of players playing our strategy and the number
    of players playing a neighboring strategy, hence local effect.

    In this formulation, payoffs for others playing our strategy are negative
    quadratics, and payoffs for playing other strategies are positive cubics.

    Parameters
    ----------
    num_players : int > 1
        The number of players.
    num_strategies : int > 1
        The number of strategies.
    edge_prob : float, optional
        The probability that one strategy affects another.
    """
    utils.check(num_players > 1, "can't generate a single player game")
    utils.check(num_strategies > 1, "can't generate a single strategy game")

    local_effect_graph = np.random.rand(
        num_strategies, num_strategies) < edge_prob
    np.fill_diagonal(local_effect_graph, False)
    num_neighbors = local_effect_graph.sum()
    num_functions = num_neighbors + num_strategies

    action_weights = np.eye(num_functions, num_strategies, dtype=float)
    function_inputs = np.eye(num_strategies, num_functions, dtype=bool)
    in_act, out_act = local_effect_graph.nonzero()
    func_inds = np.arange(num_strategies, num_functions)
    function_inputs[in_act, func_inds] = True
    action_weights[func_inds, out_act] = 1

    function_table = np.empty((num_functions, num_players + 1), float)
    function_table[:num_strategies] = -_random_monotone_polynomial(
        num_strategies, num_players, 2)
    function_table[num_strategies:] = _random_monotone_polynomial(
        num_neighbors, num_players, 3)
    return aggfn.aggfn(num_players, num_strategies, action_weights,
                       function_inputs, function_table)
