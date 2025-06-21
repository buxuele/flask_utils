from app.extensions import db
from datetime import datetime

class Prompt(db.Model):
    __tablename__ = 'prompts' # Optional: Explicitly name the table
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Prompt {self.id}>'
