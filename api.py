from flask import Flask, jsonify, request
from flask_cors import CORS
from database import Database
import traceback

app = Flask(__name__)
CORS(app)

# Initialize DB with error handling
try:
    db = Database()
except Exception as e:
    print(f"❌ Failed to initialize database: {e}")
    db = None


@app.route('/', methods=['GET'])
def health_check():
    """Health check for Railway"""
    db_status = 'ok' if db else 'db_error'
    return jsonify({
        'status': db_status,
        'message': 'Spotted Leaderboard API is running',
        'database': 'connected' if db else 'disconnected'
    }), 200 if db else 503


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get full leaderboard with error handling"""
    if not db:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        scores = db.get_leaderboard(limit=100)
        return jsonify({
            'leaderboard': [
                {'user_id': user_id, 'user_name': user_name or 'Unknown', 'score': score}
                for user_id, user_name, score in scores
            ]
        })
    except Exception as e:
        print(f"❌ Error in get_leaderboard: {e}")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to fetch leaderboard', 'details': str(e)}), 500


@app.route('/api/score/<user_id>', methods=['GET'])
def get_user_score(user_id):
    """Get specific user's score with validation"""
    if not db:
        return jsonify({'error': 'Database not available'}), 503
    
    # Basic validation
    if not user_id or len(user_id) > 50:
        return jsonify({'error': 'Invalid user_id'}), 400
    
    try:
        score = db.get_score(user_id)
        return jsonify({
            'user_id': user_id,
            'score': score
        })
    except Exception as e:
        print(f"❌ Error in get_user_score: {e}")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to fetch score', 'details': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics with error handling"""
    if not db:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        scores = db.get_leaderboard(limit=1000)
        
        if not scores:
            return jsonify({
                'total_players': 0,
                'total_spots': 0,
                'top_spotter': None,
                'most_spotted': None
            })
        
        total_spots = sum(abs(score) for _, _, score in scores) // 2
        top_spotter = max(scores, key=lambda x: x[2]) if scores else None
        most_spotted = min(scores, key=lambda x: x[2]) if scores else None
        
        return jsonify({
            'total_players': len(scores),
            'total_spots': total_spots,
            'top_spotter': {'user_id': top_spotter[0], 'user_name': top_spotter[1] or 'Unknown', 'score': top_spotter[2]} if top_spotter else None,
            'most_spotted': {'user_id': most_spotted[0], 'user_name': most_spotted[1] or 'Unknown', 'score': most_spotted[2]} if most_spotted else None
        })
    except Exception as e:
        print(f"❌ Error in get_stats: {e}")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to fetch stats', 'details': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    print(f"❌ Internal server error: {e}")
    print(traceback.format_exc())
    return jsonify({'error': 'Internal server error'}), 500

