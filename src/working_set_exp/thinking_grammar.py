"""Compose an eager final grammar with the pinned, already-open thinking block.

This is a transport envelope, not a reasoning budget or private-output parser.
The caller must verify the native prompt suffix with require_open_thinking().
The endpoint remains responsible for separating reasoning from final content.
"""
import re

OPEN_SUFFIX = b'<|im_start|>assistant\n<think>\n'


def require_open_thinking(native: bytes) -> None:
    if not native.endswith(OPEN_SUFFIX):
        raise ValueError('thinking grammar requires the qualified open-thinking generation prefix')


def with_thinking(final_grammar: str) -> str:
    roots = list(re.finditer(r'^root\s*::=', final_grammar, re.M))
    if len(roots) != 1 or re.search(r'^channel-', final_grammar, re.M):
        raise ValueError('expected one unwrapped final root and an unused channel namespace')
    # This final grammar has no references back to its root. Do not silently
    # reinterpret a recursive or differently composed grammar.
    without_root = final_grammar[:roots[0].start()] + final_grammar[roots[0].end():]
    if re.search(r'\broot\b', without_root):
        raise ValueError('referenced final root is unsupported')
    final = re.sub(r'^root\s*::=', 'channel-final ::=', final_grammar, count=1, flags=re.M)
    # A small DFA consumes arbitrary thinking until the FIRST </think>.
    # Every proper delimiter prefix falls back on a new '<' or ordinary text.
    # There is no accepting state/EOS before that delimiter and a complete reply.
    close = '</think>'
    rules = ['root ::= channel-think-0', 'channel-space ::= [ \\t\\r\\n]*',
             'channel-think-0 ::= [^<]* "<" channel-think-1']
    for n in range(1, len(close)):
        char = close[n]
        target = 'channel-space channel-final' if n == len(close)-1 else f'channel-think-{n+1}'
        rules.append(f'channel-think-{n} ::= "{char}" {target} | "<" channel-think-1 | [^<{char}] channel-think-0')
    return final + '\n' + '\n'.join(rules) + '\n'
