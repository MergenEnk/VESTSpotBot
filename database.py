import os
from typing import List, Tuple
from supabase import create_client, Client


class Database:
    def __init__(self):
        """Initialize Supabase client"""
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        print(f"✅ Connected to Supabase: {supabase_url}")
    
    def get_score(self, user_id: str) -> int:
        """Get the score for a specific user"""
        try:
            result = self.client.table('scores').select('score').eq('user_id', user_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]['score']
            return 0
        except Exception as e:
            print(f"Error getting score for {user_id}: {e}")
            return 0
    
    def add_point(self, user_id: str, points: int, user_name: str = None):
        """Add points to a user's score (can be negative)"""
        try:
            # First check if user exists
            existing = self.client.table('scores').select('*').eq('user_id', user_id).execute()
            
            if existing.data and len(existing.data) > 0:
                # User exists, update their score
                current_score = existing.data[0]['score']
                new_score = current_score + points
                update_data = {'score': new_score}
                if user_name:
                    update_data['user_name'] = user_name
                
                self.client.table('scores').update(update_data).eq('user_id', user_id).execute()
            else:
                # User doesn't exist, insert new record
                insert_data = {
                    'user_id': user_id,
                    'score': points,
                    'user_name': user_name
                }
                self.client.table('scores').insert(insert_data).execute()
        except Exception as e:
            print(f"Error adding points for {user_id}: {e}")
            raise
    
    def get_leaderboard(self, limit: int = 10) -> List[Tuple[str, str, int]]:
        """Get the top scores, ordered by score descending. Returns (user_id, user_name, score)"""
        try:
            result = self.client.table('scores').select('user_id, user_name, score').order('score', desc=True).limit(limit).execute()
            return [(row['user_id'], row['user_name'], row['score']) for row in result.data]
        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []
    
    def reset_scores(self):
        """Reset all scores to zero (use with caution!)"""
        try:
            self.client.table('scores').delete().neq('user_id', '').execute()
        except Exception as e:
            print(f"Error resetting scores: {e}")
            raise

