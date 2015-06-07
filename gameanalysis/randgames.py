import sys
import argparse
import json
import collections
import numpy as np
import numpy.random as r

from gameanalysis import rsgame

# import GameIO as IO

# from BasicFunctions import leading_zeros

# from functools import partial
# from itertools import combinations
# from bisect import bisect
# from numpy.random import uniform as U, normal, multivariate_normal, beta, gumbel
# from random import choice
# from numpy import array, arange, zeros, fill_diagonal, cumsum


def _gen_rs_game(num_roles, num_players, num_strategies):
    '''Create a role symmetric game'''
    try:
        num_players = list(num_players)
    except TypeError:
        num_players = [num_players] * num_roles
    try:
        num_strategies = list(num_strategies)
    except TypeError:
        num_strategies = [num_strategies] * num_roles

    assert len(num_players) == num_roles, \
        'length of num_players must equal num_roles'
    assert all(p > 0 for p in num_players), \
        'number of players must be greater than zero'
    assert len(num_strategies) == num_roles, \
        'length of num_strategies must equal num_roles'
    assert all(s > 0 for s in num_strategies), \
        'number of strategies must be greater than zero'

    role_len = len(str(num_roles - 1))
    strat_len = [len(str(x - 1)) for x in num_strategies]
    strategies = {'r%0*d' % (role_len, r):
                  {'s%0*d' % (s_len, s) for s in range(num_strat)}
                  for r, num_strat, s_len
                  in zip(range(num_roles), num_strategies, strat_len)}
    players = dict(zip(strategies, num_players))
    return rsgame.EmptyGame(players, strategies)


def role_symmetric_game(num_roles, num_players, num_strategies,
                        distribution=lambda: r.uniform(-1, 1)):
    '''Generate a random role symmetric game

    num_players and num_strategies can be scalers, or lists of length
    num_roles. Payoffs are drawn from distribution.

    '''
    game = _gen_rs_game(num_roles, num_players, num_strategies)
    profile_data = ({role: {(strat, count, distribution())
                            for strat, count in strats.items()}
                     for role, strats in prof.items()}
                    for prof in game.all_profiles())
    return rsgame.Game(game.players, game.strategies, profile_data)


def independent_game(num_players, num_strategies,
                     distribution=lambda: r.uniform(-1, 1)):
    '''Generate an independent game

    All payoff values drawn independently according to specified
    distribution. The distribution defaults to uniform from -1 to 1.

    '''
    return role_symmetric_game(num_players, 1, num_strategies)


def symmetric_game(num_players, num_strategies,
                   distribution=lambda: r.uniform(-1, 1)):
    '''Generate a random symmetric game

    distribution defaults to uniform from -1 to 1.

    '''
    return role_symmetric_game(1, num_players, num_strategies)


def covariant_game(num_players, num_strategies, mean_dist=lambda: 0, var=1,
                   covar_dist=r.uniform):
    '''Generate a covariant game

    Payoff values for each profile drawn according to multivariate normal.

    The multivariate normal for each profile has a constant mean-vector with
    value drawn from mean_dist, constant variance=var, and equal covariance
    between all pairs of players, drawn from covar_dist.

    mean_dist:  Distribution from which mean payoff for each profile is drawn.
                Defaults to constant 0.
    var:        Diagonal entries of covariance matrix
    covar_dist: Distribution from which the value of the off-diagonal
                covariance matrix entries for each profile is drawn

    Both mean_dist and covar_dist should be numpy-style random number
    generators that can return an array.

    '''
    game = _gen_rs_game(num_players, 1, num_strategies)
    mean = np.empty(num_strategies)
    covar = np.empty((num_strategies, num_strategies))

    profile_data = []
    for prof in game.all_profiles():
        mean.fill(mean_dist())
        covar.fill(covar_dist())
        np.fill_diagonal(covar, var)
        payoffs = r.multivariate_normal(mean, covar)
        profile_data.append({role: {(next(iter(strats)), 1, payoffs[i])}
                             for i, (role, strats) in enumerate(prof.items())})
    return rsgame.Game(game.players, game.strategies, profile_data)


def zero_sum_game(num_strategies, distribution=lambda: r.uniform(-1, 1)):
    '''Generate a two-player, zero-sum game

    2-player zero-sum game; player 1 payoffs drawn from given distribution

    distribution defaults to uniform between -1 and 1

    '''
    game = _gen_rs_game(2, 1, num_strategies)
    role1, role2 = game.strategies
    payoff_data = []
    for prof in game.all_profiles():
        row_strat = next(iter(prof[role1]))
        col_strat = next(iter(prof[role2]))
        row_payoff = distribution()
        payoff_data.append({
            role1: {(row_strat, 1, row_payoff)},
            role2: {(col_strat, 1, -row_payoff)}})
    return rsgame.Game(game.players, game.strategies, payoff_data)


def sym_2p2s_game(a=0, b=1, c=2, d=3,
                  distribution=lambda s=None: r.uniform(-1, 1, s)):
    '''Create a symmetric 2-player 2-strategy game of the specified form.

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

    distribution must accept a size parameter a la numpy distributions.

    '''
    game = _gen_rs_game(1, 2, 2)
    role, strats = next(iter(game.strategies.item()))
    strats = list(strats)

    payoffs = sorted(distribution(4))
    payoff_data = [
        {role: {(strats[0], 2, payoffs[a])}},
        {role: {(strats[0], 1, payoffs[b]),
                (strats[1], 1, payoffs[c])}},
        {role: {(strats[1], 2, payoffs[d])}}]
    return rsgame.Game(game.players, game.strategies, payoff_data)


# def congestion_game(N, facilities, required):
#     '''
#     Generates random congestion games with N players and nCr(f,r) strategies.

#     Congestion games are symmetric, so all players belong to role All. Each 
#     strategy is a subset of size #required among the size #facilities set of 
#     available facilities. Payoffs for each strategy are summed over facilities.
#     Each facility's payoff consists of three components:

#     -constant ~ U[0,#facilities]
#     -linear congestion cost ~ U[-#required,0]
#     -quadratic congestion cost ~ U[-1,0]
#     '''
#     roles = ["All"]
#     players = {"All":N}
#     strategies = {'+'.join(["f"+str(f) for f in strat]):strat for strat in \
#             combinations(range(facilities), required)}
#     facility_values = [array([U(facilities), U(-required), U(-1)]) for __ in \
#             range(facilities)]
#     g = Game(roles, players, {"All":strategies.keys()})
#     for prof in g.allProfiles():
#         payoffs = []
#         useage = [0]*facilities
#         for strat, count in prof["All"].items():
#             for facility in strategies[strat]:
#                 useage[facility] += count
#         for strat, count in prof["All"].items():
#             payoffs.append(PayoffData(strat, count, [sum(useage[f]**arange(3) \
#                     * facility_values[f]) for f in strategies[strat]]))
#         g.addProfile({"All":payoffs})
#     return g


# def local_effect_game(N, S):
#     '''
#     Generates random congestion games with N players and S strategies.

#     Local effect games are symmetric, so all players belong to role All. Each
#     strategy corresponds to a node in the G(N,2/S) local effect graph. Payoffs
#     for each strategy consist of constant terms for each strategy, and
#     interaction terms for the number of players choosing that strategy and each
#     neighboring strategy.

#     The one-strategy terms are drawn as follows:
#     -constant ~ U[-N-S,N+S]
#     -linear ~ U[-N,0]

#     The neighbor strategy terms are drawn as follows:
#     -linear ~ U[-S,S]
#     -quadratic ~ U[-1,1]
#     '''
#     g = __make_symmetric_game(N, S)
#     strategies = g.strategies["All"]
#     local_effects = {s:{} for s in strategies}
#     for s in strategies:
#         for d in strategies:
#             if s == d:
#                 local_effects[s][d] = [U(-N-S,N+S),U(-N,0)]
#             elif U(0,S) > 2:
#                 local_effects[s][d] = [U(-S,S),U(-1,1)]
#     for prof in g.allProfiles():
#         payoffs = []
#         for strat, count in prof["All"].items():
#             value = local_effects[strat][strat][0] + \
#                     local_effects[strat][strat][1] * count
#             for neighbor in local_effects[strat]:
#                 if neighbor not in prof["All"]:
#                     continue
#                 nc = prof["All"][neighbor]
#                 value += local_effects[strat][neighbor][0] * count
#                 value += local_effects[strat][neighbor][1] * count**2
#             payoffs.append(PayoffData(strat, count, value))
#         g.addProfile({"All":payoffs})
#     return g


# def polymatrix_game(N, S, matrix_game=partial(independent_game,2)):
#     '''
#     Creates a polymatrix game using the specified 2-player matrix game function.

#     Each player's payoff in each profile is a sum over independent games played
#     against each opponent. Each pair of players plays an instance of the
#     specified random 2-player matrix game.

#     N: number of players
#     S: number of strategies
#     matrix_game: a function of one argument (S) that returns 2-player, 
#                     S-strategy games.
#     '''
#     g = __make_asymmetric_game(N, S)
#     matrices = {pair : matrix_game(S) for pair in combinations(g.roles, 2)}
#     for prof in g.allProfiles():
#         payoffs = {r:0 for r in g.roles}
#         for role in g.roles:
#             role_strat = prof[role].keys()[0]
#             for other in g.roles:
#                 if role < other:
#                     m = matrices[(role, other)]
#                     p0 = sorted(m.players.keys())[0]
#                     p1 = sorted(m.players.keys())[1]
#                 elif role > other:
#                     m = matrices[(other, role)]
#                     p0 = sorted(m.players.keys())[1]
#                     p1 = sorted(m.players.keys())[0]
#                 else:
#                     continue
#                 other_strat = prof[other].keys()[0]
#                 s0 = m.strategies[p0][g.strategies[role].index(role_strat)]
#                 s1 = m.strategies[p1][g.strategies[other].index(other_strat)]
#                 m_prof = Profile({p0:{s0:1},p1:{s1:1}})
#                 payoffs[role] += m.getPayoff(m_prof, p0, s0)
#         g.addProfile({r:[PayoffData(prof[r].keys()[0], 1, payoffs[r])] \
#                         for r in g.roles})
#     return g


# game_functions = filter(lambda k: k.endswith("game") and not \
#                     k.startswith("__"), globals().keys())


# def add_noise(game, model, spread, samples):
#     '''
#     Generate sample game with random noise added to each payoff.
    
#     game: a RSG.Game or RSG.SampleGame
#     model: a 2-parameter function that generates mean-zero noise
#     spread, samples: the parameters passed to the noise function
#     '''
#     sg = SampleGame(game.roles, game.players, game.strategies)
#     for prof in game.knownProfiles():
#         sg.addProfile({r:[PayoffData(s, prof[r][s], game.getPayoff(prof,r,s) + \
#                 model(spread, samples)) for s in prof[r]] for r in game.roles})
#     return sg


# def gaussian_mixture_noise(max_stdev, samples, modes=2, spread_mult=2):
#     '''
#     Generate Gaussian mixture noise to add to one payoff in a game.

#     max_stdev: maximum standard deviation for the mixed distributions (also 
#                 affects how widely the mixed distributions are spaced)
#     samples: numer of samples to take of every profile
#     modes: number of Gaussians to mix
#     spread_mult: multiplier for the spread of the Gaussians. Distance between
#                 the mean and the nearest distribution is drawn from 
#                 N(0,max_stdev*spread_mult).
#     '''
#     multipliers = arange(float(modes)) - float(modes-1)/2
#     offset = normal(0, max_stdev * spread_mult)
#     stdev = beta(2,1) * max_stdev
#     return [normal(choice(multipliers)*offset, stdev) for _ in range(samples)]


# eq_var_normal_noise = partial(normal, 0)
# normal_noise = partial(gaussian_mixture_noise, modes=1)
# bimodal_noise = partial(gaussian_mixture_noise, modes=2)


# def nonzero_gaussian_noise(max_stdev, samples, prob_pos=0.5, spread_mult=1):
#     '''
#     Generate Noise from a normal distribution centered up to one stdev from 0.

#     With prob_pos=0.5, this implements the previous buggy output of 
#     bimodal_noise.

#     max_stdev: maximum standard deviation for the mixed distributions (also 
#                 affects how widely the mixed distributions are spaced)
#     samples: numer of samples to take of every profile
#     prob_pos: the probability that the noise mean for any payoff will be >0.
#     spread_mult: multiplier for the spread of the Gaussians. Distance between
#                 the mean and the mean of the distribution is drawn from 
#                 N(0,max_stdev*spread_mult).
#     '''
#     offset = normal(0, max_stdev)*(1 if U(0,1) < prob_pos else -1)*spread_mult
#     stdev = beta(2,1) * max_stdev
#     return normal(offset, stdev, samples)


# def uniform_noise(max_half_width, samples):
#     '''
#     Generate uniform random noise to add to one payoff in a game.

#     max_range: maximum half-width of the uniform distribution
#     samples: numer of samples to take of every profile
#     '''
#     hw = beta(2,1) * max_half_width
#     return U(-hw, hw, samples)


# def gumbel_noise(scale, samples, flip_prob=0.5):
#     '''
#     Generate random noise according to a gumbel distribution.

#     Gumbel distributions are skewed, so the default setting of the flip_prob
#     parameter makes it equally likely to be skewed positive or negative

#     variance ~= 1.6*scale
#     '''
#     location = -0.5772*scale
#     multiplier = -1 if (U(0,1) < flip_prob) else 1
#     return multiplier * gumbel(location, scale, samples)


# def mix_models(models, rates, spread, samples):
#     '''
#     Generate SampleGame with noise drawn from several models.

#     models: a list of 2-parameter noise functions to draw from
#     rates: the probabilites with which a payoff will be drawn from each model
#     spread, samples: the parameters passed to the noise functions
#     '''
#     cum_rates = cumsum(rates)
#     m = models[bisect(cum_rates, U(0,1))]
#     return m(spread, samples)


# n80b20_noise = partial(mix_models, [normal_noise, bimodal_noise], [.8,.2])
# n60b40_noise = partial(mix_models, [normal_noise, bimodal_noise], [.6,.4])
# n40b60_noise = partial(mix_models, [normal_noise, bimodal_noise], [.4,.6])
# n20b80_noise = partial(mix_models, [normal_noise, bimodal_noise], [.2,.8])

# equal_mix_noise = partial(mix_models, [normal_noise, bimodal_noise, \
#         uniform_noise, gumbel_noise], [.25]*4)
# mostly_normal_noise =  partial(mix_models, [normal_noise, bimodal_noise, \
#         gumbel_noise], [.8,.1,.1])

# noise_functions = filter(lambda k: k.endswith("_noise") and not \
#                     k.startswith("add_"), globals().keys())

# def rescale_payoffs(game, min_payoff=0, max_payoff=100):
#     '''
#     Rescale game's payoffs to be in the range [min_payoff, max_payoff].

#     Modifies game.values in-place.
#     '''
#     game.makeArrays()
#     min_val = game.values.min()
#     max_val = game.values.max()
#     game.values -= min_val
#     game.values *= (max_payoff - min_payoff)
#     game.values /= (max_val - min_val)
#     game.values += min_payoff

_PARSER = argparse.ArgumentParser(description='Generate random games')
_PARSER.add_argument('type',
                     choices=['uzs', 'usym', 'cg', 'leg', 'pmx', 'ind'],
                     help='''Type of random game to generate. uzs = uniform zero
                     sum.  usym = uniform symmetric. cg = congestion game. pmx
                     = polymatrix game. ind = independent game.''')
_PARSER.add_argument('arg', nargs='*', default=[],
                     help='Additional arguments for game generator function.')
_PARSER.add_argument('--count', '-c', type=int, default=1,
                     help='Number of random games to create. Default = 1')
_PARSER.add_argument('--noise', choices=['none', 'normal', 'gauss_mix'],
                     default='none', help='Noise function.')
_PARSER.add_argument('--noise_args', nargs='+', default=[],
                     help='Arguments to be passed to the noise function.')
_PARSER.add_argument('--output', '-o', metavar='output', default=sys.stdout,
                     type=argparse.FileType('w'),
                     help='Output destination; defaults to standard out')
_PARSER.add_argument('--indent', '-i', metavar='indent', type=int,
                     default=None,
                     help='Indent for json output; default = None')


def command(args, prog=''):
    _PARSER.prog = ('%s %s' % (_PARSER.prog, prog)).strip()
    args = _PARSER.parse_args(args)

    if args.type == 'uzs':
        assert len(args.arg) == 1, \
            'Must specify strategy count for uniform zero sum'
        game_func = lambda: zero_sum_game(*map(int, args.arg))
    elif args.type == 'usym':
        assert len(args.arg) == 2, \
            'Must specify player and strategy counts for uniform symmetric'
        game_func = lambda: symmetric_game(*map(int, args.arg))
    # elif args.type == 'cs':
    #     game_func = congestion_game
    #     assert len(args.game_args) == 3, 'game_args must specify player, '+\
    #                                 'facility, and required facility counts'
    # elif args.type == 'LEG':
    #     game_func = local_effect_game
    #     assert len(args.game_args) == 2, 'game_args must specify player and '+\
    #                                 'strategy counts'
    # elif args.type == 'PMX':
    #     game_func = polymatrix_game
    #     assert len(args.game_args) == 2, 'game_args must specify player and '+\
    #                                 'strategy counts'
    # elif args.type == 'ind':
    #     game_func = polymatrix_game
    #     assert len(args.game_args) == 2, 'game_args must specify player and '+\
    #                                 'strategy counts'
    else:
        raise ValueError('Unknown game type: %s' % args.type)

    games = [game_func() for _ in range(args.count)]

    # if args.noise == 'normal':
    #     assert len(args.noise_args) == 2, 'noise_args must specify stdev '+\
    #                                         'and sample count'
    #     noise_args = [float(args.noise_args[0]), int(args.noise_args[1])]
    #     games = map(lambda g: normal_noise(g, *noise_args), games)
    # elif args.noise == 'gauss_mix':
    #     assert len(args.noise_args) == 3, 'noise_args must specify max '+\
    #                                 'stdev, sample count, and number of modes'
    #     noise_args = [float(args.noise_args[0]), int(args.noise_args[1]), \
    #                     int(args.noise_args[2])]
    #     games = map(lambda g: gaussian_mixture_noise(g, *noise_args), games)

    json.dump(games, args.output, default=lambda x: x.to_json(),
              indent=args.indent)
    args.output.write('\n')
