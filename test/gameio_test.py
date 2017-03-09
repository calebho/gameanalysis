import copy
import json
import warnings

import numpy as np
import pytest

from gameanalysis import gameio
from gameanalysis import rsgame
from gameanalysis import utils


SERIAL = gameio.gameserializer(['role'], [['strat1', 'strat2']])

GAME = rsgame.samplegame(
    [2], [2],
    [[2, 0],
     [1, 1],
     [0, 2]],
    [
        [[[-1, 0, 1], [0, 0, 0]],
         [[9, 10, 11], [21, 20, 19]]],
        [[[0, 0, 0, 0], [32, 28, 30, 30]]],
    ],
)

BASEGAME_JSON = {
    'players': {
        'role': 2,
    },
    'strategies': {
        'role': [
            'strat1',
            'strat2',
        ],
    },
}

GAME_JSON = {
    'players': {
        'role': 2,
    },
    'strategies': {
        'role': [
            'strat1',
            'strat2',
        ],
    },
    'profiles': [
        {
            'role': [
                ('strat1', 2, 0.0),
            ],
        },
        {
            'role': [
                ('strat1', 1, 10.0),
                ('strat2', 1, 20.0),
            ],
        },
        {
            'role': [
                ('strat2', 2, 30.0),
            ],
        },
    ],
}

SAMPLEGAME_JSON = {
    'players': {
        'role': 2,
    },
    'strategies': {
        'role': [
            'strat1',
            'strat2',
        ],
    },
    'profiles': [
        {
            'role': [
                ('strat1', 2, [-1.0, 0.0, 1.0]),
            ],
        },
        {
            'role': [
                ('strat1', 1, [9.0, 10.0, 11.0]),
                ('strat2', 1, [21.0, 20.0, 19.0]),
            ],
        },
        {
            'role': [
                ('strat2', 2, [32.0, 28.0, 30.0, 30.0]),
            ],
        },
    ],
}

EMPTYGAME_JSON = {
    'roles': [
        {
            'name': 'role',
            'strategies': [
                'strat1',
                'strat2',
            ],
            'count': 2,
        },
    ],
}

SUMMARYGAME_JSON = {
    'roles': [
        {
            'name': 'role',
            'strategies': [
                'strat1',
                'strat2',
            ],
            'count': 2,
        },
    ],
    'profiles': [
        {
            'symmetry_groups': [
                {
                    'payoff': 0,
                    'count': 2,
                    'strategy': 'strat1',
                    'role': 'role',
                },
            ],
        },
        {
            'symmetry_groups': [
                {
                    'payoff': 10,
                    'count': 1,
                    'strategy': 'strat1',
                    'role': 'role',
                },
                {
                    'payoff': 20,
                    'count': 1,
                    'strategy': 'strat2',
                    'role': 'role',
                },
            ],
        },
        {
            'symmetry_groups': [
                {
                    'payoff': 30,
                    'count': 2,
                    'strategy': 'strat2',
                    'role': 'role',
                },
            ],
        },
    ],
}

OBSERVATIONGAME_JSON = {
    'roles': [
        {
            'name': 'role',
            'strategies': [
                'strat1',
                'strat2',
            ],
            'count': 2,
        },
    ],
    'profiles': [
        {
            'symmetry_groups': [
                {
                    'strategy': 'strat1',
                    'id': 0,
                    'role': 'role',
                    'count': 2,
                },
            ],
            'observations': [
                {
                    'symmetry_groups': [
                        {
                            'id': 0,
                            'payoff': -1,
                        },
                    ],
                },
                {
                    'symmetry_groups': [
                        {
                            'id': 0,
                            'payoff': 0,
                        },
                    ],
                },
                {
                    'symmetry_groups': [
                        {
                            'id': 0,
                            'payoff': 1,
                        },
                    ],
                },
            ],
        },
        {
            'symmetry_groups': [
                {
                    'strategy': 'strat1',
                    'id': 1,
                    'role': 'role',
                    'count': 1,
                },
                {
                    'strategy': 'strat2',
                    'id': 2,
                    'role': 'role',
                    'count': 1,
                },
            ],
            'observations': [
                {
                    'symmetry_groups': [
                        {
                            'id': 1,
                            'payoff': 9,
                        },
                        {
                            'id': 2,
                            'payoff': 21,
                        },
                    ],
                },
                {
                    'symmetry_groups': [
                        {
                            'id': 1,
                            'payoff': 10,
                        },
                        {
                            'id': 2,
                            'payoff': 20,
                        },
                    ],
                },
                {
                    'symmetry_groups': [
                        {
                            'id': 1,
                            'payoff': 11,
                        },
                        {
                            'id': 2,
                            'payoff': 19,
                        },
                    ],
                },
            ],
        },
        {
            'symmetry_groups': [
                {
                    'strategy': 'strat2',
                    'id': 3,
                    'role': 'role',
                    'count': 2,
                },
            ],
            'observations': [
                {
                    'symmetry_groups': [
                        {
                            'id': 3,
                            'payoff': 32,
                        },
                    ],
                },
                {
                    'symmetry_groups': [
                        {
                            'id': 3,
                            'payoff': 28,
                        },
                    ],
                },
                {
                    'symmetry_groups': [
                        {
                            'id': 3,
                            'payoff': 30,
                        },
                    ],
                },
                {
                    'symmetry_groups': [
                        {
                            'id': 3,
                            'payoff': 30,
                        },
                    ],
                },
            ],
        },
    ],
}

FULLGAME_JSON = {
    'roles': [
        {
            'name': 'role',
            'strategies': [
                'strat1',
                'strat2',
            ],
            'count': 2,
        },
    ],
    'profiles': [
        {
            'symmetry_groups': [
                {
                    'strategy': 'strat1',
                    'id': 0,
                    'role': 'role',
                    'count': 2,
                },
            ],
            'observations': [
                {
                    'players': [
                        {
                            'sid': 0,
                            'p': -2,
                        },
                        {
                            'sid': 0,
                            'p': 0,
                        },
                    ],
                },
                {
                    'players': [
                        {
                            'sid': 0,
                            'p': 0,
                        },
                        {
                            'sid': 0,
                            'p': 0,
                        },
                    ],
                },
                {
                    'players': [
                        {
                            'sid': 0,
                            'p': 0,
                        },
                        {
                            'sid': 0,
                            'p': 2,
                        },
                    ],
                },
            ],
        },
        {
            'symmetry_groups': [
                {
                    'strategy': 'strat1',
                    'id': 1,
                    'role': 'role',
                    'count': 1,
                },
                {
                    'strategy': 'strat2',
                    'id': 2,
                    'role': 'role',
                    'count': 1,
                },
            ],
            'observations': [
                {
                    'players': [
                        {
                            'sid': 1,
                            'p': 9,
                        },
                        {
                            'sid': 2,
                            'p': 21,
                        },
                    ],
                },
                {
                    'players': [
                        {
                            'sid': 1,
                            'p': 10,
                        },
                        {
                            'sid': 2,
                            'p': 20,
                        },
                    ],
                },
                {
                    'players': [
                        {
                            'sid': 1,
                            'p': 11,
                        },
                        {
                            'sid': 2,
                            'p': 19,
                        },
                    ],
                },
            ],
        },
        {
            'symmetry_groups': [
                {
                    'strategy': 'strat2',
                    'id': 3,
                    'role': 'role',
                    'count': 2,
                },
            ],
            'observations': [
                {
                    'players': [
                        {
                            'sid': 3,
                            'p': 32,
                        },
                        {
                            'sid': 3,
                            'p': 32,
                        },
                    ],
                },
                {
                    'players': [
                        {
                            'sid': 3,
                            'p': 30,
                        },
                        {
                            'sid': 3,
                            'p': 26,
                        },
                    ],
                },
                {
                    'players': [
                        {
                            'sid': 3,
                            'p': 34,
                        },
                        {
                            'sid': 3,
                            'p': 26,
                        },
                    ],
                },
                {
                    'players': [
                        {
                            'sid': 3,
                            'p': 28,
                        },
                        {
                            'sid': 3,
                            'p': 32,
                        },
                    ],
                },
            ],
        },
    ],
}


@pytest.mark.parametrize('jgame', [BASEGAME_JSON, GAME_JSON, SAMPLEGAME_JSON,
                                   EMPTYGAME_JSON, SUMMARYGAME_JSON,
                                   OBSERVATIONGAME_JSON, FULLGAME_JSON])
def test_basegame_from_json(jgame):
    gameio.read_basegame(jgame)


@pytest.mark.parametrize('jgame', [BASEGAME_JSON, GAME_JSON, SAMPLEGAME_JSON,
                                   EMPTYGAME_JSON, SUMMARYGAME_JSON,
                                   OBSERVATIONGAME_JSON, FULLGAME_JSON])
def test_game_from_json(jgame):
    gameio.read_game(jgame)


@pytest.mark.parametrize('jgame', [BASEGAME_JSON, GAME_JSON, SAMPLEGAME_JSON,
                                   EMPTYGAME_JSON, SUMMARYGAME_JSON,
                                   OBSERVATIONGAME_JSON, FULLGAME_JSON])
def test_samplegame_from_json(jgame):
    gameio.read_samplegame(jgame)


@pytest.mark.parametrize('jgame', [BASEGAME_JSON, GAME_JSON, SAMPLEGAME_JSON,
                                   EMPTYGAME_JSON, SUMMARYGAME_JSON,
                                   OBSERVATIONGAME_JSON, FULLGAME_JSON])
def test_basegame_equality(jgame):
    game, serial = gameio.read_basegame(jgame)
    assert game == rsgame.basegame_copy(GAME)
    assert serial == SERIAL


@pytest.mark.parametrize('jgame', [GAME_JSON, SAMPLEGAME_JSON,
                                   SUMMARYGAME_JSON, OBSERVATIONGAME_JSON,
                                   FULLGAME_JSON])
def test_game_equality(jgame):
    game, serial = gameio.read_game(jgame)
    assert rsgame.game_copy(game) == rsgame.game_copy(GAME)
    assert serial == SERIAL


@pytest.mark.parametrize('jgame', [SAMPLEGAME_JSON, OBSERVATIONGAME_JSON,
                                   FULLGAME_JSON])
def test_samplegame_equality(jgame):
    game, serial = gameio.read_samplegame(jgame)
    assert game == GAME
    assert serial == SERIAL


def test_output():
    EMPTYGAME_JSON = BASEGAME_JSON.copy()
    EMPTYGAME_JSON['profiles'] = []

    SAMPLEDGAME_JSON = copy.deepcopy(GAME_JSON)
    for prof in SAMPLEDGAME_JSON['profiles']:
        for pays in prof.values():
            pays[:] = [(s, c, [p]) for s, c, p in pays]

    assert BASEGAME_JSON == SERIAL.to_basegame_json(GAME)
    assert BASEGAME_JSON == SERIAL.to_basegame_json(rsgame.game_copy(GAME))
    assert BASEGAME_JSON == SERIAL.to_basegame_json(rsgame.basegame_copy(GAME))

    assert GAME_JSON == SERIAL.to_game_json(GAME)
    assert GAME_JSON == SERIAL.to_game_json(rsgame.game_copy(GAME))
    assert EMPTYGAME_JSON == SERIAL.to_game_json(rsgame.basegame_copy(GAME))

    assert SAMPLEGAME_JSON == SERIAL.to_samplegame_json(GAME)
    assert SAMPLEDGAME_JSON == SERIAL.to_samplegame_json(
        rsgame.game_copy(GAME))
    assert EMPTYGAME_JSON == SERIAL.to_samplegame_json(
        rsgame.basegame_copy(GAME))

    expected = """
BaseGame:
    Roles: role
    Players:
        2x role
    Strategies:
        role:
            strat1
            strat2
"""[1:-1]
    assert expected == SERIAL.to_basegame_printstring(GAME)
    assert expected == SERIAL.to_basegame_printstring(rsgame.game_copy(GAME))
    assert expected == SERIAL.to_basegame_printstring(
        rsgame.basegame_copy(GAME))

    expected = """
Game:
    Roles: role
    Players:
        2x role
    Strategies:
        role:
            strat1
            strat2
payoff data for 3 out of 3 profiles
"""[1:-1]
    assert expected == SERIAL.to_game_printstring(GAME)
    assert expected == SERIAL.to_game_printstring(rsgame.game_copy(GAME))
    expected = """
Game:
    Roles: role
    Players:
        2x role
    Strategies:
        role:
            strat1
            strat2
payoff data for 0 out of 3 profiles
"""[1:-1]
    assert expected == SERIAL.to_game_printstring(rsgame.basegame_copy(GAME))

    expected = """
SampleGame:
    Roles: role
    Players:
        2x role
    Strategies:
        role:
            strat1
            strat2
payoff data for 3 out of 3 profiles
3 to 4 observations per profile
"""[1:-1]
    assert expected == SERIAL.to_samplegame_printstring(GAME)
    expected = """
SampleGame:
    Roles: role
    Players:
        2x role
    Strategies:
        role:
            strat1
            strat2
payoff data for 3 out of 3 profiles
1 observation per profile
"""[1:-1]
    assert expected == SERIAL.to_samplegame_printstring(rsgame.game_copy(GAME))
    expected = """
SampleGame:
    Roles: role
    Players:
        2x role
    Strategies:
        role:
            strat1
            strat2
payoff data for 0 out of 3 profiles
no observations
"""[1:-1]
    assert expected == SERIAL.to_samplegame_printstring(
        rsgame.basegame_copy(GAME))


@pytest.mark.parametrize('_', range(20))
def test_sorted_strategy_loading(_):
    with open('test/hard_nash_game_1.json') as f:
        _, serial = gameio.read_basegame(json.load(f))
    assert utils.is_sorted(serial.role_names), \
        "loaded json game didn't have sorted roles"
    assert all(utils.is_sorted(strats) for strats in serial.strat_names), \
        "loaded json game didn't have sorted strategies"


def test_to_from_prof_json():
    game = gameio.gameserializer(['a', 'b'], [['bar', 'foo'], ['baz']])

    prof = [6, 5, 3]
    json_prof = {'a': {'foo': 5, 'bar': 6}, 'b': {'baz': 3}}
    assert game.to_prof_json(prof) == json_prof
    assert np.all(game.from_prof_json(json_prof) == prof)
    assert game.from_prof_json(json_prof).dtype == int

    mix = [.6, .4, 1]
    json_mix = {'a': {'foo': .4, 'bar': .6}, 'b': {'baz': 1}}
    assert game.to_prof_json(mix) == json_mix
    assert np.all(game.from_prof_json(json_mix, dtype=float) == mix)
    assert game.from_prof_json(json_mix, dtype=float).dtype == float

    sub = [True, False, True]
    json_sub = {'a': {'bar': True}, 'b': {'baz': True}}
    assert game.to_prof_json(sub) == json_sub
    assert np.all(game.from_prof_json(json_sub, dtype=bool) == sub)
    assert game.from_prof_json(json_sub, dtype=bool).dtype == bool

    prof_str = 'a: 5 foo, 6 bar; b: 3 baz'
    assert np.all(game.from_prof_string(prof_str) == prof)
    assert set(game.to_prof_string(prof)) == set(prof_str)

    prof = [3, 0, 4]
    obs = [[3, 0, 7], [4, 0, 8], [5, 0, 9]]
    json_obs = {'a': {'bar': [3, 4, 5]}, 'b': {'baz': [7, 8, 9]}}
    assert game.to_obs_json(prof, obs) == json_obs
    assert np.allclose(game.from_obs_json(json_obs), obs)

    json_profobs = {'a': [('bar', 3,  [3, 4, 5])],
                    'b': [('baz', 4, [7, 8, 9])]}
    assert game.to_profobs_json(prof, obs) == json_profobs
    p, o = game.from_profobs_json(json_profobs)
    assert np.all(p == prof)
    assert np.allclose(o, obs)

    prof = [6, 5, 3]
    expected = """
a:
    bar: 6
    foo: 5
b:
    baz: 3
"""[1:]
    assert game.to_prof_printstring(prof) == expected

    mix = [0.3, 0.7, 1]
    expected = """
a:
    bar:  30.00%
    foo:  70.00%
b:
    baz: 100.00%
"""[1:]
    assert game.to_prof_printstring(mix) == expected

    sub = [True, False, True]
    expected = """
a:
    bar
b:
    baz
"""[1:]
    assert game.to_prof_printstring(sub) == expected


def test_to_from_role_json():
    game = gameio.gameserializer(['a', 'b'], [['bar', 'foo'], ['baz']])
    role = [6, 3]
    json_role = {'a': 6, 'b': 3}
    assert game.to_role_json(role) == json_role
    assert np.all(game.from_role_json(json_role) == role)
    assert game.from_role_json(json_role).dtype == float


def test_deviation_payoff_json():
    game = gameio.gameserializer(['a', 'b'], [['bar', 'foo'], ['baz']])
    prof = [3, 0, 4]
    devpay = [5]
    json_devpay = {'a': {'bar': {'foo': 5}}, 'b': {'baz': {}}}
    assert game.to_deviation_payoff_json(prof, devpay) == json_devpay

    prof = [2, 1, 4]
    devpay = [5, 4]
    json_devpay = {'a': {'bar': {'foo': 5},
                         'foo': {'bar': 4}}, 'b': {'baz': {}}}
    assert game.to_deviation_payoff_json(prof, devpay) == json_devpay


def test_to_pay_json():
    jprof = SERIAL.to_payoff_json(GAME.profiles[0], GAME.payoffs[0])
    assert jprof == {'role': {'strat1': 0}}
    jprof = SERIAL.to_payoff_json(GAME.profiles[1], GAME.payoffs[1])
    assert jprof == {'role': {'strat1': 10, 'strat2': 20}}
    jprof = SERIAL.to_payoff_json(GAME.profiles[2], GAME.payoffs[2])
    assert jprof == {'role': {'strat2': 30}}

    jprof = SERIAL.to_profpay_json(GAME.profiles[0], GAME.payoffs[0])
    assert jprof == {'role': [('strat1', 2, 0)]}
    jprof = {k: set(v) for k, v in SERIAL.to_profpay_json(
        GAME.profiles[1], GAME.payoffs[1]).items()}
    assert jprof == {'role': set([('strat1', 1, 10), ('strat2', 1, 20)])}
    jprof = SERIAL.to_profpay_json(GAME.profiles[2], GAME.payoffs[2])
    assert jprof == {'role': [('strat2', 2, 30)]}


@pytest.mark.parametrize('jgame', [GAME_JSON, SAMPLEGAME_JSON,
                                   SUMMARYGAME_JSON, OBSERVATIONGAME_JSON,
                                   FULLGAME_JSON])
def test_to_from_payoff_json(jgame):
    _, serial = gameio.read_basegame(jgame)
    payoffs = np.concatenate([serial.from_payoff_json(p)[None]
                              for p in jgame['profiles']])
    expected = [[0, 0],
                [10, 20],
                [0, 30]]
    assert np.allclose(expected, payoffs)


def test_load_empty_observations():
    serial = gameio.gameserializer(['a', 'b'], [['bar', 'foo'], ['baz']])
    profile = {
        'symmetry_groups': [
            {
                'strategy': 'bar',
                'id': 0,
                'role': 'a',
                'count': 1,
            },
            {
                'strategy': 'baz',
                'id': 1,
                'role': 'b',
                'count': 1,
            },
        ],
        'observations': [],
    }
    payoff = serial.from_payoff_json(profile)
    assert np.allclose(payoff, [np.nan, 0, np.nan], equal_nan=True)

    profile = {
        'a': {
            'bar': []
        },
        'b': {
            'baz': []
        },
    }
    payoff = serial.from_payoff_json(profile)
    assert np.allclose(payoff, [np.nan, 0, np.nan], equal_nan=True)


def test_sorted_strategy_warning():
    with pytest.raises(UserWarning), warnings.catch_warnings():
        warnings.simplefilter('error')
        gameio.gameserializer(['role'], [['b', 'a']])


def test_invalid_game():
    with pytest.raises(ValueError):
        SERIAL.from_basegame_json({})
    with pytest.raises(ValueError):
        gameio.read_basegame({})


def test_repr():
    assert repr(SERIAL) is not None


def test_strat_name():
    serial = gameio.gameserializer(['a', 'b'], [['e', 'q', 'w'], ['r', 't']])
    for i, s in enumerate(['e', 'q', 'w', 'r', 't']):
        assert s == serial.strat_name(i)


def test_index():
    serial = gameio.gameserializer(['a', 'b'], [['e', 'q', 'w'], ['r', 't']])
    assert 0 == serial.role_index('a')
    assert 1 == serial.role_index('b')
    assert 0 == serial.role_strat_index('a', 'e')
    assert 1 == serial.role_strat_index('a', 'q')
    assert 2 == serial.role_strat_index('a', 'w')
    assert 3 == serial.role_strat_index('b', 'r')
    assert 4 == serial.role_strat_index('b', 't')


def test_serialization():
    json.dumps(SERIAL.to_basegame_json(GAME))
    json.dumps(SERIAL.to_game_json(GAME))
    json.dumps(SERIAL.to_samplegame_json(GAME))
