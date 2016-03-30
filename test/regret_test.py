import math

import numpy as np

from gameanalysis import gamegen
from gameanalysis import regret
from gameanalysis import rsgame
from test import testutils


@testutils.apply(repeat=20)
def pure_prisoners_dilemma_test():
    game = gamegen.sym_2p2s_game(2, 0, 3, 1)  # prisoners dilemma
    role = next(iter(game.strategies))
    strats = list(game.strategies[role])
    eqm = {role: {strats[1]: 2}}

    assert regret.pure_strategy_regret(game, eqm) == 0, \
        "Known equilibrium was not zero regret"


@testutils.apply(repeat=20)
def mixed_prisoners_dilemma_test():
    game = gamegen.sym_2p2s_game(2, 0, 3, 1)  # prisoners dilemma
    role = next(iter(game.strategies))
    strats = list(game.strategies[role])
    eqm = {role: {strats[1]: 1}}

    assert regret.mixture_regret(game, eqm) == 0, \
        "Known symmetric mixed was not zero regret"


def mixed_incomplete_data_test():
    game = rsgame.Game({'r': 2}, {'r': ['1', '2']},
                       np.array([[2, 0],
                                 [1, 1]]),
                       np.array([[4.3, 0],
                                 [6.2, 6.7]]))
    dg = regret.mixture_deviation_gains(game, {'r': {'1': 1}}, as_array=True)
    expected_gains = np.array([0.0, 2.4])
    assert np.allclose(dg, expected_gains), \
        "mixture gains wrong {} instead of {}".format(dg, expected_gains)
    dg = regret.mixture_deviation_gains(game, game.uniform_mixture(),
                                        as_array=True)
    assert np.isnan(dg).all(), "had data for mixture without data"


def mixed_incomplete_data_test_2():
    game = rsgame.Game({'r': 2}, {'r': ['1', '2']},
                       np.array([[2, 0]]),
                       np.array([[1.0, 0.0]]))
    dg = regret.mixture_deviation_gains(game, {'r': {'1': 1}})
    assert dg['r']['1'] == 0, \
        "nonzero regret for mixture {}".format(dg)
    assert math.isnan(dg['r']['2']), \
        "deviation without payoff didn't return nan {}".format(dg)


def pure_incomplete_data_test():
    game = rsgame.Game({'r': 2}, {'r': ['1', '2']},
                       np.array([[2, 0]]),
                       np.array([[1.0, 0.0]]))
    reg = regret.pure_strategy_regret(game, [2, 0])
    assert math.isnan(reg), "regret of missing profile not nan"


@testutils.apply(zip(range(6)), repeat=20)
def two_player_zero_sum_pure_wellfare_test(strategies):
    game = gamegen.zero_sum_game(6)
    for prof in game.all_profiles():
        assert abs(regret.pure_social_welfare(game, prof)) < 1e-5, \
            "zero sum profile wasn't zero sum"


def nonzero_profile_welfare_test():
    game = rsgame.Game.from_matrix({'a': ['s'], 'b': ['s']},
                                   np.array([[[3.5, 2.5]]]))
    assert abs(6 - regret.pure_social_welfare(
        game, {'a': {'s': 1}, 'b': {'s': 1}})) < 1e-5, \
        "Didn't properly sum welfare"


@testutils.apply(zip(range(6)), repeat=20)
def two_player_zero_sum_mixed_wellfare_test(strategies):
    game = gamegen.zero_sum_game(6)
    for prof in game.random_mixtures(20):
        assert abs(regret.mixed_social_welfare(game, prof)) < 1e-5, \
            "zero sum profile wasn't zero sum"


def nonzero_mixed_welfare_test():
    game = rsgame.Game.from_matrix({'a': ['s'], 'b': ['s']},
                                   np.array([[[3.5, 2.5]]]))
    assert abs(6 - regret.mixed_social_welfare(
        game, {'a': {'s': 1}, 'b': {'s': 1}})) < 1e-5, \
        "Didn't properly sum welfare"


@testutils.apply([
    (1, 1, 1),
    (1, 1, 2),
    (1, 2, 1),
    (1, 2, 2),
    (2, 1, 1),
    (2, 1, 2),
    (2, 2, 1),
    (2, 2, 2),
    (2, [1, 2], 2),
    (2, 2, [1, 2]),
    (2, [1, 2], [1, 2]),
    (2, [3, 4], [2, 3]),
])
# Test that for complete games, there are never any nan deviations.
def nan_deviations_test(roles, players, strategies):
    game = gamegen.role_symmetric_game(roles, players, strategies)
    for mix in game.random_mixtures(20, 0.05, as_array=True):
        mix = game.trim_mixture_array_support(mix)
        gains = regret.mixture_deviation_gains(game, mix, as_array=True)
        assert not np.isnan(gains).any(), \
            "deviation gains in complete game were nan"
