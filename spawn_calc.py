

def teammate_influence(d):
    
    return (1-(d-1)*.2)**0.600000023841857


def teammate_influence_final(w):
    
    return 1.0 + w * 3.0


def random_from_distance(d):

    wt = teammate_influence(d)
    wf = teammate_influence_final(wt)
    # P[ sqrt(U) < 1 / wf ]
    return wf**-2


if __name__ == '__main__':

    d = 5.71353
    wt = teammate_influence(d)
    wf = teammate_influence_final(wt)
    percent = random_from_distance(d)
    print(f'wt = {wt}\nwf = {wf}\n%  = {percent}')
