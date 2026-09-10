import os
import re
import sys
import yaml
import zipfile
import io
import pandas as pd


def _log(message):
    """
    Emit a diagnostic without ever failing the caller.

    Under Passenger sys.stdout can be ASCII-encoded (no LANG in the app's
    environment), so printing a note name containing e.g. an en-dash raises
    UnicodeEncodeError. The API wraps parsing in `except Exception`, so an
    unprintable filename would otherwise surface to the user as a 400.
    """
    try:
        print(message)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, 'encoding', None) or 'ascii'
        try:
            print(message.encode(enc, 'replace').decode(enc, 'replace'))
        except Exception:
            pass
    except Exception:
        pass


def parse_markdown_content(content):
    """Parse YAML frontmatter and ## Description section from a markdown string."""
    frontmatter = {}
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if fm_match:
        try:
            frontmatter = yaml.safe_load(fm_match.group(1)) or {}
        except Exception:
            pass
        content = content[fm_match.end():]

    description = ""
    desc_match = re.search(r'## Description\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL | re.IGNORECASE)
    if desc_match:
        description = desc_match.group(1).strip()

    return frontmatter, description


def _decode(raw_bytes):
    """Decode bytes to str, falling back to Latin-1 if not valid UTF-8."""
    try:
        return raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return raw_bytes.decode('latin-1')


def parse_markdown_file(filepath):
    """Read a markdown file from disk and parse it."""
    try:
        with open(filepath, 'rb') as f:
            return parse_markdown_content(_decode(f.read()))
    except Exception as e:
        _log(f"Error reading {filepath}: {e}")
        return {}, ""


def clean_link(value):
    """Strip Obsidian [[ ]] link syntax."""
    if isinstance(value, str):
        return value.replace('[[', '').replace(']]', '').strip('"').strip("'")
    return value


def _clean_tag_list(value):
    """
    Normalize a frontmatter `tags:` value into a list of valid tag names.

    Obsidian writes tags as a YAML list, but hand-edited notes produce shapes
    that would otherwise reach the tag filter as bogus chips:
      - an empty list item parses as None, which str() renders as the tag "None"
      - a leading '#' makes '#nutrients' a separate chip from 'nutrients'
      - an embedded comma splits into two fake tags downstream, because tags
        travel to core.parse_tags comma-joined
    Duplicates are dropped while preserving the order the vault declares them.
    """
    if value is None:
        return []

    items = value if isinstance(value, (list, tuple)) else [value]

    tags = []
    for item in items:
        if item is None:
            continue
        for part in str(item).split(','):
            tag = part.strip().lstrip('#').strip()
            if tag and tag not in tags:
                tags.append(tag)
    return tags


def _tags_to_str(value):
    return ", ".join(_clean_tag_list(value))


def _build_edges_df(actor_paths, instrument_paths, interlinkage_paths, read_fn):
    """
    Build an edges DataFrame from collections of markdown file paths.
    read_fn(path) -> str  returns the file content for a given path.
    """
    nodes = {}

    for path in actor_paths:
        name = os.path.splitext(os.path.basename(path))[0]
        fm, desc = parse_markdown_content(read_fn(path))
        nodes[name] = {
            "type": fm.get("type", "actor"),
            "layer": fm.get("level", "unknown"),
            "tags": fm.get("tags", []),
            "description": desc
        }

    for path in instrument_paths:
        name = os.path.splitext(os.path.basename(path))[0]
        fm, desc = parse_markdown_content(read_fn(path))
        nodes[name] = {
            "type": fm.get("type", "instrument"),
            "layer": fm.get("level", "unknown"),
            "tags": fm.get("tags", []),
            "description": desc
        }

    rows = []
    node_descriptions_used = set()

    for path in interlinkage_paths:
        fm, edge_desc = parse_markdown_content(read_fn(path))
        source_name = clean_link(fm.get("from"))
        target_name = clean_link(fm.get("to"))

        if not source_name or not target_name:
            _log(f"Skipping {os.path.basename(path)}: missing 'from' or 'to'.")
            continue

        src = nodes.get(source_name, {"type": "unknown", "layer": "unknown", "tags": [], "description": ""})
        tgt = nodes.get(target_name, {"type": "unknown", "layer": "unknown", "tags": [], "description": ""})

        node_desc = ""
        if source_name not in node_descriptions_used and src["description"]:
            node_desc = f"{source_name}: {src['description']}"
            node_descriptions_used.add(source_name)

        rows.append({
            "source": source_name,
            "source_layer": src["layer"],
            "source_type": src["type"],
            "source_tags": _tags_to_str(src.get("tags", [])),
            "target": target_name,
            "target_layer": tgt["layer"],
            "target_type": tgt["type"],
            "target_tags": _tags_to_str(tgt.get("tags", [])),
            "edge_tags": _tags_to_str(fm.get("tags", [])),
            "description": edge_desc,
            "node_description": node_desc
        })

    return pd.DataFrame(rows)


def parse_obsidian_dir(base_dir):
    """Parse an Obsidian vault from a directory. Returns edges DataFrame."""
    def get_md(directory):
        if not os.path.isdir(directory):
            return []
        return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.md')]

    def read_fn(path):
        with open(path, 'rb') as f:
            return _decode(f.read())

    return _build_edges_df(
        get_md(os.path.join(base_dir, "1 Node - Actors")),
        get_md(os.path.join(base_dir, "2 Node - Instruments")),
        get_md(os.path.join(base_dir, "10 Interlinkages")),
        read_fn
    )


def _zip_entry_name(info):
    """
    Recover the true UTF-8 name of a ZIP entry.

    Archivers that don't set the UTF-8 flag (general-purpose bit 11) store
    names in CP437, and zipfile decodes them as such -- turning an en-dash
    into 'ΓÇô'. Node names come from filenames while [[links]] come from
    UTF-8 file *content*, so a mangled filename silently fails to match its
    interlinkages and the node falls back to layer/type 'unknown'.
    """
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode('cp437').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def _is_macos_metadata(name):
    """
    True for macOS archive cruft, which is not a real note.

    `zip` on macOS adds a '__MACOSX/' tree and a '._<name>' AppleDouble
    sidecar per file. The sidecars have no frontmatter, so they'd otherwise
    be reported as interlinkages 'missing from or to'.
    """
    return name.startswith('__MACOSX/') or os.path.basename(name).startswith('._')


def parse_obsidian_zip(zip_bytes):
    """
    Parse an Obsidian vault from a ZIP file. Returns edges DataFrame.
    The ZIP may contain any top-level folder; directories are matched
    case-insensitively by name fragment (actors / instruments / interlinkages).
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Keep the recovered name -> entry mapping: zf.read() needs the
        # original (possibly CP437-mangled) name to look the member up.
        entries = {}
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = _zip_entry_name(info)
            if name.endswith('.md') and not _is_macos_metadata(name):
                entries[name] = info

        names = list(entries)
        actor_paths = [n for n in names if 'actors' in n.lower()]
        instrument_paths = [n for n in names if 'instruments' in n.lower()]
        interlinkage_paths = [n for n in names if 'interlinkages' in n.lower()]

        def read_fn(path):
            return _decode(zf.read(entries[path]))

        return _build_edges_df(actor_paths, instrument_paths, interlinkage_paths, read_fn)


def main():
    base_dir = "Obsidian Files"
    df = parse_obsidian_dir(base_dir)
    output_file = "parsed_data.csv"
    df.to_csv(output_file, index=False)
    print(f"Successfully created {output_file} with {len(df)} interlinkages.")


if __name__ == "__main__":
    main()
