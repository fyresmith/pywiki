import os
import random
import sqlite3
import threading
import time
from typing import List

from flask import Flask, render_template, request, redirect, make_response, session, jsonify, send_file
from datetime import datetime, timedelta, timezone
import jwt
from functools import wraps

import markdown_fyresmith
from db import Access
from mailer import send_email
import logging
from backup import backup_db

app = Flask(__name__)
app.secret_key = 'cb55906271b159debefe6e7b7786a22ade3fc1f0be5c38d39b8d8f457c856c70'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("app")

# Backup Threading Logic
is_backup_thread_active = any(thread.name == "backup_db" and thread.is_alive() for thread in threading.enumerate())

if not is_backup_thread_active:
    log.info('Backup Scheduled.')
    backup_thread = threading.Timer(24 * 3600, backup_db)
    backup_thread.name = "backup_db"
    backup_thread.start()

# Inter-Thread Data Structures
lock = threading.Lock()
last_update_times = {}
pages_being_edited = {}

# Constants
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1


def generate_token(user: List[str]) -> str:
    """
    Generates a JWT (JSON Web Token) for the given username.

    :param user: The username for which the token is generated.
    :type user: list

    :return: The generated JWT token.
    :rtype: str
    """

    payload = {
        'email': user[0],
        'first_name': user[1],
        'last_name': user[2],
        'role': user[3]
    }

    token = jwt.encode(payload, app.secret_key, algorithm='HS256')

    return token


def token_required(f):
    """
    Decorator function to enforce token authentication for a given route.

    :param f: The route function to be decorated.
    :type f: function

    :return: The decorated route function.
    :rtype: function
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')

        if not token:
            log.warning('Token is missing. Redirecting to sign-in page.')
            return redirect('/sign-in', code=302)

        try:
            data = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            log.info(f'Decoded JWT data: {data}')

            user = {
                'email': data['email'],
                'role': data['role'],
                'first_name': data['first_name'],
                'last_name': data['last_name']
            }

        except jwt.ExpiredSignatureError:
            log.warning('Token has expired. Redirecting to sign-in page.')
            return redirect('/sign-in', code=302)
        except jwt.InvalidTokenError:
            log.warning('Invalid token. Redirecting to sign-in page.')
            return redirect('/sign-in', code=302)

        return f(user, *args, **kwargs)

    return decorated


def parse_date(date_str: str) -> datetime:
    """
    Parses a date string into a datetime object.

    :param date_str: The date string to be parsed.
    :type date_str: str

    :return: A datetime object representing the parsed date.
    :rtype: datetime.datetime
    """
    date_object = datetime.strptime(date_str, "%b %d, %Y - %I:%M %p")

    return date_object


def get_page_list() -> List[str]:
    """
    Retrieves a list of recent pages based on their titles and dates.

    :return: A list of recent page titles.
    :rtype: list
    """
    # create an Access instance for the 'pages' collection
    access = Access('pages')

    # select 'title' and 'date' fields from the 'pages' collection
    select = access.select(['title', 'date'])

    # sort the list of tuples based on both date and time in descending order
    sorted_tuples = sorted(select, key=lambda item: (datetime.strptime(item[1], "%b %d, %Y - %I:%M %p"), item),
                           reverse=True)

    # extract page titles from the sorted tuples
    page_list = [subtuple[0] for subtuple in sorted_tuples]

    # return the list of recent page titles
    return page_list


def generate_random_code() -> str:
    """
    Generates a random 6-digit code.

    :return: A randomly generated 6-digit code.
    :rtype: str
    """
    # generate a random integer between 100000 and 999999
    random_code = str(random.randint(100000, 999999))

    # return the generated code as a string
    return random_code


def get_user_info(email: str) -> list or None:
    access = Access('users')

    users = access.select(['email', 'firstName', 'lastName', 'role'])

    for user in users:
        if email == user[0]:
            log.info('User updated.')
            return user

    return None


def authenticate_user(email: str, password: str) -> list or None:
    """
    Authenticates a user based on email and password.

    :param email: The email of the user attempting to authenticate.
    :type email: str
    :param password: The password of the user attempting to authenticate.
    :type password: str

    :return: True if authentication is successful, False otherwise.
    :rtype: bool
    """
    access = Access('users')

    users = access.select(['email', 'password', 'firstName', 'lastName', 'role'])

    for user in users:
        if email == user[0] and password == user[1]:
            log.info('User updated.')
            return user

    return None


def get_page_categories() -> list:
    """
    Retrieves unique categories from the 'pages' collection.

    :return: A list of unique categories.
    :rtype: list
    """
    retries = 0

    while retries < MAX_RETRIES:
        try:
            access = Access('pages')

            select = access.select(['category'])

            categories = []

            for item_list in select:
                category = item_list[0]

                if ',' in category:
                    string = category.split(',')
                else:
                    string = [category]

                for item in string:
                    if item.strip() not in categories:
                        # if not, add it to the list of categories
                        categories.append(item.strip())

            return categories

        except sqlite3.Error as e:
            log.error(f'Error getting categories: {e}')

            retries += 1

            if retries < MAX_RETRIES:
                log.info(f'Retrying category retrieval after {RETRY_DELAY_SECONDS} seconds...')
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                log.error(f'Maximum number of retries reached. Category retrieval failed.')
                return []  # Handle the error or log as needed


def get_organized_pages():
    """
    Retrieves pages organized by categories from the 'pages' collection.

    :return: A dictionary of pages organized by categories.
    :rtype: dict
    """
    # obtain a list of unique categories using the get_categories function
    categories = get_page_categories()

    # initialize a dictionary where each category is a key mapped to an empty list
    pages = {key: [] for key in categories}

    # create an Access instance for the 'pages' collection
    access = Access('pages')

    select = access.select(['title', 'category'])

    for page in select:
        for category in categories:
            if category in page[1] and category != '':
                pages[category].append(page[0])
            elif category == '' and page[1] == '':
                pages[category].append(page[0])

    # return the dictionary of pages organized by categories
    return pages


def render_page_with_modal(page: str, title='', message=''):
    return redirect(f'/page?page={page}&title={title}&message={message}')


def render_home_with_modal(title='', message=''):
    return redirect(f'/?title={title}&message={message}')


def unlock_page_if_inactive(page: str):
    """
    Unlocks a page if this server has not received a ping from an editor in twenty seconds.

    :param page: The name of the page to be checked as a string
    :return: nothing
    """

    with lock:
        current_time = time.time()
        last_update_time = last_update_times.get(page, 0)

        if current_time - last_update_time >= 20:
            log.info(f'Page: {page} unlocked due to inactivity.')
            del pages_being_edited[page]


def detect_users():
    """
    A thread function which will monitor and manage pages being edited.

    :return: None
    """

    try:
        while True:
            time.sleep(3)

            keys = []

            keys.extend(list(pages_being_edited.keys()))

            for page in keys:
                unlock_page_if_inactive(page)

    except Exception as e:
        log.error(f"Error in detect_users: {e}")


def lock_page(page, email):
    """
    Locks a page for a user to edit.

    :param page: Name of the page to be locked.
    :param email: User's email address.
    :return: None.
    """

    with lock:
        pages_being_edited[page] = email
        last_update_times[page] = time.time()


# Start the detect_users thread
threading.Thread(target=detect_users).start()


@app.route('/active-editor', methods=['POST'])
@token_required
def active_editor(user: dict):
    try:
        page = request.json.get('page')

        log.info(f"Pinged by editor: '{user['email']}' for page: '{page}'")

        with lock:
            pages_being_edited[page] = user['email']
            last_update_times[page] = time.time()

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        log.error(f"Error in active_editor: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/return-to-page', methods=['POST'])
@token_required
def return_to_page(user: dict):
    """
    Handles the 'return-to-page' route for updating page content.

    :param user: The authenticated user obtained from the token.
    :type user: dict

    :return: Redirects to the updated page.
    :rtype: werkzeug.wrappers.response.Response
    """
    content = request.form.get('editorContent')
    page = request.form.get('page')

    access = Access('pages')
    access.update(['markdown'], [content], f'title = "{page}"')

    log.info('Updated page.')

    return render_page_with_modal(page)


@app.route('/save-file', methods=['POST'])
@token_required
def save_file(user: dict):
    """
    Handles the 'save-file' route for saving file content.

    :param user: The authenticated user obtained from the token.
    :type user: dict

    :return: Redirects to the editor page for the saved file.
    :rtype: Response
    """
    content = request.form.get('editorContent')
    page = request.form.get('page')

    if pages_being_edited[page] == user['email']:
        access = Access('pages')
        access.update(['markdown'], [content], f'title = "{page}"')

        log.info('File was saved.')

        return redirect(f'/editor?page={page}', code=302)
    else:
        return render_page_with_modal(page, title='Access Denied!',
                                      message='Your save request was denied because '
                                              'you are not currently editing the document!')


@app.route('/create-page', methods=['GET', 'POST'])
@token_required
def create_page(user: dict):
    """
    Handles the 'create-page' route for creating a new page.

    :param user: The authenticated user obtained from the token.
    :type user: dict

    :return: Renders 'create-page.html' template for GET requests, or redirects to the editor page for the new page for POST requests.
    :rtype: Response
    """
    if user['role'] != 'admin' and user['role'] != 'editor':
        return render_home_with_modal(title='Access Denied!', message='You do not have the permissions to create a page!')

    if request.method == 'POST':
        page_title = request.form.get('pageTitle')

        access = Access('pages')

        select = access.select(['title'], f'title = "{page_title}"')

        if len(select) != 0:
            log.warning(f'User {user["email"]} attempted to create a page with an existing title.')
            return render_template('create-page.html', message='That page already exists!')
        else:
            access.insert(['title', 'markdown', 'date', 'editor', 'category'],
                          [page_title, markdown_fyresmith.DEFAULT_MARKDOWN,
                           datetime.now().strftime('%b %d, %Y - %I:%M %p'),
                           user['first_name'], ''])

            return redirect(f'/editor?page={page_title}', code=302)
    else:
        log.debug('Rendering the "create-page.html" template for GET request.')
        return render_template('create-page.html', message='')


@app.route('/delete-page', methods=['GET', 'POST'])
@token_required
def delete_page(user: dict):
    """
    Handles the 'delete-page' route for deleting a page.

    :param user: The authenticated user obtained from the token.
    :type user: dict

    :return: Renders 'delete-page.html' template for GET requests, or redirects to the editor page for the new page for POST requests.
    :rtype: Response
    """
    if user['role'] != 'admin':
        return render_home_with_modal(title='Access Denied!',
                                      message='You do not have the permissions to delete a page!')

    if request.method == 'POST':
        page = request.args.get('page')
        page_title = request.form.get('pageTitle')

        if page != page_title:
            return render_template('delete-page.html', page=page, message='Page title does not match!')

        # Check again if the user is an admin.
        if user['role'] == 'admin':
            access = Access('pages')
            access.delete(f'title = "{page_title}"')
            render_home_with_modal(title='Success!', message=f'Page: "{page}" was successfully deleted!')
        else:
            return render_home_with_modal(title='Access Denied!', message='You do not have the permissions to delete a page!')
    else:
        page = request.args.get('page')

        if page in pages_being_edited.keys() and pages_being_edited[page] != user['email']:
            log.info(f'{user["email"]} attempted to access deletion page for page: {page} but was denied access.')

            return render_page_with_modal(page, title='Page Locked!',
                                          message='Page deletion is not allowed while the page is being edited. Please '
                                                  'wait for the editor to finish.')
        elif user['role'] != 'admin':
            render_page_with_modal(page, title='Access Denied!',
                                   message='You do not have the permissions to delete a page!')
        else:
            log.debug('Rendering the "delete-page.html" template for GET request.')
            return render_template('delete-page.html', page=page)


@app.route('/update-page-name', methods=['GET', 'POST'])
@token_required
def update_page_name(user: dict):
    """
    Handles the 'update-page-name' route for updating the title of a page.

    :param user: The authenticated user obtained from the token.
    :type user: dict

    :return: Redirects to the editor page with the updated title if successful, otherwise returns None.
    :rtype: Response or None
    """
    if user['role'] != 'admin' and user['role'] != 'editor':
        return {'status', 'denied'}

    new_page = request.form.get('new_page')
    page = request.form.get('page')

    if pages_being_edited[page] != user['email']:
        return render_page_with_modal(page, title='Access Denied!',
                                      message='Your update request was denied because you are not currently editing '
                                              'the document!')
    else:
        access = Access('pages')

        select = access.select(['title'], f'title = "{new_page}"')

        if len(select) != 0:
            log.warning('Attempt to update page name to an existing title.')
            return None
        else:
            access.update(['title'], [new_page.strip()], f'title = "{page}"')
            log.info(f'Page title updated: {page} -> {new_page}')
            return redirect(f'/editor?page={new_page}', code=302)


@app.route('/update-page-category', methods=['GET', 'POST'])
@token_required
def update_page_category(user: dict):
    """
    Handles the 'update-page-category' route for updating the category of a page.

    :param user: The authenticated user obtained from the token.
    :type user: dict

    :return: Redirects to the editor page with the updated category if successful, otherwise returns None.
    :rtype: Response or None
    """
    if user['role'] != 'admin' and user['role'] != 'editor':
        return {'status', 'denied'}

    category = request.form.get('new_category')
    page = request.form.get('page')

    if pages_being_edited[page] != user['email']:
        return render_page_with_modal(page, title='Access Denied!',
                                      message='Your update request was denied because you are not currently editing '
                                              'the document!')
    else:
        access = Access('pages')

        select = access.select(['category'], f'title = "{page}"')
        if len(select) == 0:
            log.warning(f'Attempt to update category for non-existing page: {page}')
            return None
        else:
            access.update(['category'], [category.strip()], f'title = "{page}"')
            log.info(f'Category updated for page: {page} -> {category}')
            return redirect(f'/editor?page={page}', code=302)


@app.route('/editor', methods=['GET'])
@token_required
def editor(user: dict):
    """
    Handles the 'editor' route for displaying and updating page content.

    :param user: The authenticated user obtained from the token.
    :type user: dict

    :return: Renders 'editor.html' template with the page content, title, and category.
    :rtype: Response
    """
    page = request.args.get('page')

    if user['role'] != 'admin' and user['role'] != 'editor':
        return render_page_with_modal(page, title='Access Denied!', message='You do not have the permissions to '
                                                                            'access the editor for this page!')

    if page in pages_being_edited.keys() and pages_being_edited[page] != user['email']:
        log.info(f'{user["email"]} attempted to access editor for page: {page} but was denied access.')

        return render_page_with_modal(page, 'Page Locked!',
                                      'The page editor is locked as it is currently being edited. Please '
                                      'wait for the editor to finish.')
    else:
        access = Access('pages')

        select = access.select(['markdown', 'category'], f'title = "{page}"')

        access.update(['editor', 'date'], [user['first_name'], datetime.now().strftime('%b %d, %Y - %I:%M %p')],
                      f'title = "{page}"')

        page_markdown = ''
        category = ''

        if select:
            page_markdown = select[0][0]
            category = select[0][1]

        log.info(f'Editor accessed for page: {page}')

        lock_page(page, user['email'])

        return render_template('editor.html', page_content=page_markdown, page=page,
                               category=category, first_name=user['first_name'])


@app.route('/page', methods=['GET'])
@token_required
def get_page(user: dict):
    """
    Handles the 'page' route for displaying a page's content.

    :param user: The authenticated user obtained from the token.
    :type user: dict

    :return: Renders 'page.html' template with the parsed HTML content.
    :rtype: flask.templating.TemplatedResponse
    """
    page = request.args.get('page')
    title = request.args.get('title')
    message = request.args.get('message')

    if title is None:
        title = ''

    if message is None:
        message = ''

    page_list = get_page_list()

    if page not in page_list:
        return render_template('404.html')

    access = Access('pages')

    data = access.select(['markdown', 'date', 'editor'], f'title = "{page}"')

    md = data[0][0]
    date = data[0][1] if data else ''
    editor = data[0][2] if data else ''

    html = markdown_fyresmith.to_html(md, date, editor, page, page_list, user['role'])

    return render_template('page.html', md=html, title=title,
                           message=message, first_name=user['first_name'])


@app.route('/download-db', methods=['GET'])
@token_required
def download_db(user: dict):
    if user['role'] != 'admin' and user['role'] != 'editor':
        return render_home_with_modal(title='Access Denied!', message='You do not have the permissions to '
                                                                      'access the database!')

    db_file_path = 'data/data.db'

    if os.path.exists(db_file_path):
        return send_file(db_file_path, as_attachment=True)
    else:
        return 'File not found', 404


@app.route('/backup-db', methods=['GET'])
@token_required
def backup_database(user: dict):
    if user['role'] == 'admin':
        backup_db()
        return render_home_with_modal(title='Success!', message='The database was backed up.')

    return render_home_with_modal(title='Access Denied!', message='You do not have the permissions to '
                                                                  'backup the database!')


@app.route('/', methods=['GET'])
@token_required
def main(user: dict):
    """
    Handles the main route '/' for displaying the user's dashboard.

    :param user: The authenticated user obtained from the token.
    :type user: dict

    :return: Renders 'dashboard.html' template with page categories.
    :rtype: flask.templating.TemplatedResponse
    """
    title = request.args.get('title')
    message = request.args.get('message')

    if title is None:
        title = ''

    if message is None:
        message = ''

    categories = get_organized_pages()

    return render_template('dashboard.html', categories=categories, title=title,
                           message=message, first_name=user['first_name'], role=user['role'])


@app.route('/code', methods=['GET', 'POST'])
def code_input():
    """
    Handles the 'code' route for processing user inputted verification code.

    :return: Redirects to the home page if verification is successful, otherwise renders 'verify.html' with an error message.
    :rtype: Response
    """
    if request.method == 'POST':
        email = session.get('email')

        if email is None or email == '':
            return redirect('/sign-in', code=302)

        user_code = ''.join(request.form.get(f'num{i}') for i in range(1, 7))
        log.info(f'User entered verification code: {user_code}')

        if str(session.get('code')) == user_code:
            user = get_user_info(email)

            token = generate_token(user)
            expiration_time = datetime.now(timezone.utc) + timedelta(days=1)
            response = make_response(redirect("/", code=302))
            response.set_cookie('token', token, httponly=True, expires=expiration_time)

            log.info(f'User {email} successfully verified.')
            return response
        else:
            log.warning(f'User {email} entered incorrect verification code.')
            return render_template('verify.html', message='That code is incorrect!')
    else:
        return render_page_with_modal('verify.html')


@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    """
    Handles the 'sign-in' route for user authentication.

    :return: Renders 'sign-in.html' for GET requests, or 'verify.html' with a token cookie for successful authentication in POST requests.
    :rtype: flask.templating.TemplatedResponse or werkzeug.wrappers.response.Response
    """
    message = ''

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = authenticate_user(email, password)

        if user is not None:
            session['code'] = generate_random_code()
            send_email(email, session.get('code'))
            log.info(f'User {email} successfully authenticated. Verification code sent.')

            session['email'] = user[0]

            return render_template('verify.html')
        else:
            message = 'No valid match was found.'
            log.warning(f'Authentication failed for user {email}.')

    return render_template('sign-in.html', message=message)


@app.route('/sign-out', methods=['GET'])
def sign_out():
    """
    Handles the 'sign-out' route for user sign-out.

    :return: Redirects to the home page with cleared cookies.
    :rtype: werkzeug.wrappers.response.Response
    """
    response = make_response(redirect('/'))
    [response.delete_cookie(key) for key in request.cookies.keys()]
    log.info('User signed out.')

    return response


if __name__ == '__main__':
    app.run()
