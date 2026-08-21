def calcola_checksum_ean13(base_12_cifre):
    dispari = sum(int(base_12_cifre[i]) for i in range(0, 12, 2))
    pari = sum(int(base_12_cifre[i]) for i in range(1, 12, 2))
    totale = dispari + pari * 3
    resto = totale % 10
    checksum = (10 - resto) % 10
    return checksum