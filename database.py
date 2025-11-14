import os
from supabase import create_client, Client


class Database:
    def __init__(self):
        """Initialize Supabase client"""
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        self.table_name = "leaderboard"
    
    def get_user_points(self, user_id: str) -> int:
        """Get current points for a user"""
        try:
            result = self.client.table(self.table_name).select("points").eq("user_id", user_id).execute()
            
            if result.data:
                return result.data[0]["points"]
            return 0
        except Exception as e:
            print(f"Error getting points for {user_id}: {e}")
            return 0
    
    def add_points(self, user_id: str, points: int, username: str = None):
        """Add points to a user (creates user if doesn't exist)"""
        try:
            current_points = self.get_user_points(user_id)
            new_points = current_points + points
            
            # Upsert: insert or update
            data = {
                "user_id": user_id,
                "points": new_points
            }
            if username:
                data["username"] = username
            
            self.client.table(self.table_name).upsert(data).execute()
            
            print(f"Added {points} points to {username or user_id}. New total: {new_points}")
        except Exception as e:
            print(f"Error adding points to {user_id}: {e}")
    
    def subtract_points(self, user_id: str, points: int, username: str = None):
        """Subtract points from a user (creates user if doesn't exist)"""
        try:
            current_points = self.get_user_points(user_id)
            new_points = current_points - points
            
            # Upsert: insert or update
            data = {
                "user_id": user_id,
                "points": new_points
            }
            if username:
                data["username"] = username
            
            self.client.table(self.table_name).upsert(data).execute()
            
            print(f"Subtracted {points} points from {username or user_id}. New total: {new_points}")
        except Exception as e:
            print(f"Error subtracting points from {user_id}: {e}")
    
    def get_leaderboard(self, limit: int = 10):
        """Get top users by points"""
        try:
            result = self.client.table(self.table_name).select("*").order("points", desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []

