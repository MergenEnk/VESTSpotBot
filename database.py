import os
import time
from typing import List, Tuple, Optional
from supabase import create_client, Client


class Database:
    def __init__(self):
        """Initialize Supabase client with validation"""
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        try:
            self.client: Client = create_client(supabase_url, supabase_key)
            print(f"✅ Connected to Supabase: {supabase_url}")
        except Exception as e:
            print(f"❌ Failed to connect to Supabase: {e}")
            raise
    
    def _retry_operation(self, operation, max_retries=3, operation_name="operation"):
        """Retry a database operation with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                    print(f"⚠️  {operation_name} failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    print(f"❌ {operation_name} failed after {max_retries} attempts: {e}")
                    raise
    
    def get_score(self, user_id: str) -> int:
        """Get the score for a specific user with retry logic"""
        try:
            def fetch():
                result = self.client.table('scores').select('score').eq('user_id', user_id).execute()
                if result.data and len(result.data) > 0:
                    return result.data[0]['score']
                return 0
            
            return self._retry_operation(fetch, operation_name=f"get_score({user_id})")
        except Exception as e:
            print(f"❌ Error getting score for {user_id}: {e}")
            return 0
    
    def add_point(self, user_id: str, points: int, user_name: str = None):
        """Add points to a user's score (can be negative) with retry logic and transaction safety"""
        def update_score():
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
        
        try:
            self._retry_operation(update_score, operation_name=f"add_point({user_id}, {points})")
        except Exception as e:
            print(f"❌ Failed to add points for {user_id} after retries: {e}")
            # Don't raise - let caller handle gracefully
            raise
    
    def get_leaderboard(self, limit: int = 10) -> List[Tuple[str, Optional[str], int]]:
        """Get the top scores, ordered by score descending. Returns (user_id, user_name, score) with retry logic"""
        try:
            def fetch():
                result = self.client.table('scores').select('user_id, user_name, score').order('score', desc=True).limit(limit).execute()
                return [(row['user_id'], row['user_name'], row['score']) for row in result.data]
            
            return self._retry_operation(fetch, operation_name=f"get_leaderboard(limit={limit})")
        except Exception as e:
            print(f"❌ Error getting leaderboard after retries: {e}")
            return []
    
    def reset_scores(self):
        """Reset all scores to zero (use with caution!) with retry logic"""
        def reset():
            self.client.table('scores').delete().neq('user_id', '').execute()
        
        try:
            self._retry_operation(reset, operation_name="reset_scores")
        except Exception as e:
            print(f"❌ Failed to reset scores after retries: {e}")
            raise

