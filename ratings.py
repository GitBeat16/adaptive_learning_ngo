# ratings.py

"""
Peer rating and feedback module
"""

# In-memory storage (can be replaced with DB later)
RATINGS = []


def submit_rating(peer_name, rating, feedback):
    """
    Stores peer rating and feedback
    """

    rating_entry = {
        "peer_name": peer_name,
        "rating": rating,
        "feedback": feedback
    }

    RATINGS.append(rating_entry)

    return True


def get_all_ratings():
    """
    Optional helper to fetch all ratings
    """
    return RATINGS
