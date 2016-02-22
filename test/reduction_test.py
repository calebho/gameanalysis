import itertools

from gameanalysis import profile
from gameanalysis import reduction
from gameanalysis import randgames
from test import testutils


@testutils.apply([
    (1, [1], [1], [1]),
    (1, [2], [1], [2]),
    (1, [3], [1], [2]),
    (1, [1], [2], [1]),
    (2, [1, 2], [2, 1], [1, 2]),
    (2, [1, 4], [2, 1], [1, 2]),
    (2, [4, 9], [3, 2], [2, 3]),
])
# Simple test of DPR
# FIXME Test this with non complete games
def drp_test(roles: int, players, strategies, red_players):
    # Create game and reduction
    game = randgames.role_symmetric_game(roles, players, strategies)
    red_players = {r: p for r, p in zip(game.players, red_players)}
    red = reduction.DeviationPreserving(game.players, red_players)

    # Try to reduce game
    red_game = red.reduce_game(game)

    # Assert that reducing all profiles covers reduced game
    full_reduced_profiles = set(itertools.chain.from_iterable(
        red.reduce_profile(prof) for prof in game))
    reduced_profiles = set(red_game)
    assert full_reduced_profiles >= reduced_profiles, \
        "reduced game contained profiles it shouldn't have"

    # Assert that all contributing profiles are in the expansion of the reduced
    # game
    contributing_profiles = {prof for prof in game
                             if any(reduced in reduced_profiles
                                    for reduced in red.reduce_profile(prof))}
    reduced_full_profiles = set(itertools.chain.from_iterable(
        red.expand_profile(prof) for prof in red_game))
    assert contributing_profiles <= reduced_full_profiles, \
        "full game did not have data for all profiles required of reduced"


@testutils.apply([
    (1, [1], [1]),
    (1, [2], [1]),
    (1, [3], [1]),
    (1, [1], [2]),
    (2, [1, 2], [2, 1]),
    (2, [1, 4], [2, 1]),
    (2, [4, 8], [3, 2]),
])
# Simple test of Twins Reduction
# FIXME Test this with non complete games
def twins_test(roles, players, strategies):
    # Create game and reduction
    game = randgames.role_symmetric_game(roles, players, strategies)
    red = reduction.Twins(game.players)

    # Try to reduce game
    red_game = red.reduce_game(game)

    # Assert that reducing all profiles covers reduced game
    full_reduced_profiles = set(itertools.chain.from_iterable(
        red.reduce_profile(prof) for prof in game))
    reduced_profiles = set(red_game)
    assert full_reduced_profiles >= reduced_profiles, \
        "reduced game contained profiles it shouldn't have"

    # Assert that all contributing profiles are in the expansion of the reduced
    # game
    contributing_profiles = {prof for prof in game
                             if any(reduced in reduced_profiles
                                    for reduced in red.reduce_profile(prof))}
    reduced_full_profiles = set(itertools.chain.from_iterable(
        red.expand_profile(prof) for prof in red_game))
    assert contributing_profiles <= reduced_full_profiles, \
        "full game did not have data for all profiles required of reduced"


@testutils.apply([
    (1, [1], [1], [1]),
    (1, [2], [1], [2]),
    (1, [4], [1], [2]),
    (1, [1], [2], [1]),
    (2, [1, 2], [2, 1], [1, 2]),
    (2, [1, 4], [2, 1], [1, 2]),
    (2, [4, 9], [3, 2], [2, 3]),
])
# Simple test of Hierarchical
# FIXME Test this with non complete games
def hierarchical_test(roles, players, strategies, red_players):
    # Create game and reduction
    game = randgames.role_symmetric_game(roles, players, strategies)
    red_players = {r: p for r, p in zip(game.players, red_players)}
    red = reduction.Hierarchical(game.players, red_players)

    # Try to reduce game
    red.reduce_game(game)


@testutils.apply([
    (1, [1], [1]),
    (1, [2], [1]),
    (1, [3], [1]),
    (1, [1], [2]),
    (2, [1, 2], [2, 1]),
    (2, [1, 4], [2, 1]),
    (2, [4, 9], [3, 2]),
])
# Simple test of DPR
# FIXME Test this with non complete games
def identity_test(roles, players, strategies):
    # Create game and reduction
    game = randgames.role_symmetric_game(roles, players, strategies)
    red = reduction.Identity()

    # Try to reduce game
    red_game = red.reduce_game(game)

    # Assert that reducing all profiles covers reduced game
    full_reduced_profiles = set(itertools.chain.from_iterable(
        red.reduce_profile(prof) for prof in game))
    assert full_reduced_profiles == set(red_game), \
        "reduced game didn't match full game"

    reduced_full_profiles = set(itertools.chain.from_iterable(
        red.expand_profile(prof) for prof in red_game))
    assert set(game) == reduced_full_profiles, \
        "full game did not match reduced game"


def approximate_dpr_expansion_test():
    red = reduction.DeviationPreserving({'r': 8}, {'r': 3})
    profs = set(red.expand_profile({'r': {'a': 1, 'b': 2}}))
    expected = {profile.Profile({'r': {'a': 4, 'b': 4}}),
                profile.Profile({'r': {'a': 1, 'b': 7}})}
    assert profs == expected, "generated different profiles than expected"
