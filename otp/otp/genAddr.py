import csv

csv_name = 'vec565.csv'
with open(csv_name, 'w', newline='') as f:
    header = ['vcc', 'Refgnd', 'Refin', 'Vee', 'DacOut', 'Pwrgnd']
    for i in range(12):
        z = f'bit{i+1}'
        header.append(z)
    writer = csv.DictWriter(f, fieldnames=header)
    writer.writeheader()

with open(csv_name, 'a', newline='') as f:
    writer = csv.writer(f)
    for i in range(4096):
        vcc = 15
        Refgnd = 0
        Refin = '500uA'
        Vee = -15
        Dacout = 0
        Pwrgnd = 0
        address = '{:012b}'.format(i)
        address = [ele for ele in str(address)]
        lst_row = [vcc, Refgnd, Refin, Vee, Dacout, Pwrgnd]+address
        writer.writerow(lst_row)

    

    