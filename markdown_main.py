import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("markdown")

DEFAULT_MARKDOWN = """
{
# Simple Overview
## I <3 Infoboxes
Property 1 | Value 1
Property 2 | Value 2
Property 3 | Value 3
### Important Category
Property 4 | Value 4
Property 5 | Value 5
}

# Subheader

One

Here is some regular text.

*This is bolded text*

_This is emphasis?_

## Here is a title

Here is some more text.

### Here is a subtitle

Here is even more text.

### Here is another subtitle

Here is even more text. But again.

## Here is another title

I love examples yay!

# Various important segments

`This is a code block` Something in between them `And here's another code block`
> This is a block quote! Useful for fancy stuff.

~~Here is some struck through text~~

1. This
2. Is
3. An
4. Ordered
5. List

- This
- Is
- An
- Unordered
- List

First Header  | Second Header
------------- | -------------
Content Cell  | Content Cell
Content Cell  | Content Cell

# References

Thorough overview of the markdown format. Will add functionality for colored text/table cells and footnotes someday!

Feel free to edit and expand upon this wiki page as needed!

"""


def linkify(input_string, words):
    # regular expression pattern to match <a> tags and their attributes
    a_tag_pattern = re.compile(r'<a\b[^>]*>.*?</a>', re.DOTALL | re.IGNORECASE)

    # find all matches of <a> tags and their attributes
    a_tag_matches = a_tag_pattern.finditer(input_string)
    excluded_positions = set()

    # mark positions of existing <a> tags and their content
    for match in a_tag_matches:
        excluded_positions.update(range(match.start(), match.end()))

    # function to handle replacement, excluding positions within existing <a> tags
    def replace_words(match):
        start, end = match.span()
        return match.group() if any(pos in excluded_positions for pos in range(start, end)) else f'<a href="/page?page={match.group()}">{match.group()}</a>'

    # using regular expression with case-insensitive flag
    input_string = re.sub(rf'\b(?:{"|".join(map(re.escape, words))})\b', replace_words, input_string, flags=re.IGNORECASE)

    return input_string


def transform_to_html(lines, date, editor, title, recent_pages):
    result = []
    table_of_contents = []
    inside_infobox = False
    unordered_list_active = False
    ordered_list_active = False
    table_active = False
    hit_object = False

    # Add unique id to the header tag (stripped content without spaces)
    header_id = title.replace(" ", "")

    # TODO: Add in the lasted edited date string from the database.
    result.append(f"""
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
    """)

    for line in lines:
        if not line.strip():  # Ignore blank lines
            continue

        hit_object = False

        # LIST SYNTAX
        if line[0].isdigit() and "." in line:
            hit_object = True
            # Line begins with a number and a period, create an ordered list
            number, content = line.split(".", 1)
            if not ordered_list_active:
                if unordered_list_active:
                    result.append("</ul>")

                result.append("<ol>")
                ordered_list_active = True
                unordered_list_active = False

            result.append(f"    <li>{linkify(content.strip(), recent_pages)}</li>")
        elif line.startswith("-"):
            hit_object = True
            # Line begins with a single dash '-', create an unordered list
            if not unordered_list_active:
                if ordered_list_active:
                    result.append("</ol>")

                result.append("<ul>")
                ordered_list_active = False
                unordered_list_active = True
            result.append(f"    <li>{linkify(line[1:].strip(), recent_pages)}</li>")
        else:
            # End any ongoing lists if an empty line is encountered
            if ordered_list_active or unordered_list_active:
                result.append("</ol>" if ordered_list_active else "</ul>")
                ordered_list_active = False
                unordered_list_active = False

        # TABLE SYNTAX
        if line.startswith("|") and "|" in line:
            hit_object = True

            if not table_active:
                result.append('<div class="table-main"><table>')
                table_active = True
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                table_row = (
                        "    <tr>"
                        + "".join(
                    [f"<th>{cell}</th>" for cell in cells if cell.strip() != ""]
                )
                        + "</tr>"
                )
            else:
                # Line starts with "|" and contains at least one more "|", treat as a table row
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                table_row = (
                        "    <tr>"
                        + "".join(
                    [f"<td>{linkify(cell, recent_pages)}</td>" for cell in cells if cell.strip() != ""]
                )
                        + "</tr>"
                )
            result.append(table_row)
        elif table_active:
            result.append("</table></div>")
            table_active = False

        # INFOBOX
        if line.strip() == "[":
            # Start of infobox section
            result.append('<table class="infobox">\n    <tbody>')
            inside_infobox = True
        elif line.strip() == "]":
            # End of infobox section
            result.append("    </tbody>\n</table>")
            inside_infobox = False
        elif inside_infobox:
            # Infobox rules
            if line.startswith("# "):
                stripped_line = line.lstrip("# ").strip()
                result.append(
                    f'        <tr><th class="infobox-above" colspan="2">{stripped_line}</th></tr>'
                )
            elif line.startswith("## "):
                stripped_line = line.lstrip("## ").strip()
                result.append(
                    f'        <tr><td class="infobox-subheader" colspan="2">{stripped_line}</td></tr>'
                )
            elif line.startswith("### "):
                stripped_line = line.lstrip("### ").strip()
                result.append(
                    f'        <tr><th class="infobox-subtitle" colspan="2">{stripped_line}</th></tr>'
                )
            elif "|" in line:
                items = [item.strip() for item in line.split("|")]
                if len(items) == 2:
                    result.append(
                        f'        <tr><th scope="row" class="infobox-label">{items[0]}</th><td class="infobox-data">{linkify(items[1], recent_pages)}</td></tr>'
                    )
            else:
                result.append(
                    f'        <tr><th scope="row" class="infobox-label" colspan="2">{line.strip()}</th></tr>'
                )
        else:
            # GENERAL SYNTAX
            if line.startswith("#"):
                # Count the number of hashtags at the beginning of the line
                num_hashtags = line.count("#")

                # Identify the header level and remove hashtags and spaces
                header_level = min(num_hashtags, 5)  # Limit to h1 to h5
                stripped_line = line.lstrip("# ").strip()

                # Add unique id to the header tag (stripped content without spaces)
                header_id = stripped_line.replace(" ", "")

                # Transform the line to HTML and append to the result
                transformed_line = f'<h{header_level + 1} id="{header_id}">{stripped_line}</h{header_level}>'
                result.append(transformed_line)

                # Add header information to the table of contents
                table_of_contents.append((stripped_line, header_level, header_id))
            elif line.startswith(">"):
                transformed_line = f"<blockquote>{line.strip()}</blockquote>".replace(
                    "> ", ""
                )
                result.append(transformed_line)
            elif line.strip() == "---":
                # Line containing only '---', transform into <hr> tag
                transformed_line = "<hr>"
                result.append(transformed_line)

            elif not hit_object:
                # Wrap other lines in a <p> tag without new lines
                transformed_line = f"<p>{linkify(line.strip(), recent_pages)}</p>"

                # Handling italics, bolds, code, and strikethrough
                while '*' in transformed_line or '`' in transformed_line or '~~' in transformed_line:
                    if '**' in transformed_line:
                        start_bold = transformed_line.find('**')
                        end_bold = transformed_line.find('**', start_bold + 2)
                        if start_bold != -1 and end_bold != -1:
                            transformed_line = (
                                    transformed_line[:start_bold] +
                                    f"<strong>{transformed_line[start_bold + 2:end_bold]}</strong>" +
                                    transformed_line[end_bold + 2:]
                            )
                        else:
                            break  # If no closing '**' found, exit loop
                    elif '*' in transformed_line:
                        start_italic = transformed_line.find('*')
                        end_italic = transformed_line.find('*', start_italic + 1)
                        if start_italic != -1 and end_italic != -1:
                            transformed_line = (
                                    transformed_line[:start_italic] +
                                    f"<em>{transformed_line[start_italic + 1:end_italic]}</em>" +
                                    transformed_line[end_italic + 1:]
                            )
                        else:
                            break  # If no closing '*' found, exit loop
                    elif '`' in transformed_line:
                        start_code = transformed_line.find('`')
                        end_code = transformed_line.find('`', start_code + 1)
                        if start_code != -1 and end_code != -1:
                            code_content = transformed_line[start_code + 1:end_code]
                            transformed_line = (
                                    transformed_line[:start_code] +
                                    f"<code>{code_content}</code>" +
                                    transformed_line[end_code + 1:]
                            )
                        else:
                            break  # If no closing '`' found, exit loop
                    elif '~~' in transformed_line:
                        start_strikethrough = transformed_line.find('~~')
                        end_strikethrough = transformed_line.find('~~', start_strikethrough + 2)
                        if start_strikethrough != -1 and end_strikethrough != -1:
                            strikethrough_content = transformed_line[start_strikethrough + 2:end_strikethrough]
                            transformed_line = (
                                    transformed_line[:start_strikethrough] +
                                    f"<s>{strikethrough_content}</s>" +
                                    transformed_line[end_strikethrough + 2:]
                            )
                        else:
                            break  # If no closing '~~' found, exit loop
                    else:
                        # If none of the special characters are found, treat as a regular line
                        transformed_line = f"<p>{linkify(transformed_line.strip(), recent_pages)}</p>"
                        break  # Exit loop to avoid appending multiple <p> tags

                # Append the transformed line after handling special characters
                result.append(transformed_line)

    result.append('</div></div>')

    result.append("""
    <aside class="order-first col-md-2 wiki-sidebar list-truncate">
        <h5 class="">Contents</h5>
        <hr class="no-margin pb-2">
        <ol class="list-unstyled mb-0">
    """)

    for entry in table_of_contents:
        header_text, header_level, header_id = entry
        indentation = "toc-" + str(header_level - 2)  # Add indentation based on header level

        result.append(f'        <li class={indentation}><a href="#{header_id}">{header_text}</a></li>\n')

    result.append("""
        </ol>
    </aside>
    <aside class="col-md-2 wiki-sidebar list-truncate">
        <h5 class="">Recent Pages</h5>
        <hr class="no-margin pb-2">
        <ol class="list-unstyled mb-0">
    """)

    for i in range(15 if len(recent_pages) > 15 else len(recent_pages)):
        result.append(f'        <li><a href="/page?page={recent_pages[i]}">{recent_pages[i]}</a></li>\n')

    result.append("""
        </ol>
    </aside>
    </div>
    """)

    # Join the lines to form the transformed string
    transformed_string = "\n".join(result)

    return transformed_string
