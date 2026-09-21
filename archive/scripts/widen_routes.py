import sys
path = sys.argv[1]
s = open(path).read()
count = s.count('(width 0.15)')
s = s.replace('(width 0.15)', '(width 0.20)')
open(path, 'w').write(s)
print(f'widened {count} route segments')
