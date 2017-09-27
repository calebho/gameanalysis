import numpy as np
import numpy.random as rand
import pytest

from gameanalysis import bootstrap
from gameanalysis import gamegen

SMALL_GAMES = [
    ([1], 1),
    ([1], 2),
    ([2], 1),
    ([2], 2),
    ([2], 5),
    ([5], 2),
    ([5], 5),
    (2 * [1], 1),
    (2 * [1], 2),
    (2 * [2], 1),
    (2 * [2], 2),
    (5 * [1], 2),
]
GAMES = SMALL_GAMES + [
    (2 * [1], 5),
    (2 * [2], 5),
    (2 * [5], 2),
    (2 * [5], 5),
    (3 * [3], 3),
    (5 * [1], 5),
    ([170], 2),
    ([180], 2),
    ([1, 2], 2),
    ([1, 2], [2, 1]),
    (2, [1, 2]),
    ([3, 4], [2, 3]),
    ([2, 3, 4], [4, 3, 2]),
]


def test_mean():
    means = rand.random(100)
    min_val = means.min()
    max_val = means.max()
    boots = bootstrap.mean(means, 200)
    assert boots.shape == (200,)
    assert np.all(boots >= min_val)
    assert np.all(boots <= max_val)

    perc_boots = bootstrap.mean(means, 200, percentiles=[2.5, 97.5])
    assert perc_boots.shape == (2,)
    assert np.all(perc_boots >= min_val)
    assert np.all(perc_boots <= max_val)


@pytest.mark.parametrize('players,strategies', GAMES)
def test_sample_regret(players, strategies):
    n = 100
    game = gamegen.role_symmetric_game(players, strategies)
    max_regret = np.max(game.max_role_payoffs() - game.min_role_payoffs())
    mix = game.random_mixtures()
    dev_profs = game.random_deviator_profiles(mix, n)
    dev_profs.shape = (-1, game.num_strats)
    inds = np.broadcast_to(np.arange(game.num_strats),
                           (n, game.num_strats)).flat
    dev_payoffs = np.fromiter(
        (game.get_payoffs(p)[i] for p, i in zip(dev_profs, inds)),
        float, n * game.num_strats)
    dev_payoffs.shape = (n, game.num_strats)
    mix_payoffs = np.add.reduceat(dev_payoffs * mix, game.role_starts, 1)
    boots = bootstrap.sample_regret(game, mix_payoffs, dev_payoffs, 200)
    assert boots.shape == (200,)
    assert np.all(boots <= max_regret)
    assert np.all(boots >= 0)

    perc_boots = bootstrap.sample_regret(game, mix_payoffs, dev_payoffs, 200,
                                         percentiles=[2.5, 97.5])
    assert perc_boots.shape == (2,)
    assert np.all(perc_boots <= max_regret)
    assert np.all(perc_boots >= 0)


@pytest.mark.parametrize('players,strategies', GAMES)
def test_mixture_welfare(players, strategies):
    num_mixes = 5
    num_boots = 200
    game = gamegen.add_noise(gamegen.role_symmetric_game(players, strategies),
                             1, 3)
    mixes = game.random_mixtures(num_mixes)
    boots = bootstrap.mixture_welfare(game, mixes, num_boots, processes=1)
    assert boots.shape == (num_mixes, num_boots)


@pytest.mark.parametrize('players,strategies', SMALL_GAMES)
def test_mixture_regret(players, strategies):
    num_mixes = 5
    num_boots = 200
    game = gamegen.add_noise(gamegen.role_symmetric_game(players, strategies),
                             1, 3)
    mixes = game.random_mixtures(num_mixes)
    boots = bootstrap.mixture_regret(game, mixes, num_boots, processes=1)
    assert boots.shape == (num_mixes, num_boots)
    assert np.all(boots >= 0)

    perc_boots = bootstrap.mixture_regret(game, mixes, num_boots,
                                          percentiles=[2.5, 97.5], processes=1)
    assert perc_boots.shape == (num_mixes, 2)
    assert np.all(perc_boots >= 0)


@pytest.mark.parametrize('players,strategies', GAMES)
def test_mixture_regret_single_mix(players, strategies):
    num_boots = 200
    game = gamegen.add_noise(gamegen.role_symmetric_game(players, strategies),
                             1, 3)
    mix = game.random_mixtures()
    boots = bootstrap.mixture_regret(game, mix, num_boots, processes=1)
    assert boots.shape == (1, num_boots)
    assert np.all(boots >= 0)


def test_mixture_regret_parallel():
    num_mixes = 5
    num_boots = 200
    game = gamegen.add_noise(gamegen.role_symmetric_game([4, 3], [3, 4]), 1,
                             3)
    mixes = game.random_mixtures(num_mixes)
    boots = bootstrap.mixture_regret(game, mixes, num_boots)
    assert boots.shape == (num_mixes, num_boots)
    assert np.all(boots >= 0)
