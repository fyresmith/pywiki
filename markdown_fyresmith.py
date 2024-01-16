import re

import markdown
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension
from markdown.extensions.extra import ExtraExtension
from bs4 import BeautifulSoup

DEFAULT_MARKDOWN = """
{
# This Is An Infobox
## I <3 infoboxes because they let me put information nice and concisely.
Label | Here is a Value
Another Label | Another Value :D
Label's Are Cool | Value's are cooler
### Important Grouping of Information
Organized Labels | Are much superior.
Final Label? | Yep. Final Label.
}

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus quis arcu non felis commodo dictum. Nullam tincidunt orci nec porta imperdiet. Quisque condimentum ut ipsum quis mollis. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Duis tempus ligula justo. Etiam vel nisl ante. Nullam ac neque turpis.

Vivamus rhoncus arcu eget nulla volutpat tincidunt. Pellentesque a bibendum ligula. Nam cursus odio nec nibh fermentum pretium. Nunc euismod, est rhoncus ultrices egestas, erat libero pretium felis, eget cursus tellus leo non neque. Pellentesque euismod ut mauris ac ultrices. Morbi porttitor non eros sed bibendum. Proin congue lacus non metus dignissim rutrum.

_This is some emphasized text._

*This is some more emphasized text.*

__This is some bold text.__

**This is some more bold text.**

***This is bold emphasized text.***

Footnotes[^1] have a label[^@#$%] and the footnote's content.

# Generic Sub Title

Nam semper nunc sit amet blandit vehicula. 

This is what an unordered list would look like :D

* Suspendisse aliquet nisi mauris, a aliquam ligula blandit faucibus. 
* Etiam tempor cursus porttitor. Aliquam elementum nulla et nisi sollicitudin rutrum. 
* Donec hendrerit tristique massa, eget lacinia eros eleifend vel. 
* Donec eget arcu id nisl pulvinar condimentum. 

And this is what an ordered list looks like :)

1. Maecenas aliquet luctus augue vitae sagittis. 
2. Mauris vel turpis vel eros imperdiet bibendum. 
3. Quisque metus purus, ultrices vitae mi nec, mattis congue nisl. 
4. Vivamus nunc sem, tincidunt sit amet enim vitae, consequat accumsan felis.

## Simple Header

In et elit vitae augue tincidunt scelerisque et nec nulla. 

### This is a sub header!

Pellentesque pharetra tincidunt mi in pharetra. Pellentesque consequat congue nunc. Mauris aliquet tempus ex, sit amet tempor dui condimentum sed. Aenean non fringilla magna. 

### It's an easy way to divide up your content!

Donec ac porttitor felis, eu dignissim massa. Nulla eu dignissim dui, vestibulum vulputate dolor. Cras mi risus, ultricies a volutpat eu, euismod non odio. Phasellus aliquet sed libero in ullamcorper. Pellentesque quis risus vel magna condimentum tempus ac vitae velit. Nulla rutrum magna ut vestibulum maximus.

## Another Simple Header

In ultrices, enim ut varius finibus, metus tellus consequat risus, quis maximus nulla elit id mauris. Aliquam pretium metus sed placerat lobortis. In fringilla velit non tellus consequat, sed convallis felis pulvinar. Sed ac est luctus, semper purus non, dictum dui. Ut nisi velit, mattis eu ex vel, sodales tincidunt nisi. Nam et enim venenatis, malesuada ligula eu, maximus nisi. Duis finibus in metus id sagittis.

## Gotta Love Those Headers

Here is where I show you how to do links.

[An Example Link](http://example.com/ "Title")
[Another Example Link](/page?page=Second Test Page Wow)

Here is a reference to another page called Example. Unfortunately I cannot reference myself as Lorem Ipsum.

## Wow, ANOTHER header??

`This is a code block` Something in between them `And here's another code block`

# This is just a regular sub title.

## Blockquotes are awesome!

> This is a block quote.

Something in between.

> Now I will tell you the answer to my question. It is this. The Party seeks power entirely for its own sake. We are not interested in the good of others; we are interested solely in power, pure power. What pure power means you will understand presently. We are different from the oligarchies of the past in that we know what we are doing. All the others, even those who resembled ourselves, were cowards and hypocrites. The German Nazis and the Russian Communists came very close to us in their methods, but they never had the courage to recognize their own motives. They pretended, perhaps they even believed, that they had seized power unwillingly and for a limited time, and that just around the corner there lay a paradise where human beings would be free and equal. We are not like that. We know that no one ever seizes power with the intention of relinquishing it. Power is not a means; it is an end. One does not establish a dictatorship in order to safeguard a revolution; one makes the revolution in order to establish the dictatorship. The object of persecution is persecution. The object of torture is torture. The object of power is power. Now you begin to understand me.
> **- George Orwell, 1984**

## These are some tables:

[ 
=Table Header 1=Table Header 2=
|Table Cell 1|Table Cell 2|
|Table Cell 1|Table Cell 2|
|Table Cell 1|Table Cell 2|
|Table Cell 1|Table Cell 2|
|Table Cell 1|Table Cell 2|
]

[^1]: This is a footnote content.
[^@#$%]: A footnote on the label: "@#$%".
"""


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
            return f'<tr><td class="infobox-subheader" colspan="2">{line[3:]}</td></tr>'
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
        super().__init__(md)
        self.words = config.get('words', [])

    def run(self, lines):
        new_lines = []

        for line in lines:
            line = self.linkify_words(line)
            new_lines.append(line)

        return new_lines

    def linkify_words(self, line):
        # Regular expression pattern to match words within brackets '[]' or parentheses '()'
        brackets_pattern = re.compile(r'[\[\(]([^\]\)]*)[\]\)]')

        # Exclude specific words within brackets or parentheses from being turned into links
        line = re.sub(r'[\[\(]([^\]\)]*)[\]\)]', lambda x: x.group(), line)

        # Find all matches of words within brackets or parentheses
        brackets_matches = brackets_pattern.finditer(line)
        excluded_positions = set()

        # Mark positions of words within brackets or parentheses
        for match in brackets_matches:
            excluded_positions.update(range(match.start(), match.end()))

        def replace_words(match):
            start, end = match.span()
            return match.group() if any(pos in excluded_positions for pos in range(start,
                                                                                   end)) else f'<a href="/page?page={match.group()}">{match.group()}</a>'

        # Using regular expression with case-insensitive flag
        line = re.sub(rf'\b(?:{"|".join(map(re.escape, self.words))})\b', replace_words, line, flags=re.IGNORECASE)

        return line


class HeaderAdvancerExtension(markdown.postprocessors.Postprocessor):
    def run(self, text):
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('<h'):
                # Find the header tag and any additional attributes
                tag_start = line.find('<h')
                tag_end = line.find('>', tag_start)
                header_tag = line[tag_start:tag_end + 1]

                # Extract the header level using regex
                import re
                match = re.match(r'<h(\d+)', header_tag)
                if match:
                    header_level = int(match.group(1))

                    # Advance the header level by one
                    new_header_level = header_level + 1

                    # Replace the old header tag with the new one
                    new_header_tag = f'<h{new_header_level}'
                    if tag_end > tag_start:
                        new_header_tag += line[tag_end:tag_end + 1]

                    lines[i] = line.replace(header_tag, new_header_tag)

        # Join the modified lines back into the HTML
        modified_html = '\n'.join(lines)
        return modified_html


class TableExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(TableProcessor(md), 'custom_table', 30)


class TableProcessor(Preprocessor):
    def run(self, lines):
        new_lines = []
        in_table = False
        for line in lines:
            if line.strip() == '[':
                in_table = True
                new_lines.append('<div class="table-main"><table>')
            elif line.strip() == ']':
                in_table = False
                new_lines.append('</table></div>')
            elif in_table:
                processed_line = self.process_line(line)
                new_lines.append(processed_line)
            else:
                new_lines.append(line)
        return new_lines

    def process_line(self, line):
        line = line.strip()
        if line.startswith('='):
            headers = [header.strip() for header in line.split('=')]
            return self.process_table_header(headers)
        elif '|' in line:
            cells = [cell.strip() for cell in line.split('|')]
            return self.process_table_row(cells)
        else:
            return line

    def process_table_header(self, headers):
        result = "<tr>"

        for header in headers:
            if header != '':
                result += f'<th>{header}</th>'

        result += "</tr>"

        return result

    def process_table_row(self, cells):
        result = "<tr>"

        for cell in cells:
            if cell != '':
                result += f'<td>{cell}</td>'

        result += "</tr>"

        return result


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


def to_html(markdown_string, date, editor, title, page_list, role):
    link_list = page_list
    link_list.remove(title)

    md = markdown.Markdown(
        extensions=[InfoBoxExtension(), TableExtension(), TableOfContentsExtension(), LinkifyExtension(words=link_list),
                    ExtraExtension(), 'sane_lists'])
    md.postprocessors.register(HeaderAdvancerExtension(), "header_advancer", 0)
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
    """

    if role == 'admin' or role == 'editor':
        result += """
            <a href="/" class="">Home</a>
            <a href="" class="active">Page</a>
            <a href="editor?page={title}" class="nav-right">Edit</a>
            <a href="/delete-page?page={title}" class="delete">Delete</a>
        """
    else:
        result += """
                    <a href="/" class="">Home</a>
                    <a href="" class="active">Page</a>
                    <a href="" class="nav-right"></a>
                """

    result += f"""
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
        indentation = "toc-" + str(header_level - 1)  # Add indentation based on header level

        result += f'<li class={indentation}><a href="#{header_id}">{header_text}</a></li>\n'

    result += """
        </ol>
    </aside>
    <aside class="col-md-2 wiki-sidebar list-truncate">
        <h5 class="">Recently Edited Pages</h5>
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
