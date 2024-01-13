import re

import markdown_main
import markdown
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension
from markdown.extensions.tables import TableExtension
from markdown.extensions.extra import ExtraExtension
from bs4 import BeautifulSoup


class InfoBoxExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(InfoBoxProcessor(md), 'custom_brace', 30)


class InfoBoxProcessor(Preprocessor):
    def run(self, lines):
        new_lines = []
        in_braces = False

        for line in lines:
            if line.strip() == '{':
                in_braces = True
                new_lines.append('<table class="infobox"><tbody>')
            elif line.strip() == '}':
                in_braces = False
                new_lines.append('</tbody></table>')
            elif in_braces:
                processed_line = self.process_inside_braces(line)
                new_lines.append(processed_line)
            else:
                processed_line = self.process_line(line, in_braces)
                new_lines.append(processed_line)

        return new_lines

    def process_line(self, line, in_braces):
        if in_braces:
            return self.process_inside_braces(line)
        else:
            return f"{line}"

    def process_inside_braces(self, line):
        line = line.strip()
        if line.startswith('# '):
            return f'<tr><th class="infobox-above" colspan="2">{line[2:]}</th></tr>'
        elif line.startswith('## '):
            return f'<tr><th class="infobox-subheader" colspan="2">{line[3:]}</th></tr>'
        elif line.startswith('### '):
            return f'<tr><th class="infobox-subtitle" colspan="2">{line[4:]}</th></tr>'
        elif '|' in line:
            item, value = map(str.strip, line.split('|', 1))
            return f'<tr><th scope="row" class="infobox-label">{item}</th><td class="infobox-data">{value}</td></tr>'
        else:
            # Handle other cases as needed
            return f"{line}"


class TableOfContentsExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(TableOfContentsPreprocessor(md), 'table_of_contents', 30)


class TableOfContentsPreprocessor(Preprocessor):
    def run(self, lines):
        table_of_contents = []
        new_lines = []

        for line in lines:
            if line.startswith('#'):
                header_level = line.count('#')
                header_text = line.strip('#').strip()
                header_id = header_text.replace(' ', '')

                # Add header to the table_of_contents list
                table_of_contents.append((header_text, header_level, header_id))

                # Add an id attribute to the header tag
                line = f'<h{header_level} id="{header_id}">{header_text}</h{header_level}>'

            new_lines.append(line)

        # Add the table_of_contents list to the markdown instance
        setattr(self.md, 'table_of_contents', table_of_contents)

        return new_lines


class LinkifyExtension(markdown.Extension):
    def __init__(self, **kwargs):
        self.config = {
            'words': [kwargs.get('words', [])],
        }
        super(LinkifyExtension, self).__init__(**kwargs)

    def extendMarkdown(self, md):
        md.preprocessors.register(LinkifyPreprocessor(md, self.getConfigs()), 'linkify', 35)

class LinkifyPreprocessor(markdown.preprocessors.Preprocessor):
    def __init__(self, md, config):
        super().__init__(md)  # Remove config argument
        self.words = config.get('words', [])

    def run(self, lines):
        new_lines = []

        for line in lines:
            # Check and replace words in lines about to be wrapped by <p>, <li>, <td> tags
            line = self.linkify_words(line)

            new_lines.append(line)

        return new_lines

    def linkify_words(self, line):
        # Regular expression pattern to match <p>, <li>, and <td> tags
        tag_pattern = re.compile(r'<(p|li|td)\b[^>]*>.*?</\1>', re.DOTALL | re.IGNORECASE)

        # Find all matches of <p>, <li>, and <td> tags
        tag_matches = tag_pattern.finditer(line)
        excluded_positions = set()

        # Mark positions of existing <a> tags and their content
        for match in tag_matches:
            excluded_positions.update(range(match.start(), match.end()))

        # Function to handle replacement, excluding positions within existing <a> tags
        def replace_words(match):
            start, end = match.span()
            return match.group() if any(pos in excluded_positions for pos in range(start, end)) else f'<a href="/page?page={match.group()}">{match.group()}</a>'

        # Using regular expression with case-insensitive flag
        line = re.sub(rf'\b(?:{"|".join(map(re.escape, self.words))})\b', replace_words, line, flags=re.IGNORECASE)

        return line


def format_html(html_string):
    # Parse the HTML string
    soup = BeautifulSoup(html_string, 'html.parser')

    # Define the initial indentation level
    indentation = 0

    # Helper function to add tabs to a line
    def add_tabs(line):
        return '\t' * indentation + line

    # Helper function to remove excessive whitespace
    def clean_whitespace(line):
        return ' '.join(line.split())

    # Iterate through all tags in the HTML
    for tag in soup.descendants:
        # Check if the tag is a BeautifulSoup element
        if hasattr(tag, 'name'):
            # Add tabs to the start tag
            tag.insert_before(add_tabs(''))

            # Increase indentation for the tag content
            indentation += 1

            # Add tabs to the end tag
            tag.insert_after(add_tabs(''))

            # Remove excessive whitespace from the tag content
            if tag.string:
                tag.string.replace_with(clean_whitespace(tag.string))

            # Decrease indentation for the end tag
            indentation -= 1

    # Get the formatted HTML string
    formatted_html = soup.prettify()

    return formatted_html


def to_html(markdown_string, date, editor, title, page_list):
    md = markdown.Markdown(extensions=[InfoBoxExtension(), TableExtension(), TableOfContentsExtension(), LinkifyExtension(words=page_list), ExtraExtension(), 'sane_lists'])
    html_output = md.convert(markdown_string)
    table_of_contents = getattr(md, 'table_of_contents', [])

    header_id = title.replace(" ", "")

    result = f"""
    <div class="row">
        <div class="col-md-8 wiki-main">
            <div class="header-border">
                <div class="row">
                    <h1 class="col-md-8 page-header" id="{header_id}">{title}</h1>
                    <div class="col-md-4 text-md-right align-bottom">
                        <p class="date">Edited <span class="text-success">{date}</span> by <span class="text-primary">{editor}</span></p>
                    </div>
                </div>
            </div>
            <nav>
                <a href="/" class="">Home</a>
                <a href="" class="active">Page</a>
                <a href="">Comments</a>
                <a href="editor?page={title}" class="nav-right">Edit</a>
                <a href="" class="delete">Delete</a>
            </nav>
            <div class="wiki-post">
                {html_output}
            </div>
            </div>
            <aside class ="order-first col-md-2 wiki-sidebar list-truncate" >
              <h5 class="">Contents</h5>
              <hr class="no-margin pb-2">
              <ol class="list-unstyled mb-0">
        """

    for entry in table_of_contents:
        header_text, header_level, header_id = entry
        indentation = "toc-" + str(header_level - 2)  # Add indentation based on header level

        result += f'<li class={indentation}><a href="#{header_id}">{header_text}</a></li>\n'

    result += """
        </ol>
    </aside>
    <aside class="col-md-2 wiki-sidebar list-truncate">
        <h5 class="">Recent Pages</h5>
        <hr class="no-margin pb-2">
        <ol class="list-unstyled mb-0">
    """

    for i in range(15 if len(page_list) > 15 else len(page_list)):
        result += f'<li><a href="/page?page={page_list[i]}">{page_list[i]}</a></li>\n'

    result += """
        </ol>
    </aside>
    </div>
    """

    return result


# print(format_html(to_html(markdown_main.DEFAULT_MARKDOWN, 'Jan 1 1989', 'Fyresmith', 'Cool Title', ['One', 'Two', 'Three'])))

# final_markdown = """
# """
#
# final_markdown += markdown_string + "</div></div>"
#
# final_markdown += """
# <aside class="order-first col-md-2 wiki-sidebar list-truncate">
#     <h5 class="">Contents</h5>
#     <hr class="no-margin pb-2">
#     [TOC]
# </aside>
# </div>
#     """