from RoleSymmetricGame import Game, Profile, PayoffData, is_symmetric

def hierarchical_reduction(game, players={}):
	players = deduce_players(game, players)
	HR_game = type(game)(game.roles, players, game.strategies)
	for reduced_profile in HR_game.allProfiles():
		try:
			full_profile = Profile({r:full_prof_sym(reduced_profile[r], \
					game.players[r]) for r in game.roles})
			HR_game.addProfile({r:[PayoffData(s, reduced_profile[r][s], \
					game.getPayoffData(full_profile, r, s)) for s in \
					full_profile[r]] for r in full_profile})
		except KeyError:
			continue
	return HR_game


HR = hierarchical_reduction


def full_prof_sym(HR_profile, N):
	"""
	Returns the symmetric full game profile corresponding to the given
	symmetric reduced game profile under hierarchical reduction.

	In the event that N isn't divisible by n, we first assign by rounding
	error and break ties in favor of more-played strategies. The final
	tie-breaker is alphabetical order.
	"""
	if N < 2:
		return HR_profile
	n = sum(HR_profile.values())
	full_profile = {s : c * N / n  for s,c in HR_profile.items()}
	if sum(full_profile.values()) == N:
		return full_profile

	#deal with non-divisible strategy counts
	rounding_error = {s : float(c * N) / n - full_profile[s] for \
						s,c in HR_profile.items()}
	strat_order = sorted(HR_profile.keys())
	strat_order.sort(key=HR_profile.get, reverse=True)
	strat_order.sort(key=rounding_error.get, reverse=True)
	for s in strat_order[:N - sum(full_profile.values())]:
		full_profile[s] += 1
	return full_profile


def full_prof_DPR(DPR_profile, role, strat, players):
	"""
	Returns the full game profile whose payoff determines that of strat
	in the reduced game profile.
	"""
	full_prof = {}
	for r in DPR_profile:
		if r == role:
			opp_prof = DPR_profile.asDict()[r]
			opp_prof[strat] -= 1
			full_prof[r] = full_prof_sym(opp_prof, players[r] - 1)
			full_prof[r][strat] += 1
		else:
			full_prof[r] = full_prof_sym(DPR_profile[r], players[r])
	return Profile(full_prof)


def full_prof_HR(HR_profile, players):
	"""
	Returns the full game profile whose payoff determines that of strat
	in the reduced game profile.
	"""
	return Profile({r:full_prof_sym(HR_profile[r], players[r]) for r in \
															HR_profile})


def deviation_preserving_reduction(game, players={}):
	players = deduce_players(game, players)

	#it's often faster to go through all of the full-game profiles
	DPR_game = type(game)(game.roles, players, game.strategies)
	if len(game) <= DPR_game.size and is_symmetric(game):
		DPR_prof_data = {}
		divisible = True
		for full_prof in game.knownProfiles():
			try:
				rp, role, strat = dpr_profile(full_prof, players, game.players)
			except NotImplementedError:
				divisible = False
				break
			if rp not in DPR_prof_data:
				DPR_prof_data[rp] = {r:[] for r in game.roles}
			count = rp[role][strat]
			value = game.getPayoffData(full_prof, role, strat)
			DPR_prof_data[rp][role].append(PayoffData(strat,count,value))
		if divisible:
			for prof_data in DPR_prof_data.values():
				valid_profile = True
				for r,l in prof_data.items():
					if sum([d.count for d in l]) != players[r]:
						valid_profile = False
						break
				if valid_profile:
					DPR_game.addProfile(prof_data)
			return DPR_game

	#it's conceptually simpler to go through all of the reduced-game profiles
	for DPR_prof in DPR_game.allProfiles():
		try:
			role_payoffs = {}
			for r in game.roles:
				role_payoffs[r] = []
				for s in DPR_prof[r]:
					full_prof = full_prof_DPR(DPR_prof, r, s, game.players)
					role_payoffs[r].append(PayoffData(s,DPR_prof[r][s],\
							game.getPayoffData(full_prof, r, s)))
			DPR_game.addProfile(role_payoffs)
		except KeyError:
			continue
	return DPR_game


DPR = deviation_preserving_reduction


def dpr_profile(full_profile, reduced_players, full_players=None):
	"""
	Gives the DPR profile, role, and strategy that f_p's payoffs determine

	Providing full_players is optional, but saves some work.
	"""
	role = None
	strat = None
	if full_players == None:
		full_players = {r:sum(v.values()) for r,v in full_profile.items()}
	reduction_factors = {}
	for r in full_profile:
		if full_players[r] % reduced_players[r] == 0:
			reduction_factors[r] = full_players[r] / reduced_players[r]
		else:
			role = r
			reduction_factors[r] = (full_players[r]-1) / (reduced_players[r]-1)
	for s,c in full_profile[role].items():
		if c % reduction_factors[r] != 0:
			if strat != None:
				raise NotImplementedError("This function doesn't handle "+\
										"non-divisible player counts yet.")
			strat = s
	reduced_profile = {r:{} for r in reduced_players}
	for r in full_profile:
		for s,c in full_profile[role].items():
			if r == role and s == strat:
				reduced_profile[r][s] = (c-1) / reduction_factors[r] + 1
			else:
				reduced_profile[r][s] = c / reduction_factors[r]
	return Profile(reduced_profile), role, strat


def twins_reduction(game):
	players = {r:min(2,p) for r,p in game.players.items()}
	return DPR(game, players)


def DPR_profiles(game, players={}):
	"""Returns the profiles from game that contribute to the DPR game."""
	players = deduce_players(game, players)
	DPR_game = Game(game.roles, players, game.strategies)
	profiles = []
	for DPR_prof in DPR_game.allProfiles():
		for r in game.roles:
			for s in DPR_prof[r]:
				full_prof = full_prof_DPR(DPR_prof, r, s, game.players)
				profiles.append(full_prof)
	return profiles


def HR_profiles(game, players={}):
	"""Returns the profiles from game that contribute to the HR game."""
	players = deduce_players(game, players)
	HR_game = Game(game.roles, players, game.strategies)
	return [full_prof_HR(HR_prof, players) for HR_prof in HR_game.allProfiles()]


def deduce_players(game, players={}):
	if not players:
		players = {r:2 for r in game.roles}
	elif len(game.roles) == 1 and isinstance(players, int):
		players = {game.roles[0]:players}
	elif isinstance(players, list):
		players = dict(zip(game.roles, players))
	return players
