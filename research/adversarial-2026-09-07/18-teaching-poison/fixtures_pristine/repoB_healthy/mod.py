LIMIT = 100

def net_change(balance, fee):
    return balance - fee

def over_limit(x):
    return x > LIMIT
