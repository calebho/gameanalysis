#!/usr/bin/env python
import argparse
import time
import itertools
from Queue import PriorityQueue as priorityqueue

import egtaonlineapi as egta
import analysis
import containers

PARSER = argparse.ArgumentParser(description='Quiesce a generic scheduler on egtaonline.')
PARSER.add_argument('-a', '--auth', metavar='auth_token', required=True,
                    help='An authorization token to allow access to egtaonline.')
PARSER.add_argument('-s', '--scheduler', metavar='scheduler', required=True,
                    help='The name or id of the scheduler to quiesce.')
PARSER.add_argument('-g', '--game', metavar='game_id', type=int, default=None,
                    help='''The id of the game used to indicate how to schedule.
                    If not provided, this will try and determine the game, but may fail.
                    ''')
PARSER.add_argument('-n', '--max-profiles', metavar='num-profiles', type=int,
                    default=10000, help='''Maximum number of profiles to ever have
                    scheduled at a time. Defaults to 10000.''')
PARSER.add_argument('-t', '--sleep-time', metavar='delta', type=int, default=600,
                    help='''Time to wait in seconds between checking egtaonline for
                    job completion. Defaults to 300.''')

class quieser(object):
    """Class to manage quiesing of a scheduler"""
    # pylint: disable=too-many-instance-attributes

    # TODO keep track up most recent set of data, and have schedule update it
    # after it finishes blocking
    def __init__(self, scheduler, auth_token, game=None, max_profiles=10000,
                 sleep_time=300):
        # pylint: disable=too-many-arguments
        # Get api and access to standard objects
        self.api = egta.egtaonline(auth_token)
        self.scheduler = self.api.get_scheduler(scheduler, verbose=True)
        self.simulator = self.api.get_simulator(self.scheduler.simulator_id)
        sim_inst_id = self.api.get_scheduler(self.scheduler.id).simulator_instance_id
        if game is None:
            # Hack to find game with same simulator instance id
            game = analysis.only(g for g in self.api.get_games()
                                 if g.simulator_instance_id == sim_inst_id).id
            self.game = self.api.get_game(game, granularity='summary')

        # Set other game information
        self.role_counts = {r['name']: r['count'] for r in self.game.roles}
        self.full_game = analysis.subgame(
            (r['name'], set(r['strategies'])) for r in self.game.roles)

        # Set useful variables
        self.obs_count = self.scheduler.default_observation_requirement
        self.max_profiles = max_profiles
        self.sleep_time = sleep_time

    def quiesce(self):
        """Starts the process of quiescing

        No writes happen until this method is called

        """
        # Keeps a set of explored subgames, a queue of necessary subgames to
        # explore, and a queue of optional subgames to explore if no equilibria
        # have been found. The queues use the negative regret of the deviation
        # that generated them as a key to prompt exploration.

        # pylint: disable=star-args

        # Set initial subgames
        #
        # TODO Initial subgames might not want to include all pure profiles
        necessary = containers.priorityqueue(
            (0, analysis.subgame(rs)) for rs in itertools.product(
                *([(r, {s}) for s in ss] for r, ss in self.full_game.iteritems())))
        backup = containers.priorityqueue()
        explored = analysis.subgame_set()
        confirmed_equilibria = set()

        # TODO could be changed to allow multiple stopping conditions
        # TODO could be changed to be parallel
        while not confirmed_equilibria or necessary:
            # Get next subgame to explore
            _, subgame = necessary.pop() if necessary else backup.pop()
            print "\nExploring subgame:\t", subgame
            if not explored.add(subgame):  # already explored
                print "***Already Explored Subgame***"
                continue

            # Schedule subgame
            self.schedule_profiles(subgame.get_subgame_profiles(self.role_counts))
            data = self.get_data()

            # Find equilibria in the subgame
            equilibria = data.equilibria(eq_subgame=subgame)
            for eq in equilibria:
                print "Found equilibrium:\t", eq

            # Schedule all deviations from found equilibria
            self.schedule_profiles(itertools.chain.from_iterable(
                eq.support().get_deviation_profiles(self.full_game, self.role_counts)
                for eq in equilibria))
            data = self.get_data()

            # Confirm equilibria and add beneficial deviating subgames to
            # future exploration
            for equm in equilibria:
                responses = sorted(data.responses(equm), reverse=True)
                print "Responses:\t", responses
                if not responses:  # Found equilibrium
                    confirmed_equilibria.add(equm)
                    print "!!!Confirmed!!!:\t", equm
                else: # Queue up next subgames
                    supp = equm.support()
                    b_reg, b_role, b_strat = responses[0]
                    # Best response becomes necessary to explore
                    necessary.append((-b_reg, supp.with_deviation(b_role, b_strat)))
                    # All others become backups if we run out without finding one
                    for reg, role, strat in responses[1:]:
                        backup.append((-reg, supp.with_deviation(role, strat)))

        print "\nConfirmed Equilibria:"
        for i, eq in enumerate(confirmed_equilibria):
            print (i + 1), ")", eq

    def schedule_profiles(self, profiles):
        """Schedules an interable of profiles

        Makes sure not to exceed max_profiles, and to only query the state of
        the simulator every sleep_time seconds when blocking on simulation
        execution

        """
        # Number of running profiles
        #
        # This is an overestimate because checking is expensive
        count = self.scheduler.num_running_profiles()
        for prof in profiles:
            # First, we check / block until we can schedule another profile

            # Sometimes scheduled profiles already exist, and so even though we
            # increment our count, the global count doesn't increase. This
            # stops up from waiting a long time if we hit this threshold by
            # accident
            if count >= self.max_profiles:
                count = self.scheduler.num_running_profiles()
            # Wait until we can schedule more profiles
            while count >= self.max_profiles:
                time.sleep(self.sleep_time)
                count = self.scheduler.num_running_profiles()

            count += 1
            self.api.add_profile(self.scheduler.id, prof, self.obs_count)

        # Like before, but we block until everything is finished
        if count > 0:
            count = self.scheduler.num_running_profiles()
        while count > 0:
            time.sleep(self.sleep_time)
            count = self.scheduler.num_running_profiles()

    def get_data(self):
        """Gets current game data"""
        return analysis.game_data(self.api.get_game(self.game.id, 'summary'))

if __name__ == '__main__':
    args = PARSER.parse_args()

    quies = quieser(
        int(args.scheduler) if args.scheduler.isdigit() else args.scheduler,
        args.auth,
        args.game and (int(args.game) if args.game.isdigit() else args.game),
        args.max_profiles,
        args.sleep_time)

    quies.quiesce()
    print '[[ done ]]'
