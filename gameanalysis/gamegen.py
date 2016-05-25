import collections
import itertools
import random
from collections import abc
from os import path

import numpy as np
import numpy.random as rand
import scipy.misc as scm

from gameanalysis import collect
from gameanalysis import rsgame
from gameanalysis import utils


# Populate word list for generating better names
_WORD_LIST_FILE = path.join(path.dirname(path.dirname(__file__)),
                            '.wordlist.txt')
_WORD_LIST = []

try:
    with open(_WORD_LIST_FILE) as f:
        for word in f:
            _WORD_LIST.append(word[:-1])
except OSError:  # Something bad happened
    pass

default_distribution = lambda shape=None: rand.uniform(-1, 1, shape)


def _as_list(item, length):
    """Makes sure item is a length list"""
    if isinstance(item, abc.Sequence):
        assert len(item) == length, "List was not the proper length"
    else:
        item = [item] * length
    return item


def _random_strings(number, prefix='x', padding=None, cool=False):
    """Generate random strings without repetition

    Parameters
    ----------
    prefix : str
        The prefix to put before the numbers.
    padding : int
        The amount to pad numbers so that the lexicographically sort. If None,
        they are padded to fit all of the numbers.
    cool : bool
        If true, numbers and prefixes are omitted, and instead words are
        sampled from a list of dictionary words read in.
    """
    if cool and _WORD_LIST:
        return random.sample(_WORD_LIST, number)
    else:
        if padding is None:
            padding = len(str(number - 1))
        return ('{}{:0{}d}'.format(prefix, i, padding) for i in range(number))


def _compact_payoffs(game):
    """Given a game returns a compact representation of the payoffs

    In this case compact means that they're in one ndarray. This representation
    is inefficient for almost everything but an independent game with full
    data.

    Parameters
    ----------
    game : rsgame.Game
        The game to generate a compact payoff matrix for

    Returns
    -------
    payoffs : ndarray; shape (s1, s2, ..., sn, n)
        payoffs[s1, s2, ..., sn, j] is the payoff to player j when player 1
        plays s1, player 2 plays s2, etc. n is the total number of players.

    strategies : [(role, [strat])]
        The first list indexes the players, and the second indexes the
        strategies for that player.
    """
    # TODO could probably be done better with array profiles, but it's unclear.
    # np.lexsort(-profs.T[::-1]) will get the proper ordering of the profiles
    # for assignment into a matrix. However, the expansion from one array
    # profile to all expanded profiles is not easy, and maybe not worth
    # constructing?
    strategies = list(itertools.chain.from_iterable(
        itertools.repeat((role, list(strats)), game.players[role])
        for role, strats in game.strategies.items()))

    payoffs = np.empty([len(s) for _, s in strategies] + [len(strategies)])
    for profile, payoff in game.profile_payoffs(as_array=True):
        # This generator expression takes a role symmetric profile with payoffs
        # and generates tuples of strategy indexes and payoffs for every player
        # when that player plays the given strategy.

        # The first line takes results in the form:
        # (((r1i1, r1p1), (r1i2, r1p2)), ((r1i1, r2p1),)) that is grouped by
        # role, then by player in the role, then grouped strategy index and
        # payoff, and turns it into a single tuple of indices and payoffs.
        perms = (zip(*itertools.chain.from_iterable(sp))
                 # This product is over roles
                 for sp in itertools.product(*[
                     # This computes all of the ordered permutations of
                     # strategies in a given role, e.g. if two players play s1
                     # and one plays s2, this iterates over all possible ways
                     # that could be expressed in an asymmetric game.
                     utils.ordered_permutations(itertools.chain.from_iterable(
                         # This iterates over the strategy counts, and
                         # duplicates strategy indices and payoffs based on the
                         # strategy counts.
                         itertools.repeat((i, v), c) for i, (c, v)
                         in enumerate(zip(p, pay))))
                     for p, pay in zip(game.role_split(profile),
                                       game.role_split(payoff))]))
        for indices, utilities in perms:
            payoffs[indices] = utilities
    return payoffs, strategies


def drop_profiles(game, prob: float, independent=True):
    if independent:
        selection = rand.random(len(game)) < prob
    else:
        selection = rand.choice(np.arange(len(game)), round(len(game) * prob),
                                replace=False)

    new_profiles = game.profiles(as_array=True)[selection]
    new_payoffs = game.payoffs(as_array=True)[selection]
    return rsgame.Game(game.players, game.strategies, new_profiles,
                       new_payoffs)


def empty_role_symmetric_game(num_roles: int, num_players, num_strategies,
                              cool=False):
    """Create an empty role symmetric game"""
    assert num_roles > 0, "Number of roles must be greater than 0"
    num_players = _as_list(num_players, num_roles)
    num_strategies = _as_list(num_strategies, num_roles)

    assert all(p > 0 for p in num_players), \
        "number of players must be greater than zero"
    assert all(s > 0 for s in num_strategies), \
        "number of strategies must be greater than zero"

    # This list is necessary to maintain consistent order.
    roles = list(_random_strings(num_roles, prefix='r', cool=cool))
    strategies = collections.OrderedDict(
        (role, list(_random_strings(num_strat, prefix='s', cool=cool)))
        for role, num_strat
        in zip(roles, num_strategies))
    players = dict(zip(roles, num_players))
    return rsgame.EmptyGame(players, strategies)


def role_symmetric_game(num_roles, num_players, num_strategies,
                        distribution=default_distribution, cool=False):
    """Generate a random role symmetric game

    Parameters
    ----------
    num_roles : int > 0
        The number of roles in the game.
    num_players : int or [int], len == num_roles
        The number of players, same for each role if a scalar, or a list, one
        for each role.
    num_strategies : int or [int], len == num_roles
        The number of strategies, same for each role if a scalar, or a list,
        one for each role.
    distribution : () -> float
        Payoff distribution. Calling should result in a scalar payoff.
        (default: default_distribution)
    cool : bool
        Whether to generate word-like role and strategy strings. These will be
        random, and hence unpredictable, whereas standard role and strategy
        names are predictable. (default: False)
    """
    game = empty_role_symmetric_game(num_roles, num_players, num_strategies,
                                     cool)
    aprofiles = game.all_profiles(as_array=True)
    mask = aprofiles > 0
    apayoffs = np.zeros(aprofiles.shape)
    apayoffs[mask] = distribution(mask.sum())

    return rsgame.Game(game.players, game.strategies, aprofiles, apayoffs)


def independent_game(num_players, num_strategies,
                     distribution=default_distribution, cool=False):
    """Generate a random independent (asymmetric) game

    All payoffs are generated independently from distribution.

    Parameters
    ----------
    num_players : int > 0
        The number of players.
    num_strategies : int or [int], len == num_players
        The number of strategies for each player. If an int, then every player
        has the same number of strategies.
    distribution : (shape) -> ndarray (shape)
        The distribution to sample payoffs from. Must take a single shape
        argument and return an ndarray of iid values with that shape.
    """
    # Correct inputs
    num_strategies = _as_list(num_strategies, num_players)
    shape = num_strategies + [num_players]

    # Generate names
    roles = _random_strings(num_players, prefix='r', cool=cool)
    strategies = collect.fodict(
        (role, tuple(_random_strings(num_strat, prefix='s', cool=cool)))
        for role, num_strat
        in zip(roles, shape))

    return rsgame.Game.from_matrix(strategies, distribution(shape))


def symmetric_game(num_players, num_strategies,
                   distribution=default_distribution, cool=False):
    """Generate a random symmetric game"""
    return role_symmetric_game(1, num_players, num_strategies, distribution,
                               cool)


def covariant_game(num_players, num_strategies, mean_dist=lambda shape:
                   np.zeros(shape), var_dist=lambda shape: np.ones(shape),
                   covar_dist=default_distribution, cool=False):
    """Generate a covariant game

    Covariant games are asymmetric games where payoff values for each profile
    drawn according to multivariate normal.

    The multivariate normal for each profile has a constant mean drawn from
    `mean_dist`, constant variance drawn from`var_dist`, and constant
    covariance drawn from `covar_dist`.

    Parameters
    ----------
    mean_dist : (shape) -> ndarray (shape)
        Distribution from which mean payoff for each profile is drawn.
        (default: lambda: 0)
    var_dist : (shape) -> ndarray (shape)
        Distribution from which payoff variance for each profile is drawn.
        (default: lambda: 1)
    covar_dist : (shape) -> ndarray (shape)
        Distribution from which the value of the off-diagonal covariance matrix
        entries for each profile is drawn. (default: uniform [-1, 1])
    """
    # Create sampling distributions and sample from them
    num_strategies = _as_list(num_strategies, num_players)
    shape = num_strategies + [num_players]
    var = covar_dist(shape + [num_players])
    diag = var.diagonal(0, num_players, num_players + 1)
    diag.setflags(write=True)  # Hack
    np.copyto(diag, var_dist(shape))

    # The next couple of lines do multivariate Gaussian sampling for all
    # payoffs simultaneously
    u, s, v = np.linalg.svd(var)
    payoffs = rand.normal(size=shape)
    payoffs = (payoffs[..., None] * (np.sqrt(s)[..., None] * v)).sum(-2)
    payoffs += mean_dist(shape)

    # Generate names
    roles = _random_strings(num_players, prefix='r', cool=cool)
    strategies = collect.fodict(
        (role, tuple(_random_strings(num_strat, prefix='s', cool=cool)))
        for role, num_strat
        in zip(roles, num_strategies))

    return rsgame.Game.from_matrix(strategies, payoffs)


def zero_sum_game(num_strategies, distribution=default_distribution,
                  cool=False):
    """Generate a two-player, zero-sum game"""
    # Generate player 1 payoffs
    num_strategies = _as_list(num_strategies, 2)
    p1_payoffs = distribution(num_strategies)

    # Generate names
    roles = _random_strings(2, prefix='r', cool=cool)
    strategies = collect.fodict(
        (role, tuple(_random_strings(num_strat, prefix='s', cool=cool)))
        for role, num_strat
        in zip(roles, num_strategies))

    return rsgame.Game.from_matrix(strategies,
                                   np.dstack([p1_payoffs, -p1_payoffs]))


def sym_2p2s_game(a=0, b=1, c=2, d=3, distribution=default_distribution,
                  cool=False):
    """Create a symmetric 2-player 2-strategy game of the specified form.

    Four payoff values get drawn from U(min_val, max_val), and then are
    assigned to profiles in order from smallest to largest according to the
    order parameters as follows:

       | s0  | s1  |
    ---|-----|-----|
    s0 | a,a | b,c |
    s1 | c,b | d,d |
    ---|-----|-----|

    So a=2,b=0,c=3,d=1 gives a prisoners' dilemma; a=0,b=3,c=1,d=2 gives a game
    of chicken.

    distribution must accept a size parameter a la numpy distributions."""
    # Generate payoffs
    payoffs = distribution(4)
    payoffs.sort()
    counts = np.array([[2, 0],
                       [1, 1],
                       [0, 2]])
    values = np.array([[payoffs[a], 0],
                       [payoffs[b], payoffs[c]],
                       [0, payoffs[d]]])

    # Generate names
    role = next(_random_strings(1, prefix='r', cool=cool))
    strategies = list(_random_strings(2, prefix='s', cool=cool))

    return rsgame.Game({role: 2}, {role: strategies}, counts, values)


def sym_2p2s_known_eq(eq_prob, cool=False):
    """Generate a symmetric 2-player 2-strategy game

    This game has a single mixed equilibrium where strategy one is played with
    probability eq_prob.
    """
    profiles = np.array([[2, 0],
                         [1, 1],
                         [0, 2]])
    payoffs = np.array([[0, 0],
                        [eq_prob, 1 - eq_prob],
                        [0, 0]])

    # Generate names
    role = next(_random_strings(1, prefix='r', cool=cool))
    strategies = list(_random_strings(2, prefix='s', cool=cool))

    return rsgame.Game({role: 2}, {role: strategies}, profiles, payoffs)


def congestion_game(num_players, num_facilities, num_required, cool=False):
    """Generates a random congestion game with num_players players and nCr(f, r)
    strategies

    Congestion games are symmetric, so all players belong to one role. Each
    strategy is a subset of size #required among the size #facilities set of
    available facilities. Payoffs for each strategy are summed over facilities.
    Each facility's payoff consists of three components:

    -constant ~ U[0, num_facilities]
    -linear congestion cost ~ U[-num_required, 0]
    -quadratic congestion cost ~ U[-1, 0]
    """
    # Generate strategies mask
    strat_list = list(itertools.combinations(range(num_facilities),
                                             num_required))
    num_strats = len(strat_list)
    num_strats = scm.comb(num_facilities, num_required, exact=True)
    strat_mask = np.zeros([num_strats, num_facilities], dtype=bool)
    inds = np.fromiter(
        itertools.chain.from_iterable(
            (row * num_facilities + f for f in facs) for row, facs
            in enumerate(strat_list)),
        int, num_strats * num_required)
    strat_mask.ravel()[inds] = True

    # Generate value for congestions
    values = rand.random((num_facilities, 3))
    values[:, 0] *= num_facilities  # constant
    values[:, 1] *= -num_required   # linear
    values[:, 2] *= -1              # quadratic

    # Compute array version of all payoffs
    counts = (empty_role_symmetric_game(1, num_players, num_strats)
              .all_profiles(as_array=True))

    # Compute usage of every facility and then payoff
    strat_usage = counts[..., None] * strat_mask
    usage = strat_usage.sum(1)
    fac_payoffs = (usage[..., None] ** np.arange(3) * values).sum(2)
    payoffs = (strat_usage * fac_payoffs[:, None, :]).sum(2)

    # Generate names for everything
    role = next(_random_strings(num_strats, cool=cool)) if cool else 'all'
    strategies = (list(_random_strings(num_strats, cool=cool)) if cool
                  else ['_'.join(str(s) for s in strat)
                        for strat in strat_list])

    return rsgame.Game({role: num_players}, {role: strategies}, counts,
                       payoffs)


def local_effect_game(num_players, num_strategies, cool=False):
    """Generates random congestion games with num_players (N) players and
    num_strategies (S) strategies.

    Local effect games are symmetric, so all players belong to one role. Each
    strategy corresponds to a node in the G(N, 2/S) (directed edros-renyi
    random graph with edge probability of 2/S) local effect graph. Payoffs for
    each strategy consist of constant terms for each strategy, and interaction
    terms for the number of players choosing that strategy and each neighboring
    strategy.

    The one-strategy terms are drawn as follows:
    -constant ~ U[-(N+S), N+S]
    -linear ~ U[-N, 0]

    The neighbor strategy terms are drawn as follows:
    -linear ~ U[-S, S]
    -quadratic ~ U[-1, 1]

    """
    # Generate local effects graph. This is an SxSx3 graph where the first two
    # axis are in and out nodes, and the final axis is constant, linear,
    # quadratic gains.

    # There's a little redundant computation here (what?)
    local_effects = np.empty((num_strategies, num_strategies, 3))
    # Fill in neighbors
    local_effects[..., 0] = 0
    local_effects[..., 1] = rand.uniform(-num_strategies, num_strategies,
                                         (num_strategies, num_strategies))
    local_effects[..., 2] = rand.uniform(-1, 1,
                                         (num_strategies, num_strategies))
    # Mask out some edges
    local_effects *= (rand.random((num_strategies, num_strategies)) >
                      (2 / num_strategies))[..., None]
    # Fill in self
    np.fill_diagonal(local_effects[..., 0],
                     rand.uniform(-(num_players + num_strategies),
                                  num_players + num_strategies,
                                  num_strategies))
    np.fill_diagonal(local_effects[..., 1],
                     rand.uniform(-num_players, 0, num_strategies))
    np.fill_diagonal(local_effects[..., 2], 0)

    # Compute all profiles and payoffs
    counts = (empty_role_symmetric_game(1, num_players, num_strategies)
              .all_profiles(as_array=True))
    payoffs = (local_effects * counts[..., None, None] ** np.arange(3))\
        .sum((1, 3)) * (counts > 0)

    # Compute string names of things
    role = next(_random_strings(1, prefix='r', cool=cool))
    strategies = list(_random_strings(num_strategies, prefix='s', cool=cool))

    return rsgame.Game({role: num_players}, {role: strategies}, counts,
                       payoffs)


# TODO make more efficient i.e. don't loop through all player combinations in
# python
# TODO make matrix game generate the compact form instead of calling the
# function on it...
# TODO allow variable number of strategies
def polymatrix_game(num_players, num_strategies, matrix_game=independent_game,
                    players_per_matrix=2, cool=False):
    """Creates a polymatrix game using the specified k-player matrix game function.

    Each player's payoff in each profile is a sum over independent games played
    against each set of opponents. Each k-tuple of players plays an instance of
    the specified random k-player matrix game.

    players_per_matrix: k
    matrix_game:        a function of two arguments (player_per_matrix,
                        num_strategies) that returns 2-player,
                        num_strategies-strategy games.

    Note: The actual roles and strategies of matrix game are ignored.
    """
    payoffs = np.zeros([num_strategies] * num_players + [num_players])
    for players in itertools.combinations(range(num_players),
                                          players_per_matrix):
        subgame = matrix_game(players_per_matrix, num_strategies)
        sub_payoffs, _ = _compact_payoffs(subgame)
        new_shape = np.array([1] * num_players + [players_per_matrix])
        new_shape[list(players)] = num_strategies
        payoffs[..., list(players)] += sub_payoffs.reshape(new_shape)

    # Generate names
    roles = _random_strings(num_players, prefix='r', cool=cool)
    strategies = collect.fodict(
        (role, tuple(_random_strings(num_strategies, prefix='s', cool=cool)))
        for role in roles)

    return rsgame.Game.from_matrix(strategies, payoffs)


def rock_paper_scissors():
    players = {'all': 2}
    strategies = {'all': ['rock', 'paper', 'scissors']}
    profiles = np.array([[2, 0, 0],
                         [1, 1, 0],
                         [1, 0, 1],
                         [0, 2, 0],
                         [0, 1, 1],
                         [0, 0, 2]])
    payoffs = np.array([[0., 0., 0.],
                        [-1., 1., 0.],
                        [1., 0., -1.],
                        [0., 0., 0.],
                        [0., -1., 1.],
                        [0., 0., 0.]])
    return rsgame.Game(players, strategies, profiles, payoffs)


def add_noise(game, num_samples, noise=default_distribution):
    """Generate sample game by adding noise to game payoffs

    Arguments
    ---------
    game:        A Game or SampleGame (only current payoffs are used)
    num_samples: The number of observations to create per profile
    noise:       A noise generating function. The function should take a single
                 shape parameter, and return a number of samples equal to
                 shape. In order to preserve mixed equilibria, noise should
                 also be zero mean (aka unbiased)
    """
    aprofiles = game.profiles(as_array=True)
    apayoffs = game.payoffs(as_array=True)
    mask = aprofiles > 0
    sample_payoffs = np.zeros(apayoffs.shape + (num_samples,))
    pview = sample_payoffs.view()
    pview.shape = (-1, num_samples)
    pview[mask.ravel()] = apayoffs[mask, None] + noise((mask.sum(),
                                                        num_samples))
    return rsgame.SampleGame(game.players, game.strategies, aprofiles,
                             [sample_payoffs])

# def gaussian_mixture_noise(max_stdev, samples, modes=2, spread_mult=2):
#     """
#     Generate Gaussian mixture noise to add to one payoff in a game.

#     max_stdev: maximum standard deviation for the mixed distributions (also
#                 affects how widely the mixed distributions are spaced)
#     samples: numer of samples to take of every profile
#     modes: number of Gaussians to mix
#     spread_mult: multiplier for the spread of the Gaussians. Distance between
#                 the mean and the nearest distribution is drawn from
#                 N(0,max_stdev*spread_mult).
#     """
#     multipliers = arange(float(modes)) - float(modes-1)/2
#     offset = normal(0, max_stdev * spread_mult)
#     stdev = beta(2,1) * max_stdev
#     return [normal(choice(multipliers)*offset, stdev) for _ in range(samples)] # noqa


# eq_var_normal_noise = partial(normal, 0)
# normal_noise = partial(gaussian_mixture_noise, modes=1)
# bimodal_noise = partial(gaussian_mixture_noise, modes=2)


# def nonzero_gaussian_noise(max_stdev, samples, prob_pos=0.5, spread_mult=1):
#     """
#     Generate Noise from a normal distribution centered up to one stdev from 0. # noqa

#     With prob_pos=0.5, this implements the previous buggy output of
#     bimodal_noise.

#     max_stdev: maximum standard deviation for the mixed distributions (also
#                 affects how widely the mixed distributions are spaced)
#     samples: numer of samples to take of every profile
#     prob_pos: the probability that the noise mean for any payoff will be >0.
#     spread_mult: multiplier for the spread of the Gaussians. Distance between
#                 the mean and the mean of the distribution is drawn from
#                 N(0,max_stdev*spread_mult).
#     """
#     offset = normal(0, max_stdev)*(1 if U(0,1) < prob_pos else -1)*spread_mult # noqa
#     stdev = beta(2,1) * max_stdev
#     return normal(offset, stdev, samples)


# def uniform_noise(max_half_width, samples):
#     """
#     Generate uniform random noise to add to one payoff in a game.

#     max_range: maximum half-width of the uniform distribution
#     samples: numer of samples to take of every profile
#     """
#     hw = beta(2,1) * max_half_width
#     return U(-hw, hw, samples)


# def gumbel_noise(scale, samples, flip_prob=0.5):
#     """
#     Generate random noise according to a gumbel distribution.

#     Gumbel distributions are skewed, so the default setting of the flip_prob
#     parameter makes it equally likely to be skewed positive or negative

#     variance ~= 1.6*scale
#     """
#     location = -0.5772*scale
#     multiplier = -1 if (U(0,1) < flip_prob) else 1
#     return multiplier * gumbel(location, scale, samples)


# def mix_models(models, rates, spread, samples):
#     """
#     Generate SampleGame with noise drawn from several models.

#     models: a list of 2-parameter noise functions to draw from
#     rates: the probabilites with which a payoff will be drawn from each model
#     spread, samples: the parameters passed to the noise functions
#     """
#     cum_rates = cumsum(rates)
#     m = models[bisect(cum_rates, U(0,1))]
#     return m(spread, samples)