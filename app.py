import os
import random
import sqlite3
import time

from flask import Flask, render_template, request, redirect, make_response, session, jsonify, send_file
from datetime import datetime, timedelta, timezone
import jwt
from functools import wraps

import markdown_main
import markdown_test
from db import Access
from mailer import send_email
import logging
from backup import backup_db, rollback_db

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

# backup_db()

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1


def generate_token(username):
    """
    Generates a JSON Web Token (JWT) for the given username.

    This function takes a username as input, creates a payload dictionary containing the username,
    and then encodes the payload using the app's secret key and the HS256 algorithm.

    :param username: The username for which the token is generated.
    :type username: str

    :return: The generated JWT token.
    :rtype: str
    """
    payload = {'username': username}

    token = jwt.encode(payload, app.secret_key, algorithm='HS256')

    return token


def token_required(f):
    """
    Decorator function to enforce token authentication for a given route.

    This decorator checks for the presence of a JWT token in the 'token' cookie of the request.
    If the token is missing or invalid, the user is redirected to the sign-in page.
    If the token is valid, it is decoded, and the username is extracted from the payload.
    The username is then passed to the decorated route function.

    :param f: The route function to be decorated.
    :type f: function

    :return: The decorated route function.
    :rtype: function
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        log.debug(f'Token: {token}')

        if not token:
            log.warning('Token is missing. Redirecting to sign-in page.')
            return redirect('/sign-in', code=302)

        try:
            data = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            log.info(f'Decoded JWT data: {data}')
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            log.warning('Token has expired. Redirecting to sign-in page.')
            return redirect('/sign-in', code=302)
        except jwt.InvalidTokenError:
            log.warning('Invalid token. Redirecting to sign-in page.')
            return redirect('/sign-in', code=302)

        return f(current_user, *args, **kwargs)

    return decorated


def parse_date(date_str):
    """
    Parses a date string into a datetime object.

    This function takes a date string formatted as "%b %d, %Y - %I:%M %p" and converts it into a
    datetime object using the `strptime` method.

    :param date_str: The date string to be parsed.
    :type date_str: str

    :return: A datetime object representing the parsed date.
    :rtype: datetime.datetime
    """
    date_object = datetime.strptime(date_str, "%b %d, %Y - %I:%M %p")

    return date_object


def get_recent_pages():
    """
    Retrieves a list of recent pages based on their titles and dates.

    This function uses the Access class to select the 'title' and 'date' fields from the 'pages' collection.
    The selected tuples are then sorted in descending order based on both date and time.
    The function returns a list of page titles, representing the recent pages.

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
    recent_pages = [subtuple[0] for subtuple in sorted_tuples]

    # return the list of recent page titles
    return recent_pages


def generate_random_code():
    """
    Generates a random 6-digit code.

    This function utilizes the random module to generate a random integer between 100000 and 999999.
    The generated code is returned as a string.

    :return: A randomly generated 6-digit code.
    :rtype: str
    """
    # generate a random integer between 100000 and 999999
    random_code = str(random.randint(100000, 999999))

    # return the generated code as a string
    return random_code


def authenticate_user(email, password):
    """
    Authenticates a user based on email and password.

    This function queries the 'users' collection using the Access class to retrieve user information
    (email, password, firstName, lastName). It then iterates through the retrieved users, checking
    if the provided email and password match any user's credentials. If a match is found, the user's
    first and last names are stored in the session, and the function returns True. Otherwise, it returns False.

    :param email: The email of the user attempting to authenticate.
    :type email: str
    :param password: The password of the user attempting to authenticate.
    :type password: str

    :return: True if authentication is successful, False otherwise.
    :rtype: bool
    """
    # create an Access instance for the 'users' collection
    access = Access('users')

    # select 'email', 'password', 'firstName', 'lastName' fields from the 'users' collection
    users = access.select(['email', 'password', 'firstName', 'lastName'])

    # iterate through the retrieved users
    for user in users:
        # check if provided email and password match any user's credentials
        if email == user[0] and password == user[1]:
            # if a match is found, store user's first and last names in the session
            session.update({'firstName': user[2], 'lastName': user[3]})
            log.info('User updated.')
            return True

    # return False if no matching credentials are found
    return False


def get_categories():
    """
    Retrieves unique categories from the 'pages' collection.

    This function uses the Access class to select the 'category' field from the 'pages' collection.
    It then iterates through the retrieved categories, ensuring uniqueness, and returns a list of categories.

    :return: A list of unique categories.
    :rtype: list
    """
    retries = 0

    while retries < MAX_RETRIES:
        try:
            access = None
            # create an Access instance for the 'pages' collection
            access = Access('pages')

            # select 'category' field from the 'pages' collection
            select = access.select(['category'])

            # initialize an empty list to store unique categories
            categories = []

            # iterate through the retrieved categories
            for item_list in select:
                category = item_list[0]

                # check if the category (after stripping whitespace) is not already in the list
                if category.strip() not in categories:
                    # if not, add it to the list of categories
                    categories.append(category.strip())

            # return the list of unique categories
            return categories

        except sqlite3.Error as e:
            log.error(f'Error getting categories: {e}')

            # Increment the number of retries
            retries += 1

            if retries < MAX_RETRIES:
                log.info(f'Retrying category retrieval after {RETRY_DELAY_SECONDS} seconds...')
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                log.error(f'Maximum number of retries reached. Category retrieval failed.')
                return []  # Handle the error or log as needed


def get_pages():
    """
    Retrieves pages organized by categories from the 'pages' collection.

    This function utilizes the get_categories function to obtain a list of unique categories.
    It then creates a dictionary where each category is a key mapped to a list of pages belonging to that category.
    The Access class is used to query the 'pages' collection for titles based on each category.
    The resulting dictionary is returned, representing pages organized by categories.

    :return: A dictionary of pages organized by categories.
    :rtype: dict
    """
    # obtain a list of unique categories using the get_categories function
    categories = get_categories()

    # initialize a dictionary where each category is a key mapped to an empty list
    pages = {key: [] for key in categories}

    # create an Access instance for the 'pages' collection
    access = Access('pages')

    # iterate through each category
    for category in categories:
        # select titles from the 'pages' collection for the current category
        select = access.select(['title'], f'category = "{category}"')

        # iterate through the selected titles and append them to the corresponding category in the dictionary
        for page in select:
            pages[category].append(page[0])

    # return the dictionary of pages organized by categories
    return pages


@app.route('/return-to-page', methods=['POST'])
@token_required
def return_to_page(current_user):
    """
    Handles the 'return-to-page' route for updating page content.

    This route expects a POST request containing 'editorContent' and 'page' parameters.
    The 'editorContent' parameter represents the updated content of the page.
    The 'page' parameter represents the title of the page to be updated.
    The token_required decorator ensures authentication before accessing this route.

    The function updates the 'markdown' field in the 'pages' collection for the specified page title.
    After the update, it redirects the user to the updated page.

    :param current_user: The authenticated user obtained from the token.
    :type current_user: str

    :return: Redirects to the updated page.
    :rtype: werkzeug.wrappers.response.Response
    """
    # get the updated content and page title from the POST request
    content = request.form.get('editorContent')
    page = request.form.get('page')

    # create an Access instance for the 'pages' collection
    access = Access('pages')

    # update the 'markdown' field for the specified page title
    access.update(['markdown'], [content], f'title = "{page}"')

    log.info('Updated page.')

    # redirect the user to the updated page
    return redirect(f'/page?page={page}', code=302)


@app.route('/save-file', methods=['POST'])
@token_required
def save_file(current_user):
    """
    Handles the 'save-file' route for saving file content.

    This route expects a POST request containing 'editorContent' and 'page' parameters.
    The 'editorContent' parameter represents the content of the file to be saved.
    The 'page' parameter represents the title of the page associated with the file.
    The token_required decorator ensures authentication before accessing this route.

    The function updates the 'markdown' field in the 'pages' collection for the specified page title.
    After the update, it redirects the user to the editor page for the saved file.

    :param current_user: The authenticated user obtained from the token.
    :type current_user: str

    :return: Redirects to the editor page for the saved file.
    :rtype: werkzeug.wrappers.response.Response
    """
    # get the content and page title from the POST request
    content = request.form.get('editorContent')
    page = request.form.get('page')

    # create an Access instance for the 'pages' collection
    access = Access('pages')

    # update the 'markdown' field for the specified page title
    access.update(['markdown'], [content], f'title = "{page}"')

    log.info('File was saved.')

    # redirect the user to the editor page for the saved file
    return redirect(f'/editor?page={page}', code=302)


@app.route('/create-page', methods=['GET', 'POST'])
@token_required
def create_page(current_user):
    """
    Handles the 'create-page' route for creating a new page.

    For GET requests, it renders the 'create-page.html' template.
    For POST requests, it expects a 'pageTitle' parameter in the form data.
    It checks if a page with the specified title already exists.
    If not, it creates a new page with default values and redirects the user to the editor page for the new page.

    :param current_user: The authenticated user obtained from the token.
    :type current_user: str

    :return: Renders 'create-page.html' template for GET requests, or redirects to the editor page for the new page for POST requests.
    :rtype: werkzeug.wrappers.response.Response or flask.templating.TemplatedResponse
    """
    if request.method == 'POST':
        # get the page title from the POST request
        page_title = request.form.get('pageTitle')

        # create an Access instance for the 'pages' collection
        access = Access('pages')

        # check if a page with the specified title already exists
        select = access.select(['title'], f'title = "{page_title}"')
        if len(select) != 0:
            log.warning('Attempt to create a page with an existing title.')
            return render_template('create-page.html', message='That page already exists!')

        # insert a new page with default values
        access.insert(['title', 'markdown', 'date', 'editor', 'category'],
                      [page_title, markdown_main.DEFAULT_MARKDOWN, datetime.now().strftime('%b %d, %Y - %I:%M %p'),
                       session.get('firstName'), ''])

        # redirect the user to the editor page for the new page
        return redirect(f'/editor?page={page_title}', code=302)
    else:
        log.debug('Rendering the "create-page.html" template for GET request.')
        # render the 'create-page.html' template for GET requests
        return render_template('create-page.html', message='')


@app.route('/update-page-name', methods=['GET', 'POST'])
@token_required
def update_page_name(current_user):
    """
    Handles the 'update-page-name' route for updating the title of a page.

    Expects a POST request containing 'new_page' and 'page' parameters.
    'new_page' represents the new title for the page, and 'page' represents the current title of the page.
    Checks if a page with the new title already exists. If not, updates the page title and redirects to the editor page.

    :param current_user: The authenticated user obtained from the token.
    :type current_user: str

    :return: Redirects to the editor page with the updated title if successful, otherwise returns None.
    :rtype: werkzeug.wrappers.response.Response or None
    """
    # get the new page title and current page title from the POST request
    new_page = request.form.get('new_page')
    page = request.form.get('page')

    # create an Access instance for the 'pages' collection
    access = Access('pages')

    # check if a page with the new title already exists
    select = access.select(['title'], f'title = "{new_page}"')
    if len(select) != 0:
        log.warning('Attempt to update page name to an existing title.')
        return None
    else:
        # update the page title and redirect to the editor page with the updated title
        access.update(['title'], [new_page.strip()], f'title = "{page}"')
        log.info(f'Page title updated: {page} -> {new_page}')
        return redirect(f'/editor?page={new_page}', code=302)


# TODO: split categories by string
@app.route('/update-page-category', methods=['GET', 'POST'])
@token_required
def update_page_category(current_user):
    """
    Handles the 'update-page-category' route for updating the category of a page.

    Expects a POST request containing 'new_category' and 'page' parameters.
    'new_category' represents the new category for the page, and 'page' represents the title of the page.
    Checks if the page exists and updates its category. Redirects to the editor page after the update.

    :param current_user: The authenticated user obtained from the token.
    :type current_user: str

    :return: Redirects to the editor page with the updated category if successful, otherwise returns None.
    :rtype: werkzeug.wrappers.response.Response or None
    """
    # get the new category and page title from the POST request
    category = request.form.get('new_category')
    page = request.form.get('page')

    # create an Access instance for the 'pages' collection
    access = Access('pages')

    # check if the page exists
    select = access.select(['category'], f'title = "{page}"')
    if len(select) == 0:
        log.warning(f'Attempt to update category for non-existing page: {page}')
        return None
    else:
        # update the category of the page and redirect to the editor page
        access.update(['category'], [category.strip()], f'title = "{page}"')
        log.info(f'Category updated for page: {page} -> {category}')
        return redirect(f'/editor?page={page}', code=302)


@app.route('/editor', methods=['GET'])
@token_required
def editor(current_user):
    """
    Handles the 'editor' route for displaying and updating page content.

    Expects a GET request containing 'page' parameter representing the title of the page.
    Retrieves the page's markdown content and category from the 'pages' collection.
    Updates the 'editor' and 'date' fields in the 'pages' collection with the current user and timestamp.
    Renders the 'editor.html' template with the page content, title, and category.

    :param current_user: The authenticated user obtained from the token.
    :type current_user: str

    :return: Renders 'editor.html' template with the page content, title, and category.
    :rtype: flask.templating.TemplatedResponse
    """
    # get the page title from the GET request
    page = request.args.get('page')

    # create an Access instance for the 'pages' collection
    access = Access('pages')

    # select 'markdown' and 'category' fields for the specified page title
    select = access.select(['markdown', 'category'], f'title = "{page}"')

    # update 'editor' and 'date' fields with the current user and timestamp
    access.update(['editor', 'date'], [session.get('firstName'), datetime.now().strftime('%b %d, %Y - %I:%M %p')],
                  f'title = "{page}"')

    # initialize variables for page markdown content and category
    page_markdown = ''
    category = ''

    # check if the page exists
    if select:
        # retrieve page markdown content and category from the select result
        page_markdown = select[0][0]
        category = select[0][1]
        log.info(f'Editor accessed for page: {page}')

    # render the 'editor.html' template with the page content, title, and category
    return render_template('editor.html', page_content=page_markdown, page=page, category=category)


@app.route('/page', methods=['GET'])
@token_required
def get_page(current_user):
    """
    Handles the 'page' route for displaying a page's content.

    Expects a GET request containing 'page' parameter representing the title of the page.
    Retrieves markdown content, date, and editor information from the 'pages' collection.
    Parses the markdown content into HTML using the markdown module.
    Renders the 'page.html' template with the parsed HTML content.

    :param current_user: The authenticated user obtained from the token.
    :type current_user: str

    :return: Renders 'page.html' template with the parsed HTML content.
    :rtype: flask.templating.TemplatedResponse
    """
    # get the page title from the GET request
    page = request.args.get('page')

    # retrieve recent pages for display
    recent_pages = get_recent_pages()

    # create an Access instance for the 'pages' collection
    access = Access('pages')

    # select 'markdown', 'date', and 'editor' fields for the specified page title
    data = access.select(['markdown', 'date', 'editor'], f'title = "{page}"')

    # extract markdown content, date, and editor information from the select result
    # md = data[0][0].split('\n') if data else []
    md = data[0][0]
    date = data[0][1] if data else ''
    editor = data[0][2] if data else ''

    # parse markdown content into HTML using the markdown module
    html = markdown_test.to_html(md, date, editor, page, recent_pages)

    # render the 'page.html' template with the parsed HTML content
    return render_template('page.html', md=html)


@app.route('/code', methods=['POST'])
@token_required
def code_input(current_user):
    """
    Handles the 'code' route for processing user inputted verification code.

    Expects a POST request containing 'num1' through 'num6' parameters representing the six digits of the verification code.
    Compares the user-inputted code with the stored code in the session.
    If the codes match, sets the 'user_signed_in' session variable to True and redirects to the home page.
    If the codes do not match, renders the 'verify.html' template with an appropriate error message.

    :param current_user: The authenticated user obtained from the token.
    :type current_user: str

    :return: Redirects to the home page if verification is successful, otherwise renders 'verify.html' with an error message.
    :rtype: werkzeug.wrappers.response.Response or flask.templating.TemplatedResponse
    """
    # concatenate user-inputted digits to form the verification code
    user_code = ''.join(request.form.get(f'num{i}') for i in range(1, 7))
    log.info(f'User entered verification code: {user_code}')

    # compare user-inputted code with the stored code in the session
    if str(session.get('code')) == user_code:
        # set 'user_signed_in' session variable to True if verification is successful
        session['user_signed_in'] = True
        log.info(f'User {current_user} successfully verified.')
        return redirect("/", code=302)
    else:
        # render 'verify.html' with an error message if verification fails
        log.warning(f'User {current_user} entered incorrect verification code.')
        return render_template('verify.html', message='That code is incorrect!')


@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    """
    Handles the 'sign-in' route for user authentication.

    For GET requests, it renders the 'sign-in.html' template.
    For POST requests, it expects 'email' and 'password' parameters in the form data.
    Authenticates the user using the authenticate_user function.
    If authentication is successful, generates a token and sends a verification code via email.
    Renders the 'verify.html' template and sets a cookie with the token.

    :return: Renders 'sign-in.html' for GET requests, or 'verify.html' with a token cookie for successful authentication in POST requests.
    :rtype: flask.templating.TemplatedResponse or werkzeug.wrappers.response.Response
    """
    # initialize an empty message
    message = ''

    # process POST requests
    if request.method == 'POST':
        # get email and password from the form data
        email = request.form.get('email')
        password = request.form.get('password')

        # authenticate the user using the authenticate_user function
        if authenticate_user(email, password):
            # generate a token and a verification code, then send the code via email
            token = generate_token(email)
            session['code'] = generate_random_code()
            send_email(email, session.get('code'))
            log.info(f'User {email} successfully authenticated. Verification code sent.')

            # render 'verify.html' and set a cookie with the token
            response = make_response(render_template('verify.html'))
            expiration_time = datetime.now(timezone.utc) + timedelta(days=1)
            response.set_cookie('token', token, httponly=True, expires=expiration_time)
            return response

        # set an error message if authentication fails
        message = 'No valid match was found :/'
        log.warning(f'Authentication failed for user {email}.')

    # render 'sign-in.html' for GET requests or 'verify.html' with an error message for unsuccessful POST requests
    return render_template('sign-in.html', message=message)


@app.route('/sign-out', methods=['GET'])
def sign_out():
    """
    Handles the 'sign-out' route for user sign-out.

    Clears all cookies and redirects the user to the home page.

    :return: Redirects to the home page with cleared cookies.
    :rtype: werkzeug.wrappers.response.Response
    """
    # create a response object and delete all cookies
    response = make_response(redirect('/'))
    [response.delete_cookie(key) for key in request.cookies.keys()]
    log.info('User signed out.')

    # return the response with cleared cookies
    return response


@app.route('/download-db', methods=['GET'])
@token_required
def download_db(current_user):
    # Path to the data.db file
    db_file_path = 'path/to/your/data.db'  # Update this with the actual path to your data.db file

    # Check if the file exists
    if os.path.exists(db_file_path):
        # Send the file to the client for download
        return send_file(db_file_path, as_attachment=True)
    else:
        return 'File not found', 404


@app.route('/test', methods=['GET'])
def test():
    return render_template("test.html")


@app.route('/', methods=['GET'])
@token_required
def main(current_user):
    """
    Handles the main route '/' for displaying the user's dashboard.

    Retrieves page categories using the 'get_pages' function and renders the 'dashboard.html' template.

    :param current_user: The authenticated user obtained from the token.
    :type current_user: str

    :return: Renders 'dashboard.html' template with page categories.
    :rtype: flask.templating.TemplatedResponse
    """
    # retrieve page categories using the 'get_pages' function
    categories = get_pages()

    # render the 'dashboard.html' template with page categories
    return render_template('dashboard.html', categories=categories)


if __name__ == '__main__':
    app.run()
