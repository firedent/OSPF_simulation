# coding=utf-8
ID = 'A'
nodes_known = {
    'A': {
        'B': 6.5,
        'F': 2.2
    },
    'B': {
        'A': 6.5,
        'C': 1.1,
        'E': 3.2,
        'D': 4.2
    },
    'C': {
        'B': 1.1,
        'F': 1.6,
    },
    'D': {
        'F': 0.7,
        'B': 4.2,
        'C': 1.6,
        'E': 2.9
    },
    'E': {
        'B': 3.2,
        'F': 6.2,
        'D': 2.9
    },
    'F': {
        'A': 2.2,
        'E': 6.2,
        'D': 0.7
    }
}
d = {ID: 0}
previous = dict()
S = set()
Q = set(nodes_known.keys())
while len(Q) != 0:
    u = sorted([(q, d[q]) for q in Q if d.get(q, -1) != -1], key=lambda x: x[1])[0][0]
    Q.remove(u)
    S.add(u)
    for i in nodes_known[u].items():
        if d.get(i[0], -1) == -1:
            d[i[0]] = d[u] + i[1]
            previous[i[0]] = u
        elif d[i[0]] > d[u] + i[1]:
            d[i[0]] = d[u] + i[1]
            previous[i[0]] = u

print(f'I am Router {ID}')
S.remove(ID)
for i in sorted(S):
    u = i
    path = []
    while True:
        path.append(u)
        if u == ID:
            break
        u = previous[u]
    path_string = ''.join([i for i in reversed(path)])
    print(f'Least cost path to router {i}:{path_string} and the cost: {round(d[i],1)}')
