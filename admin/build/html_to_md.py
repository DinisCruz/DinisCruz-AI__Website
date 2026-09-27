"""HTML -> markdown converter for the hand-written pages' markdown twins.

Adapted from open-source.sgit.ai's admin/build/gen_markdown.py (same author, same
design language). It handles only the tag vocabulary these pages use, on purpose:
a general converter would be a dependency. Pages generated from content/ do not
go through this — their twin is written straight from the source markdown.
"""
import html
import re
from html.parser import HTMLParser

BLOCK = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "tr", "blockquote", "pre",
         "div", "section", "header", "main", "table", "thead", "tbody", "ul", "ol"}
SKIP = {"script", "style", "nav", "footer", "head", "button", "svg"}


class Node:
    __slots__ = ("tag", "attrs", "kids", "text")

    def __init__(self, tag, attrs=None, text=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.kids = []
        self.text = text

    def cls(self):
        return self.attrs.get("class", "").split()


class Tree(HTMLParser):
    """Builds a tree of the body, dropping anything in SKIP entirely."""

    VOID = {"br", "hr", "img", "meta", "link", "input", "source"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]
        self.skip_depth = 0
        self.in_body = False

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.in_body = True
            return
        if self.skip_depth:
            if tag not in self.VOID:
                self.skip_depth += 1
            return
        if tag in SKIP:
            self.skip_depth = 1
            return
        if not self.in_body:
            return
        node = Node(tag, {k: (v or "") for k, v in attrs})
        self.stack[-1].kids.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False
            return
        if self.skip_depth:
            self.skip_depth -= 1
            return
        if tag in self.VOID or not self.in_body:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.skip_depth or not self.in_body or not data.strip():
            return
        self.stack[-1].kids.append(Node("#text", text=data))


def md_escape(s):
    # Only the characters that would change meaning mid-sentence. Deliberately not
    # aggressive: over-escaping makes the markdown twin unpleasant to read, and a
    # reader — human or agent — is the point.
    return s.replace("|", "\\|")


def rel_md(href, from_rel):
    """Rewrite an internal .html link to its .md twin. This is the rule that keeps a
    traversing agent on the markdown surface: it arrives at one .md and every link it
    finds is another .md."""
    if re.match(r"^(https?:|mailto:|data:|//|#)", href):
        return href
    path, _, frag = href.partition("#")
    if path.endswith(".html"):
        path = path[:-len("html")] + "md"
    return path + ("#" + frag if frag else "")


def inline(node, from_rel):
    """Render inline content. Returns a string with no newlines."""
    if node.tag == "#text":
        return md_escape(re.sub(r"\s+", " ", node.text))
    inner = "".join(inline(k, from_rel) for k in node.kids)
    t = node.tag
    if t in ("b", "strong"):
        return f"**{inner.strip()}**" if inner.strip() else ""
    if t in ("em", "i"):
        return f"*{inner.strip()}*" if inner.strip() else ""
    if t == "code":
        return f"`{inner.strip()}`"
    if t == "br":
        return " "
    if t == "a":
        href = node.attrs.get("href", "")
        text = inner.strip()
        if not text:
            return ""
        return f"[{text}]({rel_md(href, from_rel)})"
    return inner


def cell(node, from_rel):
    return " ".join("".join(inline(k, from_rel) for k in node.kids).split()).strip()


# Anything not listed here is inline, and a RUN of inline siblings has to be
# emitted as one paragraph rather than one block each. Rendering them separately
# is what turned "<blockquote>text <b>emphasis</b> text</blockquote>" into three
# stacked block quotes — correct-looking HTML, unreadable markdown.
INLINE_TAGS = {"#text", "a", "b", "strong", "em", "i", "code", "span", "br", "small", "sup", "sub"}


def render_children(node, from_rel, out, depth=0):
    """Render a container's children, grouping consecutive inline siblings into one
    paragraph and recursing into the block ones."""
    run = []

    def flush():
        if not run:
            return
        text = " ".join("".join(run).split()).strip()
        run.clear()
        if text:
            out.append(text)

    for k in node.kids:
        # A card is a block whatever tag carries it — and it is usually carried by
        # <a>, which is otherwise inline. Checking the class first is what stops a
        # linked card being swallowed into the surrounding paragraph as one long
        # link label.
        if k.tag in INLINE_TAGS and "card" not in k.cls():
            run.append(inline(k, from_rel))
        else:
            flush()
            render(k, from_rel, out, depth)
    flush()


def render_card(node, from_rel, out, depth=0):
    """A card: an eyebrow <span class="tag">, a heading, a paragraph, and — when the
    card is itself a link — a "Read →" affordance. Rendered as a small titled block
    so the markdown keeps the grouping the layout expresses visually."""
    label = next((" ".join(inline(k, from_rel).split()).strip()
                  for k in node.kids if k.tag == "span" and "tag" in k.cls()), "")
    href = node.attrs.get("href")
    body = Node("div")
    # The eyebrow is emitted as the label and the "go" chevron is pure navigation;
    # neither belongs in the flow.
    body.kids = [k for k in node.kids
                 if not (k.tag == "span" and ("tag" in k.cls() or "go" in k.cls()))]
    buf = []
    render_children(body, from_rel, buf, depth)
    blocks = [b for b in buf if b.strip()]
    if not blocks:
        return
    # Promote the card's heading to a linked heading when the whole card is a link,
    # so a reader of the markdown can still follow where the card pointed.
    head = blocks[0]
    if head.startswith("#"):
        hashes, _, text = head.partition(" ")
        if href:
            text = f"[{text}]({rel_md(href, from_rel)})"
        blocks[0] = f"{hashes} {text}"
    elif href:
        blocks[0] = f"[{head}]({rel_md(href, from_rel)})"
    if label:
        blocks.insert(1 if blocks[0].startswith("#") else 0, f"*{label}*")
    out.extend(blocks)


def render(node, from_rel, out, depth=0):
    """Walk the tree emitting markdown blocks into `out`."""
    t = node.tag

    # A card is a self-contained unit and it is written BOTH as <div class="card">
    # and as <a class="card" href="..."> — the linked form being the common one. So
    # dispatch on the class before the tag, or the anchor branch below flattens the
    # whole card (heading, body, affordance) into a single link label.
    if "card" in node.cls():
        render_card(node, from_rel, out, depth)
        return

    if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
        text = " ".join(inline(node, from_rel).split()).strip()
        if text:
            out.append("#" * int(t[1]) + " " + text)
        return

    if t == "p":
        text = " ".join(inline(node, from_rel).split()).strip()
        if text:
            # The card "Read →" affordances are navigation, not prose; the link
            # itself is already emitted by the card's own heading.
            out.append(text)
        return

    if t == "blockquote":
        buf = []
        render_children(node, from_rel, buf, depth)
        body = "\n\n".join(b for b in buf if b.strip())
        if body:
            out.append("\n".join("> " + line if line else ">" for line in body.split("\n")))
        return

    if t == "pre":
        raw = "".join(_flatten_text(k) for k in node.kids).strip("\n")
        if raw.strip():
            out.append("```\n" + raw + "\n```")
        return

    if t in ("ul", "ol"):
        marker = (lambda i: "- ") if t == "ul" else (lambda i: f"{i}. ")
        items = []
        n = 0
        for k in node.kids:
            if k.tag != "li":
                continue
            n += 1
            buf = []
            render_children(k, from_rel, buf, depth + 1)
            body = "\n\n".join(b for b in buf if b.strip())
            if body:
                pad = " " * len(marker(n))
                lines = body.split("\n")
                items.append(marker(n) + lines[0] + "".join("\n" + (pad + l if l else "")
                                                            for l in lines[1:]))
        if items:
            out.append("\n".join(items))
        return

    if t == "table":
        rows = []
        head = None
        for tr in _find(node, "tr"):
            cells = [cell(c, from_rel) for c in tr.kids if c.tag in ("th", "td")]
            if not cells:
                continue
            if head is None and any(c.tag == "th" for c in tr.kids):
                head = cells
            else:
                rows.append(cells)
        if head is None and rows:
            head = [""] * len(rows[0])
        if head:
            width = max([len(head)] + [len(r) for r in rows]) if rows else len(head)
            head = head + [""] * (width - len(head))
            lines = ["| " + " | ".join(head) + " |",
                     "|" + "|".join(["---"] * width) + "|"]
            for r in rows:
                r = r + [""] * (width - len(r))
                lines.append("| " + " | ".join(r) + " |")
            out.append("\n".join(lines))
        return

    if t in ("div", "section", "header", "main", "thead", "tbody", "#root", "span"):
        # A .card is a self-contained unit whose <span class="tag"> is its label.
        classes = node.cls()
        if "note" in classes or "warnbox" in classes or "evbox" in classes:
            buf = []
            render_children(node, from_rel, buf, depth)
            body = "\n\n".join(b for b in buf if b.strip())
            if body:
                out.append("\n".join("> " + l if l else ">" for l in body.split("\n")))
            return
        if "crumb" in classes:
            return
        render_children(node, from_rel, out, depth)
        return

    if t == "#text":
        text = " ".join(md_escape(node.text).split()).strip()
        if text:
            out.append(text)
        return

    if t == "a":
        # A bare anchor at block level (a .cta, say) — emit it as a line.
        text = inline(node, from_rel).strip()
        if text:
            out.append(text)
        return

    render_children(node, from_rel, out, depth)


def _flatten_text(node):
    if node.tag == "#text":
        return node.text
    return "".join(_flatten_text(k) for k in node.kids)


def _find(node, tag, out=None):
    out = [] if out is None else out
    for k in node.kids:
        if k.tag == tag:
            out.append(k)
        else:
            _find(k, tag, out)
    return out


def page_title(source):
    m = re.search(r"<title>(.*?)</title>", source, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def page_description(source):
    m = re.search(r'<meta name="description" content="([^"]*)"', source)
    return html.unescape(m.group(1)).strip() if m else ""

