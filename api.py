from flask import Flask, jsonify
from flask_cors import CORS
from database import Database

app = Flask(__name__)
CORS(app)
db = Database()


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get full leaderboard"""
    scores = db.get_leaderboard(limit=100)
    return jsonify({
        'leaderboard': [
            {'user_id': user_id, 'user_name': user_name or 'Unknown', 'score': score}
            for user_id, user_name, score in scores
        ]
    })


@app.route('/api/score/<user_id>', methods=['GET'])
def get_user_score(user_id):
    """Get specific user's score"""
    score = db.get_score(user_id)
    return jsonify({
        'user_id': user_id,
        'score': score
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    scores = db.get_leaderboard(limit=1000)
    
    if not scores:
        return jsonify({
            'total_players': 0,
            'total_spots': 0,
            'top_spotter': None,
            'most_spotted': None
        })
    
    total_spots = sum(abs(score) for _, _, score in scores) // 2
    top_spotter = max(scores, key=lambda x: x[2])
    most_spotted = min(scores, key=lambda x: x[2])
    
    return jsonify({
        'total_players': len(scores),
        'total_spots': total_spots,
        'top_spotter': {'user_id': top_spotter[0], 'user_name': top_spotter[1] or 'Unknown', 'score': top_spotter[2]},
        'most_spotted': {'user_id': most_spotted[0], 'user_name': most_spotted[1] or 'Unknown', 'score': most_spotted[2]}
    })

