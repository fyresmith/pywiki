import db
import random
import re
from datetime import datetime, timedelta

# access = db.Access('pages')
# access = db.Access('users')
# access.insert(['email', 'password', 'firstName', 'lastName'], ['jptthered@gmail.com', 'J0s3phT4rr4nt!', 'Joseph', 'Tarrant'])
# access.insert(['email', 'password', 'firstName', 'lastName'], ['me@calebmsmith.com', 'C4l3bSm1th!', 'Visitor', 'Visitor'])

# random_date = (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%B %d, %Y')
# access.insert(['title', 'markdown', 'date', 'editor', 'category'], ['Test Page 2', '', random_date, 'Caleb', 'Random'])