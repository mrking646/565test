import csv
f = open("vector_565.csv", "a")
writer = csv.writer(f)
header = ['vcc', 'Refgnd', 'Refin', 'Vee', 'DacOut', 'Pwrgnd', 'bit']
for i in range(12):
    z = f'bit{i+1}'
    header.append(z)
print(header)
for i in range(4096):
    vcc = 15
    Refgnd = 0
    Refin = '500uA'
    Vee = -15
    Dacout = 0
    Pwrgnd = 0

    row = ''
    address = '{:012b}'.format(i)
    address = [ele for ele in str(address)]
    for ele in [vcc, Refgnd, Refin, Vee, Dacout, Pwrgnd]+address:
        row = row + f'{ele}, '
    row = row + '\r\n'
    writer.writerows(row)

f.close()
    

    