#!/usr/bin/env python3
"""Validate converted Obsidian markdown files for common issues."""

import sys
import re
from pathlib import Path


def strip_fenced_code(text):
    """Replace fenced code blocks with blanks while preserving line numbers."""
    lines = text.splitlines()
    out = []
    in_fence = False
    for line in lines:
        if line.strip().startswith('```'):
            in_fence = not in_fence
            out.append('')
        elif in_fence:
            out.append('')
        else:
            out.append(line)
    return '\n'.join(out)


def strip_display_math(text):
    """Replace $$...$$ blocks with blanks while preserving line numbers."""
    lines = text.splitlines()
    out = []
    in_math = False
    for line in lines:
        count = line.count('$$')
        if in_math:
            out.append('')
            if count % 2 == 1:
                in_math = False
        elif count >= 2:
            out.append('')
        elif count == 1:
            in_math = True
            out.append('')
        else:
            out.append(line)
    return '\n'.join(out)


def text_for_plain_checks(text):
    return strip_display_math(strip_fenced_code(text))


def strip_inline_math(text):
    """Replace single-line $...$ spans with blanks, preserving line numbers."""
    return re.sub(r'(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$)', '', text)


def check_dollar_balance(text):
    """Check that $ and $$ are properly paired."""
    dd_count = text.count('$$')
    if dd_count % 2 != 0:
        return False, f"Unbalanced $$ (count={dd_count})"
    temp = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    inline = temp.count('$')
    if inline % 2 != 0:
        return False, f"Unbalanced inline $ (count={inline})"
    return True, "OK"


def check_callout_balance(text):
    """Check that > [!...] blocks are properly formed."""
    lines = text.split('\n')
    in_callout = False
    issues = []
    for i, line in enumerate(lines, 1):
        if re.match(r'>\s*\[!', line):
            if in_callout:
                issues.append(f"Line {i}: nested callout start")
            in_callout = True
        elif in_callout and line.strip() == '':
            in_callout = False
        elif in_callout and not line.startswith('>'):
            in_callout = False
    return len(issues) == 0, issues


def check_residual_latex(text):
    """Check for unconverted LaTeX commands outside code blocks."""
    plain = text_for_plain_checks(text)
    env_plain = strip_inline_math(plain)
    groups = [
        (env_plain, [(r'\\begin\{', '\\begin{...}'), (r'\\end\{', '\\end{...}')]),
        (plain, [
            (r'\\index\{', '\\index'),
            (r'\\ref\{', '\\ref'),
            (r'\\eqref\{', '\\eqref'),
            (r'\\cite\{', '\\cite'),
            (r'\\label\{', '\\label'),
            (r'\\(?:re)?newcommand', '\\newcommand'),
        ]),
    ]
    issues = []
    for source, patterns in groups:
        for pattern, name in patterns:
            matches = list(re.finditer(pattern, source))
            for m in matches:
                line_num = source[:m.start()].count('\n') + 1
                issues.append(f"Line {line_num}: residual {name}")
    return len(issues) == 0, issues


def check_custom_macros(text):
    """Check for unexpanded project-specific custom macros outside math/code blocks."""
    plain = text_for_plain_checks(text)
    custom = [
        r'\\N\b', r'\\Z\b', r'\\Q\b', r'\\R\b', r'\\CC\b', r'\\F\b', r'\\A\b',
        r'\\cate\{', r'\\dcate\{', r'\\cated\{',
        r'\\rightiso\b', r'\\leftiso\b',
        r'\\lrangle\{',
        r'\\munit\b', r'\\identity\b',
    ]
    issues = []
    for pattern in custom:
        matches = list(re.finditer(pattern, plain))
        for m in matches:
            line_num = plain[:m.start()].count('\n') + 1
            issues.append(f"Line {line_num}: unexpanded macro {m.group()}")
    return len(issues) == 0, issues


def validate_file(filepath):
    """Run all checks on a markdown file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    results = {}
    for name, check_fn in [
        ('$ balance', check_dollar_balance),
        ('callout balance', check_callout_balance),
        ('residual LaTeX', check_residual_latex),
        ('custom macros', check_custom_macros),
    ]:
        ok, detail = check_fn(text)
        results[name] = (ok, detail)

    return results


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python validate.py <file.md> [file2.md ...]")
        sys.exit(1)

    all_ok = True
    for filepath in sys.argv[1:]:
        p = Path(filepath)
        if not p.exists():
            print(f"SKIP {filepath}: not found")
            continue
        print(f"\n{'='*60}")
        print(f"Checking: {p.name}")
        print(f"{'='*60}")
        results = validate_file(str(p))
        for check, (ok, detail) in results.items():
            status = "OK" if ok else "FAIL"
            print(f"  [{status}] {check}")
            if not ok:
                all_ok = False
                if isinstance(detail, list):
                    for issue in detail[:10]:
                        print(f"    - {issue}")
                else:
                    print(f"    - {detail}")

    if all_ok:
        print("\nAll checks passed.")
    else:
        print("\nSome checks failed.")
        sys.exit(1)


