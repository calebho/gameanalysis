#! /usr/bin/env python2.7

import numpy as np
from numpy.random import multinomial
from random import sample
from os import listdir as ls, mkdir
from os.path import join, exists, isdir
from argparse import ArgumentParser
import cPickle
import json

# import GaussianProcess but don't crash if it wasn't loaded
import warnings
warnings.formatwarning = lambda msg, *args: "warning: " + str(msg) + "\n"
try:
	from sklearn.gaussian_process import GaussianProcess
	from sklearn.grid_search import GridSearchCV
except ImportError:
	warnings.warn("sklearn.gaussian_process is required for game learning.")

from Reductions import HR_profiles, DPR_profiles, full_prof_DPR, DPR
import RoleSymmetricGame as RSG
from Nash import mixed_nash
from BasicFunctions import average, nCr, leading_zeros
from HashableClasses import h_array
from ActionGraphGame import LEG_to_AGG
from GameIO import to_JSON_str, read
from itertools import combinations_with_replacement as CwR, permutations

def GP_learn(game, cross_validate=False):
	"""
	Create a GP regression for each role and strategy.

	Parameters:
	game:			RoleSymmetricGame.SampleGame object with enough data to
					estimate payoff functions.
	cross_validate:	If set to True, cross-validation will be used to select
					parameters of the GPs.
	"""
	#X[r][s] stores the vectorization of each profile in which some players in
	#role r select strategy s. Profiles are listed in the same order as in the
	#input game. Y[r][s] stores corresponding payoff values in the same order.
	#Yd (d=diff) stores the difference from the average payoff. Ywd (w=weighted)
	#stores difference from expected payoff for a random agent. Ym (m=mean)
	#stores average payoffs. Ywm stores expected payoff for a random agent.
	X = {
		"profiles":[],
		"samples":{r:{s:[] for s in game.strategies[r]} for r in game.roles}
	}
	Y = {
		"Y":{r:{s:[] for s in game.strategies[r]} for r in game.roles},
		"Yd":{r:{s:[] for s in game.strategies[r]} for r in game.roles},
		"Ywd":{r:{s:[] for s in game.strategies[r]} for r in game.roles},
		"Ym":{r:[] for r in game.roles},
		"Ywm":{r:[] for r in game.roles}
	}
	for p in range(len(game)):#fill X and Y
		prof = game.counts[p]
		samples = game.sample_values[p]
		x = np.array(prof2vec(game, prof), dtype=float)[None].T
		x = np.tile(x, (1,1,samples.shape[-1]))
		x += np.random.normal(0,1e-9, x.shape)
		ym = samples.mean(1).mean(1)
		ywm = ((samples * x).sum(1) / x.sum(1)).mean(1)
		X["profiles"].append(x[0,:,0])
		for r,role in enumerate(game.roles):
			Y["Ym"][role].append(ym[r])
			Y["Ywm"][role].append(ywm[r])
			for s,strat in enumerate(game.strategies[role]):
				if prof[r][s] > 0:
					y = samples[r,s]
					Y["Y"][role][strat].extend(y)
					Y["Yd"][role][strat].extend(y - ym)
					Y["Ywd"][role][strat].extend(y - ywm)
					for i in range(y.size):
						X["samples"][role][strat].append(x[0,:,i])

	#GPs stores the learned GP for each role and strategy
	GPs = {y:{} for y in Y}
	for role in game.roles:
		for y in ["Ym", "Ywm"]:
			GPs[y][role] = train_GP(X["profiles"], Y[y][role], cross_validate)
		for y in ["Y", "Yd", "Ywd"]:
			GPs[y][role] = {}
			for strat in game.strategies[role]:
				GPs[y][role][strat] = train_GP(X["samples"][role][strat], \
										Y[y][role][strat], cross_validate)
	return GPs


def train_GP(X, Y, cross_validate=False):
	if cross_validate:
		gp = GaussianProcess(storage_mode='light', thetaL=1e-4, thetaU=1e9, \
							normalize=True)
		params = {
				"corr":["absolute_exponential","squared_exponential",
						"cubic","linear"],
				"nugget":[1e-10,1e-6,1e-4,1e-2,1e0,1e2,1e4]
		}
		cv = GridSearchCV(gp, params)
		cv.fit(X, Y)
		return cv.best_estimator_
	else:
		gp = GaussianProcess(storage_mode='light', corr="cubic", nugget=1)
		gp.fit(X, Y)
		return gp


def GP_DPR(game, players, GPs):
	"""
	Estimate equilibria of a DPR game from GP regression models.
	"""
	if len(game.roles) == 1 and isinstance(players, int):
		players = {game.roles[0]:players}
	elif isinstance(players, list):
		players = dict(zip(game.roles, players))

	learned_game = RSG.Game(game.roles, players, game.strategies)
	for prof in learned_game.allProfiles():
		role_payoffs = {}
		for role in game.roles:
			role_payoffs[role] = []
			for strat,count in prof[role].iteritems():
				full_prof = full_prof_DPR(prof, role, strat, game.players)
				prof_x = prof2vec(game, full_prof)
				prof_y = GPs[role][strat].predict(prof_x)
				role_payoffs[role].append(RSG.PayoffData(strat, count, prof_y))
		learned_game.addProfile(role_payoffs)

	return learned_game


def GP_EVs(GPs, mix, players, samples=1000):
	"""
	Mimics game.ExpectedValues via sampling from the GPs.

	WARNING: assumes that the game is symmetric!
	"""
	EVs = np.zeros(mix.shape)
	for r,role in enumerate(sorted(GPs)):
		for s,strat in enumerate(sorted(GPs[role])):
			profs = multinomial(players, mix[0], samples)
			EVs[r,s] = GPs[role][strat].predict(profs).mean()
	return EVs


def GP_point(GPs, mix, players):
	"""
	Mimics game.ExpectedValues by returning the GPs' value estimates for the ML
	profile under mix.

	WARNING: assumes that the game is symmetric!
	"""
	prof = mix * players
	EVs = np.zeros(mix.shape)
	for r,role in enumerate(sorted(GPs)):
		for s,strat in enumerate(sorted(GPs[role])):
			EVs[r,s] = GPs[role][strat].predict(prof)
	return EVs


def GP_RD(game, GPs, regret_thresh=1e-2, dist_thresh=1e-3, \
			random_restarts=0, at_least_one=False, iters=1000, \
			converge_thresh=1e-6, ev_samples=1000, EV_func=GP_EVs):
	"""
	Estimate equilibria with RD using from GP regression models.
	"""
	candidates = []
	regrets = {}
	players = game.players.values()[0] # assumes game is symmetric
	for mix in game.biasedMixtures() + [game.uniformMixture() ]+ \
			[game.randomMixture() for _ in range(random_restarts)]:
		for _ in range(iters):
			old_mix = mix
			EVs = EV_func(GPs, mix, players, ev_samples)
			mix = (EVs - game.minPayoffs + RSG.tiny) * mix
			mix = mix / mix.sum(1).reshape(mix.shape[0],1)
			if np.linalg.norm(mix - old_mix) <= converge_thresh:
				break
		mix[mix < 0] = 0
		candidates.append(h_array(mix))
		EVs = EV_func(GPs, mix, players, ev_samples)
		regrets[h_array(mix)] = (EVs.max(1) - (EVs * mix).sum(1)).max()

	candidates.sort(key=regrets.get)
	equilibria = []
	for c in filter(lambda c: regrets[c] < regret_thresh, candidates):
		if all(np.linalg.norm(e - c, 2) >= dist_thresh for e in equilibria):
			equilibria.append(c)
	if len(equilibria) == 0 and at_least_one:
		return [min(candidates, key=regrets.get)]
	return equilibria


def prof2vec(game, prof):
	"""
	Turns a profile (represented as Profile object or count array) into a
	1-D vector of strategy counts.
	"""
	if isinstance(prof, RSG.Profile):
		prof = game.toArray(prof)
	vec = []
	for r in range(len(game.roles)):
		vec.extend(prof[r][:game.numStrategies[r]])
	return vec


def sample_at_reduction(AGG, samples, reduction_profiles, players):
	"""
	AGG:		ActionGraphGame.Noisy_AGG object
	samples:	total number of samples to collect; will be spread as evenly as
				possibl across generated profiles; profiles that get sampled one
				extra time are chosen uniformly at random
	reduction_profiles:
				function that takes a number of players and generates a set of
				profiles; intended settings: DPR_profiles, HR_profiles
	players:	number of players in the reduced game; passed as an argument to
				reduction_profiles

	RETURNS:	RoleSymmetricGame.SampleGame object with samples drawn from AGG;
				samples are allocated as evenly as possible to profiles
				generated by reduction_profiles
	"""
	g = RSG.SampleGame(["All"], {"All":AGG.players}, {"All":AGG.strategies})
	profiles = reduction_profiles(g, {"All":players})
	s = samples/len(profiles)
	extras = sample(profiles, samples - s*len(profiles))
	counts = {p:(s+1 if p in extras else s) for p in profiles}
	for prof,count in counts.items():
		values = AGG.sample(prof["All"], count)
		g.addProfile({"All":[RSG.PayoffData(s,c,values[s]) for \
								s,c in prof["All"].iteritems()]})
	return g


def sample_near_reduction(AGG, samples, reduction_profiles, players):
	"""
	AGG:		ActionGraphGame.Noisy_AGG object
	samples:	total number of samples to collect; will be spread as evenly as
				possibl across generated profiles; profiles that get sampled one
				extra time are chosen uniformly at random
	reduction_profiles:
				function that takes a number of players and generates a set of
				profiles; intended settings: DPR_profiles, HR_profiles
	players:	number of players in the reduced game; passed as an argument to
				reduction_profiles

	RETURNS:	RoleSymmetricGame.SampleGame object with samples drawn from AGG;
				samples are allocated near near the profiles generated by
				reduction_profiles by treating the fraction of players in a
				profile playing each strategy as a distribution and drawing N
				samples from it; the resulting N-player profile gets sampled
				from the noisy AGG.
	"""
	g = RSG.SampleGame(["All"], {"All":AGG.players}, {"All":AGG.strategies})
	profiles = reduction_profiles(g, {"All":players})
	s = samples/len(profiles)
	extras = sample(profiles, samples - s*len(profiles))
	counts = {p:(s+1 if p in extras else s) for p in profiles}
	random_profiles = {}
	for prof,count in counts.items():
		dist = np.array([prof["All"].get(s,0) for s in AGG.strategies],
														dtype=float)
		dist /= float(AGG.players)
		for _ in range(count):
			rp = np.random.multinomial(AGG.players, dist)
			rp = filter(lambda p:p[1], zip(AGG.strategies,rp))
			rp = RSG.Profile({"All":dict(rp)})
			random_profiles[rp] = random_profiles.get(rp,0) + 1

	for prof,count in random_profiles.iteritems():
		values = AGG.sample(prof["All"], count)
		g.addProfile({"All":[RSG.PayoffData(s,c,values[s]) for \
								s,c in prof["All"].iteritems()]})

	return g


def sample_games(folder, players=[2], samples=[100], reductions=["HR","DPR"]):
	game_types = []
	if "HR" in reductions:
		game_types += ["at_HR", "near_HR"]
	if "DPR" in reductions:
		game_types += ["at_DPR", "near_DPR"]
	AGG_names = filter(lambda s: s.endswith(".json"), ls(folder))
	for AGG_name in sorted(AGG_names):
		with open(join(folder, AGG_name)) as f:
			AGG = LEG_to_AGG(json.load(f))
		for p in players:
			for n in samples:
				for game_type in game_types:
					sub_folder = game_type + "_"+str(p)+"p"+str(n)+"n"
					if exists(join(folder, sub_folder, AGG_name)):
						continue
					if game_type=="at_DPR":
						game = sample_at_reduction(AGG, n, DPR_profiles, p)
					elif game_type=="at_HR":
						game = sample_at_reduction(AGG, n, HR_profiles, p)
					elif game_type=="near_DPR":
						game = sample_near_reduction(AGG, n, DPR_profiles, p)
					elif game_type=="near_HR":
						game = sample_near_reduction(AGG, n, HR_profiles, p)
					write_game(game, folder, sub_folder, AGG_name)
					del game


def learn_games(folder, cross_validate=False):
	"""
	Goes through sub-folders of folder (which should have all been created by
	sample_games) and runs GP_learn on each sample game; creates a pkl file
	corresponding to each input json file
	"""
	for sub_folder in filter(lambda s: isdir(join(folder, s)), ls(folder)):
		for game_name in filter(lambda s: s.endswith(".json"), ls(folder)):
			GPs_name = join(folder, sub_folder, game_name[:-5] + "_GPs.pkl")
			if exists(GPs_name):
				continue
			game = read(join(folder, sub_folder, game_name))
			GPs = GP_learn(game, cross_validate)
			with open(GPs_name, "w") as f:
				cPickle.dump(GPs, f)


def write_game(game, base_folder, sub_folder, game_name):
	game_folder = join(base_folder, sub_folder)
	if not exists(game_folder):
		mkdir(game_folder)
	game_file = join(game_folder, game_name)
	with open(game_file, "w") as f:
		f.write(to_JSON_str(game))


def regrets_experiment(folder, skip_DPR=False):
	"""
	Takes a folder filled with AGGs, plus the sub-folders for DPR and GPs
	created by the learn_AGGs() and computes equilibria in each small game,
	then outputs those equilibria and their regrets in the corresponding AGGs.
	"""
	if not skip_DPR:
		DPR_eq_file = join(folder, "DPR_eq.json")
		DPR_regrets_file = join(folder, "DPR_regrets.json")
	GP_eq_file = join(folder, "GP_eq.json")
	GP_regrets_file = join(folder, "GP_regrets.json")
	if exists(GP_eq_file):
		if not skip_DPR:
			DPR_eq = read(DPR_eq_file)
			DPR_regrets = read(DPR_regrets_file)
		GP_eq = read(GP_eq_file)
		GP_regrets = read(GP_regrets_file)
	else:
		if not skip_DPR:
			DPR_eq = []
			DPR_regrets = []
		GP_eq = []
		GP_regrets = []

	for i, (AGG_fn, DPR_fn, samples_fn, GPs_fn) in \
					enumerate(learned_files(folder)):
		if i < len(GP_eq):
			continue
		with open(AGG_fn) as f:
			AGG = LEG_to_AGG(json.load(f))
		if not skip_DPR:
			DPR_game = read(DPR_fn)
		samples_game = read(samples_fn)
		with open(GPs_fn) as f:
			GPs = cPickle.load(f)

		if not skip_DPR:
			eq = mixed_nash(DPR_game, at_least_one=True)
			DPR_eq.append(map(samples_game.toProfile, eq))
			DPR_regrets.append([AGG.regret(e[0]) for e in eq])
		try:
			eq = GP_RD(samples_game, GPs, at_least_one=True)
			GP_eq.append(map(samples_game.toProfile, eq))
			GP_regrets.append([AGG.regret(e[0]) for e in eq])
		except AttributeError:
			GP_eq.append([])
			GP_regrets.append([])

		if not skip_DPR:
			with open(DPR_eq_file, "w") as f:
				f.write(to_JSON_str(DPR_eq))
			with open(join(folder, "DPR_regrets.json"), "w") as f:
				f.write(to_JSON_str(DPR_regrets))
		with open(join(folder, "GP_eq.json"), "w") as f:
			f.write(to_JSON_str(GP_eq))
		with open(join(folder, "GP_regrets.json"), "w") as f:
			f.write(to_JSON_str(GP_regrets))


def EVs_experiment(folder):
	"""
	Takes a folder filled with AGGs, plus the sub-folders for DPR and GPs
	created by learn_AGGs(), and computes expected values for a number of
	mixed strategies in the full game, in the DPR game and using several
	different methods to extract EVs from the GPs.
	"""
	DPR_game = read(join(folder, "DPR", ls(join(folder, "DPR"))[0]))
	mixtures = [DPR_game.uniformMixture()] +\
				mixture_grid(len(DPR_game.strategies["All"]))
	if not exists(join(folder, "mixtures.json")):
		with open(join(folder, "mixtures.json"), "w") as f:
			f.write(to_JSON_str(mixtures))
	out_file = join(folder, "mixture_values.csv")
	if not exists(out_file):
		last_game = 0
		last_mix = -1
		with open(out_file, "w") as f:
			f.write("game,mixture,")
			f.write(",".join("AGG EV "+s for s in \
							DPR_game.strategies["All"]) + ",")
			f.write(",".join("DPR EV "+s for s in \
							DPR_game.strategies["All"]) + ",")
			f.write(",".join("GP_sample EV " + s for s in \
							DPR_game.strategies["All"]) + ",")
			f.write(",".join("GP_point value " + s for s in \
							DPR_game.strategies["All"]) + "\n")
	else:
		with open(out_file) as f:
			last_line = [l for l in f][-1].split(",")
		last_game = int(last_line[0])
		last_mix = int(last_line[1])

	for i, (AGG_fn, DPR_fn, samples_fn, GPs_fn) in \
								enumerate(learned_files(folder)):
		if i < last_game:
			continue
		with open(AGG_fn) as f:
			AGG = LEG_to_AGG(json.load(f))
		DPR_game = read(DPR_fn)
		samples_game = read(samples_fn)
		with open(GPs_fn) as f:
			GPs = cPickle.load(f)
		for j,mix in enumerate(mixtures):
			if i == last_game and j <= last_mix:
				continue
			line = [i,j]
			line.extend(AGG.expectedValues(mix[0]))
			line.extend(DPR_game.expectedValues(mix)[0])
			line.extend(GP_EVs(GPs, mix, AGG.players)[0])
			line.extend(GP_point(GPs, mix, AGG.players)[0])
			with open(out_file, "a") as f:
				f.write(",".join(map(str, line)) + "\n")


def learned_files(folder):
	for fn in sorted(filter(lambda s: s.endswith(".json"), ls(folder))):
		AGG_fn = join(folder, fn)
		DPR_fn = join(folder, "DPR", fn)
		HR_fn = join(folder, "HR", fn)
		DPR_samples_fn = join(folder, "DPR_samples", fn)
		HR_samples_fn = join(folder, "HR_samples", fn)
		GPs_fn = join(folder, "GPs", fn[:-4] + "pkl")
		yield AGG_fn, DPR_fn, samples_fn, GPs_fn


def mixture_grid(S, points=5, digits=2):
	"""
	Generate all choose(S, points) grid points in the simplex.

	There must be a better way to do this!
	"""
	a = np.linspace(0, 1, points)
	mixtures = set()
	for p in filter(lambda x: abs(sum(x) - 1) < .5/points, CwR(a,S)):
		for m in permutations(map(lambda x: round(x, digits), p)):
			mixtures.add(h_array([m]))
	return sorted(mixtures)


def main():
	p = ArgumentParser(description="Perform game-learning experiments on " +\
									"a set of action graph games.")
	p.add_argument("mode", type=str, choices=["games","learn","regrets","EVs"],
				help="games mode creates at_DPR, at_HR, near_DPR, and near_HR "+
				"directories. It requires players and samples arguments "+
				"(other modes don't). learn mode creates _GPs.pkl files. "+
				"regrets mode computes equilibria and regrets in all games. "+
				"EVs mode computes expected values of many mixtures in all "+
				"games.")
	p.add_argument("folder", type=str, help="Folder containing pickled AGGs.")
	p.add_argument("-p", type=int, nargs="*", default=[], help=\
				"Player sizes of reduced games to try. Only for 'games' mode.")
	p.add_argument("-n", type=int, nargs="*", default=[], help=\
				"Numbers of samples to try. Only for 'games' mode.")
	p.add_argument("--CV", action="store_true", help="Perform cross-validation")
	p.add_argument("--skip", type=str, choices=["HR", "DPR", ""], default="",
				help="Don't generate games of the specified reduction type.")
	a = p.parse_args()
	if a.mode == "games":
		assert a.p
		assert a.n
		reductions = ["HR", "DPR"]
		if a.skip in reductions:
			reductions.remove(a.skip)
		sample_games(a.folder, a.p, a.n, reductions)
	elif a.mode == "learn":
		learn_games(a.folder, a.CV)
	elif a.mode == "regrets":
		raise NotImplementedError("TODO: update this")
#		regrets_experiment(a.folder, a.skip_DPR)
	elif a.mode =="EVs":
		raise NotImplementedError("TODO: update this")
#		EVs_experiment(a.folder)


if __name__ == "__main__":
	main()
