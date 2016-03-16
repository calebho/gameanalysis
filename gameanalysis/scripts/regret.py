"""Script for calculating regrets, deviations gains, and social welfare"""
import argparse
import json
from collections import abc

from gameanalysis import regret
from gameanalysis import rsgame


def _is_pure_profile(prof):
    """Returns true of the profile is pure"""
    # For an asymmetric game, this will always return false, but then it
    # shouldn't be an issue, because pure strategy regret will be more
    # informative.
    return any(sum(strats.values()) > 1.5 for strats in prof.values())


_TYPE = {
    'regret': lambda game, prof: (
        regret.pure_strategy_regret(game, prof)
        if _is_pure_profile(prof)
        else regret.mixture_regret(game, prof)),
    'gains': lambda game, prof: (
        regret.pure_strategy_deviation_gains(game, prof)
        if _is_pure_profile(prof)
        else regret.mixture_deviation_gains(game, prof)),
}
_TYPE['ne'] = _TYPE['gains']  # These are the same


def update_parser(parser):
    parser.description = """Compute regret in input game of specified
profiles."""
    parser.add_argument('profiles', metavar='<profile-file>',
                        type=argparse.FileType('r'), help="""File with profiles
                        from input games for which regrets should be
                        calculated. This file needs to be a json list of
                        profiles""")
    parser.add_argument('-t', '--type', metavar='type', default='regret',
                        choices=_TYPE, help="""What to return. regret: returns
                        the the regret of the profile; gains: returns a json
                        object of the deviators gains for every deviation; ne:
                        return the "nash equilibrium regrets", these are
                        identical to gains. (default: %(default)s)""")


def main(args):
    game = rsgame.Game.from_json(json.load(args.input))
    profiles = json.load(args.profiles)
    if isinstance(profiles, abc.Mapping):
        profiles = [profiles]
    prof_func = _TYPE[args.type]

    regrets = [prof_func(game, prof) for prof in profiles]

    json.dump(regrets, args.output, default=lambda x: x.to_json())
    args.output.write('\n')
