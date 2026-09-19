"""
Markov chain model for prediction market pricing.
Computes win probability given current score, serve-point stats, and time remaining.
"""

import math
from functools import lru_cache
from scipy.stats import norm


class TennisMarkovModel:
    """
    Point-by-point tennis model.
    Input: serve-point win probability for each player
    Output: probability of winning game, set, match
    """
    
    def __init__(self, p_a, p_b):
        """
        p_a, p_b: probability player A (resp B) wins a point when serving
        """
        self.p_a = p_a
        self.p_b = p_b
    
    @lru_cache(maxsize=None)
    def game_win_prob(self, p_server):
        """
        P(server wins game) given p_server = P(server wins point).
        Uses exact Markov chain.
        """
        p_return = 1 - p_server
        deuce_prob = p_server * p_server / (p_server * p_server + p_return * p_return)
        
        # P(server wins | at deuce) is the repeated-game probability
        # Simplified: at deuce, it's p^2 / (p^2 + (1-p)^2)
        return (p_server ** 4 * (1 + 4*p_return + 10*p_return**2) +
                20 * p_server**3 * p_return**3 * deuce_prob)
    
    @lru_cache(maxsize=None)
    def game_from_state(self, p_server, a_pts, b_pts):
        """
        P(server wins game | server has a_pts, receiver has b_pts).
        """
        @lru_cache(maxsize=None)
        def f(a, b):
            if a >= 4 and a - b >= 2:
                return 1.0
            if b >= 4 and b - a >= 2:
                return 0.0
            if a >= 3 and b >= 3:
                if a == b:
                    return p_server * p_server / (p_server * p_server + (1-p_server)**2)
                if a > b:
                    return p_server + (1 - p_server) * f(3, 3)
                return p_server * f(3, 3)
            return p_server * f(a + 1, b) + (1 - p_server) * f(a, b + 1)
        
        return f(a_pts, b_pts)
    
    def set_win_prob(self, p_a_srv, p_b_srv, games_a, games_b, a_serving):
        """
        P(A wins set) given current game score and who's serving.
        """
        p_a_game = self.game_win_prob(p_a_srv)
        p_b_game = self.game_win_prob(p_b_srv)
        
        @lru_cache(maxsize=None)
        def f(ga, gb, a_serves):
            if ga >= 6 and ga - gb >= 2:
                return 1.0
            if gb >= 6 and gb - ga >= 2:
                return 0.0
            if ga == 6 and gb == 6:
                # Tiebreak: rough approximation
                return p_a_srv if a_serves else 1 - p_b_srv
            
            pw = p_a_game if a_serves else 1 - p_b_game
            return pw * f(ga + 1, gb, not a_serves) + (1 - pw) * f(ga, gb + 1, not a_serves)
        
        return f(games_a, games_b, a_serving)
    
    def match_win_prob(self, p_a_srv, p_b_srv, best_of_3=True):
        """
        P(A wins match | best-of-3 or best-of-5).
        """
        set_a = self.set_win_prob(p_a_srv, p_b_srv, 0, 0, True)
        set_b = self.set_win_prob(p_a_srv, p_b_srv, 0, 0, False)
        avg_set = (set_a + set_b) / 2
        
        if best_of_3:
            return avg_set ** 2 * (3 - 2 * avg_set)  # P(win 2 of 3)
        else:
            return avg_set ** 3 * (10 - 15 * avg_set + 6 * avg_set ** 2)  # P(win 3 of 5)


class CryptoVolatilityModel:
    """
    Simple model for crypto 15-minute windows.
    Predicts probability of finishing above/below a target price.
    """
    
    def __init__(self, volatility_pct_per_15min=1.5):
        """
        volatility_pct_per_15min: typical move as % of price, e.g. 1.5%
        """
        self.vol = volatility_pct_per_15min / 100.0
    
    def prob_above_target(self, current_price, target_price, minutes_left):
        """
        P(price finishes above target) given current price and time left.
        Uses lognormal model scaled by sqrt(time).
        """
        if minutes_left <= 0:
            return 1.0 if current_price > target_price else 0.0
        
        # Typical move over remaining time
        time_fraction = minutes_left / 15.0
        sigma = self.vol * math.sqrt(time_fraction)
        
        # Log-return to target
        log_return = math.log(target_price / current_price)
        
        # Probability (normal approximation)
        z = log_return / (sigma * current_price + 1e-9)
        return norm.cdf(z)


class BayesianCalibrator:
    """
    Blends prior belief with observed data.
    Used to update serve-point probabilities as match progresses.
    """
    
    @staticmethod
    def blend_probabilities(prior, observed, points_count, prior_strength=100):
        """
        Bayesian update: blend prior with observed data.
        
        prior: prior probability (0-1)
        observed: empirical probability from live data (0-1)
        points_count: number of observations (e.g., serve points played)
        prior_strength: how many "pseudo-observations" the prior represents
        
        Returns: blended probability
        """
        prior_weight = prior_strength / (prior_strength + points_count)
        return prior_weight * prior + (1 - prior_weight) * observed
    
    @staticmethod
    def estimate_serve_prob(points_won, total_points):
        """Convert win/total into probability with Laplace smoothing."""
        return (points_won + 1) / (total_points + 2)
