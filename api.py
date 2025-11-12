from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def health_check():
    """
    Health check endpoint for deployment platforms.
    The webapp fetches data directly from Supabase.
    """
    return jsonify({
        'status': 'ok',
        'service': 'Spotted Bot',
        'message': 'Bot is running. Webapp uses Supabase directly for data.'
    })

