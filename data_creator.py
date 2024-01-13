import db, markdown_main
import random
import re
from datetime import datetime, timedelta

access = db.Access('pages')

f = open('wikiml', 'r+')
md = f.readlines()
final_md = '\n'.join(md)

random_date = (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%B %d, %Y')
access.insert(['title', 'markdown', 'date', 'editor', 'category'], ['Test Page 2', final_md, random_date, 'Caleb', 'Random'])