#!/usr/bin/env python3
"""
Preprocessor for LaTeX chapters of 代数学方法.
Expands custom macros, removes indexing commands, normalizes basic structures.

Usage: python preprocess.py <input.tex> [--output <output.tex>] [--project-root <dir>]
"""

import re
import sys
import os
import json
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = Path.cwd().resolve()


# ---------------------------------------------------------------------------
# 1. Parse \newcommand from .sty files
# ---------------------------------------------------------------------------

def find_matching_brace(s, start):
    """Return (content, end_pos) for balanced braces starting at s[start] == '{'."""
    depth = 0
    i = start
    while i < len(s):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
        elif s[i] == '\\' and i + 1 < len(s):
            i += 1  # skip next char (escaped brace, etc.)
        i += 1
    return None, len(s)


def parse_macros_from_sty(filepath):
    """Parse \\newcommand and \\renewcommand definitions from a .sty file.

    Returns dict: macro_name -> {'nargs': int, 'default': str|None, 'body': str}
    """
    macros = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to find \newcommand or \renewcommand
    pattern = re.compile(
        r'\\(?:re)?newcommand\s*\{\s*\\([A-Za-z]+)\s*\}'
        r'(?:\s*\[(\d+)\])?'
        r'(?:\s*\[([^\]]*)\])?'
        r'\s*\{'
    )

    pos = 0
    while pos < len(content):
        m = pattern.search(content, pos)
        if not m:
            break

        name = m.group(1)
        nargs = int(m.group(2)) if m.group(2) else 0
        default = m.group(3) if m.group(3) else None

        # Find the matching brace for the body
        body_start = m.end() - 1  # position of the opening {
        body, body_end = find_matching_brace(content, body_start)

        if body is not None:
            macros[name] = {
                'nargs': nargs,
                'default': default,
                'body': body.strip(),
            }
            pos = body_end
        else:
            pos = m.end()

    return macros


# ---------------------------------------------------------------------------
# 2. Macro expansion engine
# ---------------------------------------------------------------------------

def strip_ensuremath(body):
    """Strip outer \\ensuremath{...} wrapper if present."""
    b = body.strip()
    if b.startswith(r'\ensuremath{') and b.endswith('}'):
        inner, _ = find_matching_brace(b, len(r'\ensuremath') - 1)
        if inner is not None:
            return inner
    return body


def expand_macros(text, macros, max_passes=10):
    """Iteratively expand all custom macros in text.

    Handles 0-arg, 1-arg, and 2-arg macros.
    For macros with \\ensuremath, strips the wrapper.
    """
    # Sort macros by length (longest first) to avoid partial matches
    macro_names = sorted(macros.keys(), key=len, reverse=True)
    # Build regex: \macroname
    macro_pattern = re.compile(
        r'\\(%s)(?![A-Za-z])' % '|'.join(re.escape(m) for m in macro_names)
    )

    for _ in range(max_passes):
        new_text = []
        pos = 0
        changed = False

        for m in macro_pattern.finditer(text):
            name = m.group(1)
            info = macros[name]
            nargs = info['nargs']
            body = info['body']

            # Copy text before the macro
            new_text.append(text[pos:m.start()])
            end_pos = m.end()

            # Collect arguments
            args = []
            if info['default'] is not None and nargs >= 1:
                # First argument is optional
                if end_pos < len(text) and text[end_pos] == '[':
                    opt_content, opt_end = find_matching_brace(text, end_pos, is_square=True)
                    if opt_content is not None:
                        args.append(opt_content)
                        end_pos = opt_end
                    else:
                        args.append(info['default'])
                else:
                    args.append(info['default'])

            # Remaining required arguments (in braces)
            for i in range(len(args), nargs):
                if end_pos < len(text) and text[end_pos] == '{':
                    arg_content, arg_end = find_matching_brace(text, end_pos)
                    if arg_content is not None:
                        args.append(arg_content)
                        end_pos = arg_end
                    else:
                        args.append('')
                else:
                    args.append('')

            # Build expansion
            expanded = body
            for i, arg in enumerate(args):
                expanded = expanded.replace(f'#{i + 1}', arg)

            # Strip \ensuremath wrapper
            expanded = strip_ensuremath(expanded)

            new_text.append(expanded)
            pos = end_pos
            changed = True

        new_text.append(text[pos:])
        text = ''.join(new_text)

        if not changed:
            break

    return text


def find_matching_brace(s, start, is_square=False):
    """Return (content, end_pos) for balanced {} or [] starting at s[start]."""
    open_b = '[' if is_square else '{'
    close_b = ']' if is_square else '}'
    depth = 0
    i = start
    while i < len(s):
        if s[i] == open_b:
            depth += 1
        elif s[i] == close_b:
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
        elif s[i] == '\\' and i + 1 < len(s):
            i += 1
        i += 1
    return None, len(s)


# ---------------------------------------------------------------------------
# 3. Preprocessing passes
# ---------------------------------------------------------------------------

def remove_index_commands(text):
    """Remove \\index{...} and \\index[sym1]{...} commands."""
    # Handle \index{...} - single arg
    text = re.sub(r'\\index\{', '', text)
    # Handle \index[sym1]{...} - two args
    text = re.sub(r'\\index\[[^\]]*\]\{', '', text)
    # Actually, this leaves unmatched braces. Let's use a proper approach.
    return text


def remove_index_commands_proper(text):
    """Remove \\index[...]{...} commands with balanced brace handling."""
    result = []
    i = 0
    while i < len(text):
        # Match \index possibly followed by [opts] and {content}
        m = re.match(r'\\index(?:\[[^\]]*\])?', text[i:])
        if m:
            i += m.end()
            # Skip whitespace
            while i < len(text) and text[i] in ' \t':
                i += 1
            # Consume balanced braces
            if i < len(text) and text[i] == '{':
                _, end = find_matching_brace(text, i)
                if end:
                    i = end
            continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def convert_mycomm(text):
    """Convert \\mycomm{...} to %% ... %% comments."""
    result = []
    i = 0
    while i < len(text):
        m = re.match(r'\\mycomm\{', text[i:])
        if m:
            i += m.end() - 1  # point to opening brace
            content, end = find_matching_brace(text, i)
            if content is not None:
                result.append(f'%% {content} %%')
                i = end
            else:
                result.append(text[i])
                i += 1
            continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def convert_wenxintishi(text):
    """Convert \\begin{wenxintishi}...\\end{wenxintishi} to a marked block.

    This is a preliminary pass; AI will convert to proper callout format.
    """
    text = re.sub(r'\\begin\{wenxintishi\}', r'%%BEGIN_WENXINTISHI%%', text)
    text = re.sub(r'\\end\{wenxintishi\}', r'%%END_WENXINTISHI%%', text)
    return text


def normalize_whitespace(text):
    """Normalize whitespace: collapse multiple blank lines, strip trailing spaces."""
    lines = text.split('\n')
    lines = [l.rstrip() for l in lines]
    # Collapse 3+ blank lines to 2
    result = []
    blank_count = 0
    for line in lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return '\n'.join(result)


def convert_eq_to_display(text):
    """Convert \\[...\\] to $$...$$.
    Other math environments (equation, align, gather) are left for the AI pass
    since they require context-sensitive handling.
    """
    text = re.sub(r'\\\[', '$$', text)
    text = re.sub(r'\\\]', '$$', text)
    return text


def strip_boilerplate(text):
    """Remove the standard copyright comment block at the top of each chapter file."""
    lines = text.split('\n')
    # Find the first non-comment, non-empty line after the boilerplate
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == '% To be included':
            start_idx = i + 1
            break
    # Remove any leading blank lines
    while start_idx < len(lines) and lines[start_idx].strip() == '':
        start_idx += 1
    return '\n'.join(lines[start_idx:])


# ---------------------------------------------------------------------------
# 4. Chapter inventory
# ---------------------------------------------------------------------------

def get_chapter_inventory():
    """Return ordered list of (tex_path, md_name, chapter_title) for all chapters."""
    vol1_dir = PROJECT_ROOT / 'AlJabr-1'
    vol2_dir = PROJECT_ROOT / 'AlJabr-2'

    vol1_chapters = [
        ('prelude.tex',   '00-导言',           '导言'),
        ('chapter1.tex',  '01-集合论',         '集合论'),
        ('chapter2.tex',  '02-范畴论基础',     '范畴论基础'),
        ('chapter3.tex',  '03-幺半范畴',       '幺半范畴'),
        ('chapter4.tex',  '04-群论',           '群论'),
        ('chapter5.tex',  '05-环论初步',       '环论初步'),
        ('chapter6.tex',  '06-模论',           '模论'),
        ('chapter7.tex',  '07-代数初步',       '代数初步'),
        ('chapter8.tex',  '08-域扩张',         '域扩张'),
        ('chapter9.tex',  '09-Galois理论',     'Galois理论'),
        ('chapter10.tex', '10-域的赋值',       '域的赋值'),
    ]

    vol2_chapters = [
        ('prelude.tex',    '00-导言',               '导言'),
        ('chapter1.tex',   '01-范畴论拾遗',         '范畴论拾遗'),
        ('chapter2.tex',   '02-Abel范畴',           'Abel范畴'),
        ('chapter3.tex',   '03-复形',               '复形'),
        ('chapter4.tex',   '04-三角范畴与导出范畴', '三角范畴与导出范畴'),
        ('chapter5.tex',   '05-谱序列',             '谱序列'),
        ('chapter6.tex',   '06-群的同调与上同调',   '群的同调与上同调'),
        ('chapter7.tex',   '07-单子论',             '单子论'),
        ('chapter8.tex',   '08-单纯形方法',         '单纯形方法'),
        ('chapter9.tex',   '09-对偶性',             '对偶性'),
        ('appendix1.tex',  'A1-Abel范畴延伸',       '附录: Abel范畴延伸内容'),
        ('appendix2.tex',  'A2-ind对象与pro对象',   '附录: ind对象与pro对象'),
    ]

    return {
        'vol1': {'dir': vol1_dir, 'output': PROJECT_ROOT / 'output' / 'Vol1-基础结构', 'chapters': vol1_chapters},
        'vol2': {'dir': vol2_dir, 'output': PROJECT_ROOT / 'output' / 'Vol2-线性代数', 'chapters': vol2_chapters},
    }


# ---------------------------------------------------------------------------
# 5. Label extraction
# ---------------------------------------------------------------------------

def extract_labels(filepath):
    """Extract all \\label{...} from a file. Returns list of labels."""
    labels = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    pos = 0
    while True:
        m = re.search(r'\\label\{([^}]+)\}', content[pos:])
        if not m:
            break
        labels.append(m.group(1))
        pos += m.end()
    return labels


def build_label_map():
    """Build a global label->blockID mapping for all chapters."""
    inventory = get_chapter_inventory()
    label_map = {}

    for vol_key in ['vol1', 'vol2']:
        vol = inventory[vol_key]
        for tex_name, md_name, _ in vol['chapters']:
            tex_path = vol['dir'] / tex_name
            if tex_path.exists():
                labels = extract_labels(tex_path)
                for label in labels:
                    # Generate block ID
                    block_id = label_to_block_id(label)
                    label_map[label] = {
                        'file': md_name + '.md',
                        'block_id': block_id,
                        'volume': vol_key,
                    }

    return label_map


def label_to_block_id(label):
    """Convert a LaTeX label like 'prop:wellorder-automorphism' to a block ID like '^prop-wellorder-automorphism'."""
    # Remove common prefixes already in the type prefix
    # e.g., prop:AW-approx -> ^prop-AW-approx
    #       sec:ZFC -> ^sec-ZFC
    #       def:partial-order -> ^def-partial-order
    #       eqn:infinity-axiom -> ^eqn-infinity-axiom
    label_clean = label.replace(':', '-')
    return f'^{label_clean}'


# ---------------------------------------------------------------------------
# 6. Main processing
# ---------------------------------------------------------------------------

def load_macros():
    """Load and merge macros from both volumes' mycommand.sty."""
    macros = {}
    sty_files = [
        PROJECT_ROOT / 'AlJabr-1' / 'mycommand.sty',
        PROJECT_ROOT / 'AlJabr-2' / 'mycommand.sty',
    ]
    for sty_file in sty_files:
        if sty_file.exists():
            new_macros = parse_macros_from_sty(str(sty_file))
            macros.update(new_macros)  # Vol 2 overrides Vol 1 where they conflict
    return macros


def preprocess_file(filepath, macros):
    """Run all preprocessing passes on a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # Pass 0: Strip copyright boilerplate
    text = strip_boilerplate(text)

    # Pass 1: Convert mycomm
    text = convert_mycomm(text)

    # Pass 2: Remove index commands
    text = remove_index_commands_proper(text)

    # Pass 3: Expand custom macros
    text = expand_macros(text, macros)

    # Pass 4: Basic equation environment conversion
    text = convert_eq_to_display(text)

    # Pass 5: Mark wenxintishi blocks
    text = convert_wenxintishi(text)

    # Pass 6: Normalize whitespace
    text = normalize_whitespace(text)

    return text


def process_all(macros, dry_run=False):
    """Preprocess all chapter files."""
    inventory = get_chapter_inventory()

    for vol_key in ['vol1', 'vol2']:
        vol = inventory[vol_key]
        for tex_name, md_name, _ in vol['chapters']:
            tex_path = vol['dir'] / tex_name
            if not tex_path.exists():
                print(f"  SKIP (not found): {tex_path}")
                continue

            print(f"  Processing: {tex_name} -> {md_name}.tex")
            processed = preprocess_file(str(tex_path), macros)

            out_path = vol['output'] / f'{md_name}.tex'
            if not dry_run:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(processed, encoding='utf-8')
                print(f"    Wrote: {out_path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Preprocess LaTeX chapters for AI conversion')
    parser.add_argument('input', nargs='?', help='Single .tex file to process')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--all', action='store_true', help='Process all chapters')
    parser.add_argument('--dry-run', action='store_true', help='Validate without writing')
    parser.add_argument('--build-labels', action='store_true', help='Build label_map.json')
    parser.add_argument('--show-macros', action='store_true', help='Show parsed macro count')
    parser.add_argument('--project-root', help='Project root containing AlJabr-1/AlJabr-2 and output; defaults to the current working directory')

    args = parser.parse_args()

    PROJECT_ROOT = Path(args.project_root).resolve() if args.project_root else Path.cwd().resolve()

    print(f"Project root: {PROJECT_ROOT}")
    print("Loading macros from mycommand.sty...")
    macros = load_macros()

    if args.show_macros:
        print(f"Loaded {len(macros)} macros:")
        for name in sorted(macros.keys()):
            info = macros[name]
            print(f"  \\{name}[{info['nargs']}] -> {info['body'][:80]}")
        sys.exit(0)

    if args.build_labels:
        print("Building label map...")
        label_map = build_label_map()
        out_path = PROJECT_ROOT / 'output' / 'label_map.json'
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(label_map, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"Wrote {len(label_map)} labels to {out_path}")
        sys.exit(0)

    if args.all:
        print("Processing all chapters...")
        process_all(macros, dry_run=args.dry_run)
    elif args.input:
        print(f"Processing: {args.input}")
        processed = preprocess_file(args.input, macros)
        if args.output:
            Path(args.output).write_text(processed, encoding='utf-8')
            print(f"Wrote: {args.output}")
        else:
            # Print to stdout (for piping)
            print(processed)
    else:
        parser.print_help()

