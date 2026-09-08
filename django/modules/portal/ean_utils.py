def calcola_base_ean(ean, tipo):
    if tipo == 6:
        base = "00000" + ean[:7]
    elif tipo == 7:
        base = "0" + ean[:11]
    else:
        base = ean[:12]
    return base

def calcola_checksum_ean13(base_12_cifre):
    dispari = sum(int(base_12_cifre[i]) for i in range(0, 12, 2))
    pari = sum(int(base_12_cifre[i]) for i in range(1, 12, 2))
    totale = dispari + pari * 3
    resto = totale % 10
    checksum = (10 - resto) % 10
    return checksum

def calcola_ean13(ean, tipo):
    base = calcola_base_ean(ean, tipo)
    if len(base) < 12:
        return None
    checksum = calcola_checksum_ean13(base)
    return base + str(checksum)