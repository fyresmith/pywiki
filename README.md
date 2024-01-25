# PyWiki
I didn't particularly like MediaWiki, so I built my own wiki platform. PyWiki is a simple wiki platform built to my own personal preferences in regards to markdown, storage, and features.

# Features
## Simple, Yet Strong Security
PyWiki uses many simple security practices expected with modern platforms. PyWiki requires two-factor authentication each time a user signs in, and uses a JWT system in order to keep users securely signed in for 24 hours. PyWiki also is careful to prevent SQL injection attacks via query parameterization. PyWiki also implements rate limiting in some cases in order to prevent users from promulgating DOS attacks.

## Markdown Editor
PyWiki uses a specialized version of John Grubers [Markdown](https://daringfireball.net/projects/markdown/syntax) as a raw form of text for each wiki page. Once a page is requested, the python backend takes the stored markdown, renders it as HTML, and returns a completed HTML page to the user. Given a user has the privelages, they may edit those pages directly from the application. The editor is a simply and specially-designed javascript text editor which provides highlighting to sections which will be rendered as HTML elements.

## Google Drive Backup System
PyWiki can be configured to routinely backup its database to a Google Drive folder of your choice. This feature does require you to set up a service account for Google Drive.

## A Full Wiki
PyWiki implements everything one might need for a simple personal Wiki.

# How to Use PyWiki
To get started with PyWiki, follow these steps:

- Clone the PyWiki repository to your local machine.
- Install required dependencies.
- Configure the .env file with the proper keys and values.
- Add account to sqlite database via console insert statement.
- Start the PyWiki application.

## License
PyWiki is licensed under the MIT License.

## Disclaimer
PyWiki is provided as-is without warranty of any kind. The developers of PyWiki are not responsible for any damages or losses caused by the use of PyWiki.
