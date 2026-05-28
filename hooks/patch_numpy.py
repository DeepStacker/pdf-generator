import numpy
f = numpy.__file__
with open(f) as fp:
    c = fp.read()
old = 'def _check_local():'
new = 'def _check_local():\n    return False\n    '
if old in c:
    c = c.replace(old, new, 1)
    with open(f, 'w') as fp:
        fp.write(c)
    print('Patched ' + f)
else:
    print('WARNING: could not find _check_local in ' + f)
