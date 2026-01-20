se = set()

f1 = open('res.txt', 'r')

for i in f1.readlines():
    se.add(i)


f2 = open('res_attempt_2.txt', 'r')

for i in f2.readlines():
    se.add(i)


f3 = open('AllUsers.txt', 'w')
for i in se:

    f3.write(i)

f3.close()
    
